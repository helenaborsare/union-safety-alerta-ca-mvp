from datetime import date

from app import regras
from app.regras import classificar, extrair_ca

HOJE = date(2026, 11, 12)


def test_extrair_ca():
    assert extrair_ca("botina usafe bico de aço ca 28511") == "28511"
    assert extrair_ca("Luva CA-54321 tam M") == "54321"
    assert extrair_ca("capacete branco") is None
    assert extrair_ca("capacete aba frontal 50") is None
    assert extrair_ca("Bota CA 111 e ca 22222") == "22222"
    assert extrair_ca("luva ca 028511") == "28511"
    assert extrair_ca(None) is None


def _c(validade, situacao="VÁLIDO", **kw):
    return classificar("123", True, validade, situacao, HOJE, **kw)


def test_faixas_e_limites():
    assert _c(date(2026, 11, 11)).status == regras.VENCIDO
    assert _c(date(2026, 11, 12)).status == regras.ATENCAO_30   # vence hoje ainda vale
    assert _c(date(2026, 12, 12)).status == regras.ATENCAO_30   # 30 dias
    assert _c(date(2026, 12, 13)).status == regras.ATENCAO_90   # 31 dias
    assert _c(date(2027, 2, 10)).status == regras.ATENCAO_90    # 90 dias
    assert _c(date(2027, 2, 11)).status == regras.REGULAR       # 91 dias


def test_situacao_diferente_de_valida_e_vencida():
    r = _c(date(2030, 1, 1), situacao="CANCELADO")
    assert r.status == regras.VENCIDO and r.dias is None
    assert _c(date(2030, 1, 1), situacao="Válido").status == regras.REGULAR


def test_sem_ca_e_ca_fora_da_base():
    assert classificar(None, False, None, None, HOJE).status == regras.SEM_CA
    r = classificar("999", False, None, None, HOJE)
    assert r.status == regras.SEM_CA and "não localizado" in r.detalhe


def test_prazos_configuraveis():
    assert _c(date(2026, 12, 20), prazo_critico=60).status == regras.ATENCAO_30