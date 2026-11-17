"""Testes de integracao (precisam do SQLAlchemy instalado)."""
import io
import re
from datetime import date, timedelta

import pytest

pytest.importorskip("sqlalchemy")

from sqlalchemy import func, select  # noqa: E402
from werkzeug.security import generate_password_hash  # noqa: E402

from app.aplicacao import create_app  # noqa: E402
from app.models import Produto, Usuario  # noqa: E402
from app.seguranca import limpar_falhas  # noqa: E402

SENHA = "senha-de-teste-123"


@pytest.fixture()
def app(tmp_path):
    limpar_falhas()
    app = create_app({"DATABASE_URL": f"sqlite:///{tmp_path / 'teste.db'}",
                      "SECRET_KEY": "chave-de-teste", "TESTING": True})
    with app.extensions["session_factory"]() as db:
        db.add(Usuario(nome="Usuária Teste", email="teste@exemplo.com",
                       senha_hash=generate_password_hash(SENHA)))
        db.commit()
    return app


def _token(client, url="/login"):
    html = client.get(url).get_data(as_text=True)
    return re.search(r'name="csrf_token" value="([^"]+)"', html).group(1)


def _entrar(client, senha=SENHA):
    return client.post("/login", data={"csrf_token": _token(client), "email": "teste@exemplo.com",
                                       "senha": senha})


def _enviar(client, rota, nome, conteudo):
    token = _token(client, "/importar")
    return client.post(rota, data={"csrf_token": token, "arquivo": (io.BytesIO(conteudo), nome)},
                       content_type="multipart/form-data", follow_redirects=True)


def test_rota_protegida_sem_login_redireciona(app):
    resposta = app.test_client().get("/painel")
    assert resposta.status_code == 302 and "/login" in resposta.headers["Location"]


def test_login_certo_errado_e_bloqueio(app):
    c = app.test_client()
    errado = _entrar(c, "outra-senha")
    assert "E-mail ou senha incorretos" in errado.get_data(as_text=True)
    for _ in range(4):
        _entrar(c, "outra-senha")
    assert "Muitas tentativas" in _entrar(c).get_data(as_text=True)   # bloqueada mesmo com a senha certa


def test_login_certo_abre_menu(app):
    c = app.test_client()
    assert _entrar(c).status_code == 302
    assert "Ver painel de CAs" in c.get("/").get_data(as_text=True)


def test_post_sem_csrf_e_recusado(app):
    assert app.test_client().post("/login", data={"email": "a", "senha": "b"}).status_code == 400


def test_fluxo_completo_e_painel(app):
    c = app.test_client()
    _entrar(c)
    hoje = date.today()
    base = (f"RegistroCA;DataValidade;Situacao\n111;{hoje - timedelta(days=5):%d/%m/%Y};VENCIDO\n"
            f"222;{hoje + timedelta(days=500):%d/%m/%Y};VÁLIDO\n").encode("utf-8")
    assert "Base de CAs carregada" in _enviar(c, "/importar/base", "base.csv", base).get_data(as_text=True)
    produtos = "Código;Descrição;Estoque\nA;luva ca 111;3\nB;bota ca 222;4\nC;avental;1\n".encode()
    html = _enviar(c, "/importar/produtos", "produtos.csv", produtos).get_data(as_text=True)
    assert "3 produtos lidos, 2 com CA e 1 sem CA" in html
    painel = c.get("/painel").get_data(as_text=True)
    assert "Vencido – bloqueado para venda" in painel and "Regular" in painel and "Sem CA" in painel
    so_vencidos = c.get("/painel?situacao=vencido").get_data(as_text=True)
    assert "luva ca 111" in so_vencidos and "bota ca 222" not in so_vencidos
    assert "bota ca 222" in c.get("/painel?q=222").get_data(as_text=True)


def test_arquivo_invalido_nao_grava(app):
    c = app.test_client()
    _entrar(c)
    html = _enviar(c, "/importar/produtos", "relatorio.csv", b"MZ\x90\x00\x03\x00").get_data(as_text=True)
    assert "Nada foi gravado" in html
    with app.extensions["session_factory"]() as db:
        assert db.scalar(select(func.count()).select_from(Produto)) == 0


def test_html_no_nome_e_escapado_e_csp_presente(app):
    c = app.test_client()
    _entrar(c)
    with app.extensions["session_factory"]() as db:
        db.add(Produto(codigo="X", nome="<script>alert(1)</script>", ca_numero=None, estoque=1))
        db.commit()
    resposta = c.get("/painel")
    assert "<script>alert(1)</script>" not in resposta.get_data(as_text=True)
    assert "&lt;script&gt;" in resposta.get_data(as_text=True)
    assert "Content-Security-Policy" in resposta.headers