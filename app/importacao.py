"""Leitura e validacao das planilhas (produtos do Bling e base de CAs do MTE).

Toda a validacao acontece aqui, no servidor (RNF02). Nada e gravado se houver erro.
"""
import csv
import io
import unicodedata
from datetime import date, datetime
from typing import Dict, Iterable, List, Optional, Tuple

from .regras import extrair_ca, normalizar_ca, situacao_valida

MAX_PRODUTOS_BYTES = 10 * 1024 * 1024
MAX_BASE_BYTES = 200 * 1024 * 1024

# Nomes aceitos para cada coluna (comparados sem acento, sem espaco, em minusculas).
ALIASES_PRODUTOS = {
    "codigo": {"codigo", "sku", "codigo(sku)", "codigodoproduto"},
    "nome": {"descricao", "nome", "produto", "descricaoproduto", "nomedoproduto"},
    "estoque": {"estoque", "saldo", "quantidade", "estoqueatual", "saldoemestoque"},
    "id": {"id", "idproduto"},
    "situacao": {"situacao"},
}
ALIASES_BASE = {
    "ca": {"registroca", "nrregistroca", "nrregistro", "registro", "ca", "numeroca", "nrca",
           "numerodoca"},
    "validade": {"datavalidade", "validade", "datadevalidade"},
    "situacao": {"situacao"},
}


class ImportacaoErro(Exception):
    """Erro de validacao com mensagem pronta para o usuario."""


def _norm(texto: str) -> str:
    texto = unicodedata.normalize("NFKD", texto or "")
    texto = "".join(c for c in texto if not unicodedata.combining(c))
    return texto.strip().lower().replace(" ", "").replace("_", "")


def validar_arquivo(nome: Optional[str], dados: bytes, extensoes: Tuple[str, ...],
                    max_bytes: int) -> None:
    if not nome:
        raise ImportacaoErro("Nenhum arquivo foi escolhido. Escolha o arquivo e tente de novo.")
    ext = "." + nome.rsplit(".", 1)[-1].lower() if "." in nome else ""
    if ext not in extensoes:
        raise ImportacaoErro(
            f"O arquivo precisa ser {' ou '.join(extensoes)}. Exporte a planilha nesse formato.")
    if not dados or not dados.strip():
        raise ImportacaoErro("O arquivo está vazio. Exporte a planilha de novo e envie.")
    if len(dados) > max_bytes:
        raise ImportacaoErro(
            f"O arquivo passa de {max_bytes // (1024 * 1024)} MB. Envie um arquivo menor.")
    if b"\x00" in dados[:8192]:
        raise ImportacaoErro(
            "O conteúdo não é uma planilha de texto (.csv). Exporte a planilha de novo.")


def _decodificar(dados: bytes) -> str:
    for codificacao in ("utf-8-sig", "cp1252"):
        try:
            return dados.decode(codificacao).lstrip("\ufeff")
        except UnicodeDecodeError:
            continue
    return dados.decode("latin-1", errors="replace")


def _ler_tabela(dados: bytes, aliases: Dict[str, set], obrigatorias: List[str],
                aviso_colunas: str):
    texto = _decodificar(dados)
    primeira = next((l for l in texto.splitlines() if l.strip()), "")
    delimitador = max(";,\t|", key=primeira.count)
    if primeira.count(delimitador) == 0:
        raise ImportacaoErro(aviso_colunas)
    leitor = csv.reader(io.StringIO(texto), delimiter=delimitador)
    cabecalho = next((l for l in leitor if any(c.strip() for c in l)), [])
    mapa: Dict[str, int] = {}
    for posicao, coluna in enumerate(cabecalho):
        nome = _norm(coluna)
        for logico, aceitos in aliases.items():
            if nome in aceitos and logico not in mapa:
                mapa[logico] = posicao
    if any(c not in mapa for c in obrigatorias):
        raise ImportacaoErro(aviso_colunas)
    return mapa, leitor


def _celula(linha: List[str], posicao: int) -> str:
    return linha[posicao].strip() if posicao < len(linha) else ""


