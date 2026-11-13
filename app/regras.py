import re
import unicodedata
from dataclasses import dataclass
from datetime import date
from typing import Optional

_PADRAO_CA = re.compile(r"\bCA[\s.:\-]*(\d{3,6})\b", re.IGNORECASE)

VENCIDO = "vencido"
ATENCAO_30 = "atencao30"
ATENCAO_90 = "atencao90"
REGULAR = "regular"
SEM_CA = "sem_ca"

ORDEM_STATUS = [VENCIDO, ATENCAO_30, ATENCAO_90, REGULAR, SEM_CA]

ROTULOS = {
    VENCIDO: "Vencido – bloqueado para venda",
    ATENCAO_30: "Vence em até 30 dias",
    ATENCAO_90: "Vence em até 90 dias",
    REGULAR: "Regular",
    SEM_CA: "Sem CA",
}
ROTULOS_CURTOS = {**ROTULOS, VENCIDO: "Vencido"}
SIMBOLOS = {VENCIDO: "✕", ATENCAO_30: "▲", ATENCAO_90: "◆", REGULAR: "✓", SEM_CA: "?"}
_PESO_URGENCIA = {VENCIDO: 0, ATENCAO_30: 1, ATENCAO_90: 2, SEM_CA: 3, REGULAR: 4}


@dataclass(frozen=True)
class Resultado:
    status: str
    rotulo: str
    simbolo: str
    dias: Optional[int]
    detalhe: str
    urgencia: int


def normalizar_ca(valor) -> Optional[str]:
    digitos = re.sub(r"\D", "", str(valor or ""))
    if not digitos:
        return None
    return str(int(digitos))


def extrair_ca(nome: Optional[str]) -> Optional[str]:
    if not nome:
        return None
    achados = _PADRAO_CA.findall(nome)
    if not achados:
        return None
    return normalizar_ca(achados[-1])


def situacao_valida(situacao: Optional[str]) -> bool:
    texto = unicodedata.normalize("NFKD", situacao or "")
    texto = "".join(c for c in texto if not unicodedata.combining(c)).strip().upper()
    return texto.startswith("VALID")


def _resultado(status, dias, detalhe) -> Resultado:
    return Resultado(status, ROTULOS[status], SIMBOLOS[status], dias, detalhe,
                     _PESO_URGENCIA[status])


def classificar(ca_numero, encontrado, validade, situacao, hoje: date,
                prazo_atencao: int = 90, prazo_critico: int = 30,
                validade_manual: Optional[date] = None) -> Resultado:
    if not ca_numero:
        return _resultado(SEM_CA, None, "Sem número de CA no nome do produto")

    if validade_manual is not None:
        validade = validade_manual
    else:
        if not encontrado:
            return _resultado(SEM_CA, None, "CA não localizado na base carregada")
        if not situacao_valida(situacao):
            return _resultado(VENCIDO, None,
                              f"Situação do CA na base: {situacao or 'não informada'}")
        if validade is None:
            return _resultado(SEM_CA, None, "Base sem data de validade para este CA")

    dias = (validade - hoje).days
    detalhe = f"Validade em {validade:%d/%m/%Y}"
    if dias < 0:
        return _resultado(VENCIDO, dias, detalhe)
    if dias <= prazo_critico:
        return _resultado(ATENCAO_30, dias, detalhe)
    if dias <= prazo_atencao:
        return _resultado(ATENCAO_90, dias, detalhe)
    return _resultado(REGULAR, dias, detalhe)