"""Controles de seguranca: bloqueio de tentativas, CSRF e cabecalhos (RNF01/RNF02)."""
import hmac
import secrets
from datetime import datetime, timedelta

from flask import request, session

MAX_FALHAS = 5
BLOQUEIO = timedelta(minutes=5)
_falhas = {}  # chave -> {"n": int, "ate": datetime | None}  (em memoria)


def minutos_de_bloqueio(chave, agora=None):
    agora = agora or datetime.now()
    registro = _falhas.get(chave)
    if not registro or not registro["ate"]:
        return 0
    if registro["ate"] <= agora:
        _falhas.pop(chave, None)
        return 0
    return max(1, int((registro["ate"] - agora).total_seconds() // 60) + 1)


def registrar_falha(chave, agora=None):
    agora = agora or datetime.now()
    registro = _falhas.setdefault(chave, {"n": 0, "ate": None})
    registro["n"] += 1
    if registro["n"] >= MAX_FALHAS:
        registro["ate"] = agora + BLOQUEIO
        registro["n"] = 0


def limpar_falhas(chave=None):
    if chave is None:
        _falhas.clear()
    else:
        _falhas.pop(chave, None)


def token_csrf():
    if "csrf" not in session:
        session["csrf"] = secrets.token_hex(16)
    return session["csrf"]


def csrf_valido():
    esperado = session.get("csrf", "")
    enviado = request.form.get("csrf_token", "")
    return bool(esperado) and hmac.compare_digest(esperado.encode(), enviado.encode())


CSP = ("default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self'; "
       "form-action 'self'; frame-ancestors 'none'; base-uri 'self'")


def aplicar_cabecalhos(resposta):
    resposta.headers["Content-Security-Policy"] = CSP
    resposta.headers["X-Content-Type-Options"] = "nosniff"
    resposta.headers["X-Frame-Options"] = "DENY"
    resposta.headers["Referrer-Policy"] = "same-origin"
    resposta.headers["Cache-Control"] = "no-store"
    return resposta