from datetime import date

import pytest

from app.importacao import (ImportacaoErro, ler_base_ca, ler_produtos, validar_arquivo)

BLING = ("Código;Descrição;Estoque\nA1;botina ca 28511;10\nA2;capacete branco;5\n"
         "A3;<script>x</script> ca 1234;1\n").encode("utf-8")


def test_ler_produtos():
    produtos, resumo = ler_produtos(BLING)
    assert resumo == {"lidos": 2, "com_ca": 1, "sem_ca": 1, "ignoradas": 1}
    assert produtos[0]["ca_numero"] == "28511" and produtos[0]["estoque"] == 10


def test_recusa_executavel_renomeado():
    with pytest.raises(ImportacaoErro):
        validar_arquivo("relatorio.csv", b"MZ\x90\x00\x03\x00\x00\x00", (".csv",), 1000)


def test_recusa_extensao_vazio_e_grande():
    with pytest.raises(ImportacaoErro):
        validar_arquivo("a.exe", b"x;y", (".csv",), 1000)
    with pytest.raises(ImportacaoErro):
        validar_arquivo("a.csv", b"   \n", (".csv",), 1000)
    with pytest.raises(ImportacaoErro):
        validar_arquivo("a.csv", b"a;b" * 1000, (".csv",), 100)


def test_recusa_sem_colunas_esperadas():
    with pytest.raises(ImportacaoErro):
        ler_produtos(b"a;b\n1;2\n")
    with pytest.raises(ImportacaoErro):
        ler_base_ca(b"x;y;z\n1;2;3\n")


def test_ler_base_ca_prefere_linha_valida():
    dados = ("RegistroCA;DataValidade;Situacao\n28511;15/12/2026;VÁLIDO\n"
             "28511;10/01/2026;VENCIDO\n54321;01/09/2026;VENCIDO\n").encode("utf-8")
    base, resumo = ler_base_ca(dados)
    assert base["28511"] == (date(2026, 12, 15), "VÁLIDO")
    assert base["54321"][1] == "VENCIDO" and resumo["cas"] == 2


def test_aceita_virgula_e_latin1():
    dados = "Codigo,Descricao,Estoque\nX1,luva ca 1234,\"1.200,00\"\n".encode("cp1252")
    produtos, _ = ler_produtos(dados)
    assert produtos[0]["estoque"] == 1200


def test_cabecalho_real_do_caepi():
    dados = ('NR Registro CA;DATA DE VALIDADE;SITUACAO;NR DO PROCESSO;CNPJ\n'
             '"27";"28/01/2021";"VENCIDO";"46017000279201619";"27015676000105"\n'
             '"365";"09/01/2028";"VÁLIDO";"19966200167202555";"45655461000130"\n').encode("utf-8")
    base, resumo = ler_base_ca(dados)
    assert base["27"] == (date(2021, 1, 28), "VENCIDO")
    assert base["365"] == (date(2028, 1, 9), "VÁLIDO") and resumo["cas"] == 2


def test_codigo_vazio_usa_id_e_inativo_e_ignorado():
    dados = ('"ID";"Código";"Descrição";"Situação";"Estoque"\n'
             '"10";"A1\t";"luva ca 12345";"Ativo";"5,00"\n'
             '"11";"";"botina ca 54321";"Ativo";"-2,00"\n'
             '"12";"A3";"capacete ca 11111";"Inativo";"1,00"\n').encode("utf-8")
    produtos, resumo = ler_produtos(dados)
    assert [p["codigo"] for p in produtos] == ["A1", "ID-11"]
    assert produtos[1]["estoque"] == 0 and resumo["ignoradas"] == 1 and resumo["com_ca"] == 2


def test_bom_duplo_no_cabecalho_do_caepi():
    dados = (b"\xef\xbb\xbf\xef\xbb\xbfNR Registro CA;DATA DE VALIDADE;SITUACAO\n"
             b'"27";"28/01/2021";"VENCIDO"\n')
    base, _ = ler_base_ca(dados)
    assert base["27"][1] == "VENCIDO"