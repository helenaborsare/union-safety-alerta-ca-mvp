"""Fabrica da aplicacao Flask."""
import os
import secrets
from datetime import timedelta
from pathlib import Path

from flask import Flask, render_template
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker
from werkzeug.exceptions import HTTPException

from . import regras
from .banco import fechar_db
from .models import Base, Configuracao
from .seguranca import aplicar_cabecalhos, token_csrf


def create_app(config=None):
    app = Flask(__name__)
    raiz = Path(__file__).resolve().parent.parent

    chave = os.environ.get("SECRET_KEY")
    if not chave:
        chave = secrets.token_hex(32)
        app.logger.warning("SECRET_KEY nao definida: usando chave temporaria "
                           "(as sessoes se perdem ao reiniciar).")
    (raiz / "dados").mkdir(exist_ok=True)
    url_banco = os.environ.get("DATABASE_URL") or f"sqlite:///{raiz / 'dados' / 'union_safety.db'}"

    app.config.update(
        SECRET_KEY=chave,
        DATABASE_URL=url_banco,
        MAX_CONTENT_LENGTH=210 * 1024 * 1024,
        PERMANENT_SESSION_LIFETIME=timedelta(minutes=30),  # inatividade (RNF01)
        SESSION_COOKIE_HTTPONLY=True,
        SESSION_COOKIE_SAMESITE="Lax",
    )
    if config:
        app.config.update(config)

    argumentos = {"connect_args": {"check_same_thread": False}} \
        if app.config["DATABASE_URL"].startswith("sqlite") else {}
    motor = create_engine(app.config["DATABASE_URL"], **argumentos)
    Base.metadata.create_all(motor)
    app.extensions["session_factory"] = sessionmaker(bind=motor, expire_on_commit=False)

    with app.extensions["session_factory"]() as db:
        if db.scalar(select(Configuracao)) is None:
            db.add(Configuracao(prazo_atencao_dias=90, prazo_critico_dias=30))
            db.commit()

    app.teardown_appcontext(fechar_db)
    app.after_request(aplicar_cabecalhos)

    @app.context_processor
    def contexto():
        return {"csrf_token": token_csrf, "ROTULOS": regras.ROTULOS,
                "ROTULOS_CURTOS": regras.ROTULOS_CURTOS, "SIMBOLOS": regras.SIMBOLOS}

    def pagina_erro(codigo, mensagem):
        return render_template("erro.html", codigo=codigo, mensagem=mensagem), codigo

    @app.errorhandler(HTTPException)
    def erro_http(e):
        mensagens = {
            400: "Não foi possível concluir a ação. Volte ao menu e tente de novo.",
            404: "Página não encontrada. Volte ao menu.",
            413: "O arquivo enviado é grande demais.",
        }
        return pagina_erro(e.code or 500, mensagens.get(
            e.code, "Algo deu errado. Volte ao menu e tente de novo."))

    @app.errorhandler(Exception)
    def erro_inesperado(e):
        app.logger.exception("Erro inesperado")  # detalhes ficam so no log do servidor
        return pagina_erro(500, "Algo deu errado. Volte ao menu e tente de novo.")

    from .views import bp
    app.register_blueprint(bp)
    return app