def _inteiro(texto: str) -> int:
    texto = (texto or "").strip()
    if not texto:
        return 0
    if "," in texto:
        texto = texto.replace(".", "").replace(",", ".")
    try:
        return max(0, int(float(texto)))
    except ValueError:
        return 0


def _data(texto: str) -> Optional[date]:
    texto = (texto or "").strip()
    if not texto:
        return None
    texto = texto.split()[0].split("T")[0]
    for formato in ("%d/%m/%Y", "%Y-%m-%d", "%d-%m-%Y", "%d/%m/%y"):
        try:
            return datetime.strptime(texto, formato).date()
        except ValueError:
            continue
    return None


def _tem_html(*textos: str) -> bool:
    return any("<" in t or ">" in t for t in textos)


def ler_produtos(dados: bytes) -> Tuple[List[dict], dict]:
    mapa, linhas = _ler_tabela(
        dados, ALIASES_PRODUTOS, ["nome"],
        "O arquivo não tem as colunas esperadas (Código e Descrição). "
        "Exporte a planilha de produtos do Bling com essas colunas.")
    if "codigo" not in mapa and "id" not in mapa:
        raise ImportacaoErro("O arquivo não tem as colunas esperadas (Código e Descrição). "
                             "Exporte a planilha de produtos do Bling com essas colunas.")
    vistos: Dict[str, dict] = {}
    ignoradas = 0
    for linha in linhas:
        if not any(c.strip() for c in linha):
            continue
        codigo = _celula(linha, mapa["codigo"]) if "codigo" in mapa else ""
        if not codigo and "id" in mapa:
            id_bling = _celula(linha, mapa["id"])
            codigo = f"ID-{id_bling}" if id_bling else ""   # produto sem codigo no Bling
        nome = _celula(linha, mapa["nome"])
        if (not codigo or not nome or len(nome) > 300 or len(codigo) > 60
                or _tem_html(codigo, nome)):
            ignoradas += 1
            continue
        if "situacao" in mapa:
            situacao = _norm(_celula(linha, mapa["situacao"]))
            if situacao and not situacao.startswith("ativ"):
                ignoradas += 1
                continue
        estoque = _inteiro(_celula(linha, mapa["estoque"])) if "estoque" in mapa else 0
        vistos[codigo] = {"codigo": codigo, "nome": nome,
                          "ca_numero": extrair_ca(nome), "estoque": estoque}
    if not vistos:
        raise ImportacaoErro("Nenhuma linha válida foi encontrada na planilha.")
    produtos = list(vistos.values())
    com_ca = sum(1 for p in produtos if p["ca_numero"])
    return produtos, {"lidos": len(produtos), "com_ca": com_ca,
                      "sem_ca": len(produtos) - com_ca, "ignoradas": ignoradas}


def ler_base_ca(dados: bytes) -> Tuple[Dict[str, Tuple[Optional[date], str]], dict]:
    mapa, linhas = _ler_tabela(
        dados, ALIASES_BASE, ["ca", "validade", "situacao"],
        "O arquivo não tem as colunas esperadas da base de CAs (número do CA, "
        "data de validade e situação). Use o arquivo do CAEPI baixado do site do MTE.")
    base: Dict[str, Tuple[Optional[date], str]] = {}
    ignoradas = 0
    for linha in linhas:
        if not any(c.strip() for c in linha):
            continue
        ca = normalizar_ca(_celula(linha, mapa["ca"]))
        if not ca:
            ignoradas += 1
            continue
        validade = _data(_celula(linha, mapa["validade"]))
        situacao = _celula(linha, mapa["situacao"])[:40]
        atual = base.get(ca)
        # Se o CA aparece em varias linhas, prefere a valida e, depois, a validade mais longa.
        chave_nova = (situacao_valida(situacao), validade or date.min)
        if atual is None or chave_nova > (situacao_valida(atual[1]), atual[0] or date.min):
            base[ca] = (validade, situacao)
    if not base:
        raise ImportacaoErro("Nenhum CA válido foi encontrado na base.")
    return base, {"cas": len(base), "ignoradas": ignoradas}