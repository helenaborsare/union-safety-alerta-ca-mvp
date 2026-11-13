"""Camada de apresentacao: rotas e telas."""
from collections import Counter
from datetime import date, datetime

from flask import (Blueprint, abort, flash, redirect, render_template, request,
                   session, url_for)
from sqlalchemy import delete, func, insert, select
from werkzeug.security import check_password_hash, generate_password_hash

from . import regras
from .banco import get_db
from .importacao import (MAX_BASE_BYTES, MAX_PRODUTOS_BYTES, ImportacaoErro,
                         ler_base_ca, ler_produtos, validar_arquivo)
from .models import Certificado, Configuracao, Produto, Usuario
from .seguranca import (csrf_valido, limpar_falhas, minutos_de_bloqueio,
                        registrar_falha)

bp = Blueprint("main", __name__)

MSG_LOGIN = "E-mail ou senha incorretos. Confira os dados e tente de novo."
_HASH_FALSO = generate_password_hash("senha-falsa-para-igualar-o-tempo")


@bp.before_app_request
def proteger():
    """Exige login em todas as rotas (exceto login e arquivos estaticos) e valida CSRF."""
    if request.endpoint == "static":
        return None
    session.permanent = True
    if request.method == "POST" and not csrf_valido():
        abort(400)
    if request.endpoint != "main.login" and "id_usuario" not in session:
        return redirect(url_for("main.login"))
    return None


@bp.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "GET" and "id_usuario" in session:
        return redirect(url_for("main.menu"))
    erro, email = None, ""
    if request.method == "POST":
        email = (request.form.get("email") or "").strip().lower()[:150]
        senha = request.form.get("senha") or ""
        chave = f"{request.remote_addr}|{email}"
        espera = minutos_de_bloqueio(chave)
        if espera:
            erro = f"Muitas tentativas. Aguarde {espera} minuto(s) e tente de novo."
        else:
            usuario = get_db().scalar(select(Usuario).where(Usuario.email == email))
            hash_ = usuario.senha_hash if usuario else _HASH_FALSO
            if check_password_hash(hash_, senha) and usuario is not None:
                limpar_falhas(chave)
                session.clear()
                session["id_usuario"] = usuario.id_usuario
                session["nome"] = usuario.nome
                session.permanent = True
                return redirect(url_for("main.menu"))
            registrar_falha(chave)
            erro = MSG_LOGIN
    return render_template("login.html", erro=erro, email=email)


@bp.post("/sair")
def sair():
    session.clear()
    return redirect(url_for("main.login"))


def _ultima_carga(db):
    quando = db.scalar(select(func.max(Certificado.data_carga)))
    return quando.strftime("%d/%m/%Y") if quando else None


@bp.get("/")
def menu():
    return render_template("menu.html", ultima_carga=_ultima_carga(get_db()))


@bp.get("/importar")
def importar():
    return render_template("importar.html", ultima_carga=_ultima_carga(get_db()))


def _salvar_produtos(db, produtos):
    existentes = {p.codigo: p for p in db.scalars(select(Produto))}
    agora = datetime.now()
    for item in produtos:
        produto = existentes.get(item["codigo"])
        if produto is None:
            db.add(Produto(codigo=item["codigo"], nome=item["nome"],
                           ca_numero=item["ca_numero"], estoque=item["estoque"],
                           data_importacao=agora))
        else:
            produto.nome = item["nome"]
            produto.ca_numero = item["ca_numero"]
            produto.estoque = item["estoque"]
            produto.data_importacao = agora
    db.commit()


def _salvar_base(db, base):
    agora = datetime.now()
    db.execute(delete(Certificado))
    registros = [{"ca_numero": ca, "validade": validade, "situacao": situacao,
                  "data_carga": agora} for ca, (validade, situacao) in base.items()]
    for inicio in range(0, len(registros), 5000):
        db.execute(insert(Certificado), registros[inicio:inicio + 5000])
    db.commit()


def _numero(n):
    return f"{n:,}".replace(",", ".")


@bp.post("/importar/produtos")
def importar_produtos():
    arquivo = request.files.get("arquivo")
    try:
        if arquivo is None:
            raise ImportacaoErro("Nenhum arquivo foi enviado.")
        dados = arquivo.read(MAX_PRODUTOS_BYTES + 1)
        validar_arquivo(arquivo.filename, dados, (".csv",), MAX_PRODUTOS_BYTES)
        produtos, resumo = ler_produtos(dados)
        _salvar_produtos(get_db(), produtos)
        texto = (f"Importação concluída: {_numero(resumo['lidos'])} produtos lidos, "
                 f"{_numero(resumo['com_ca'])} com CA e {_numero(resumo['sem_ca'])} sem CA.")
        if resumo["ignoradas"]:
            texto += f" {resumo['ignoradas']} linha(s) foram ignoradas (inválidas ou produtos inativos no Bling)."
        flash(texto, "ok")
    except ImportacaoErro as erro:
        flash(f"{erro} Nada foi gravado.", "erro")
    return redirect(url_for("main.importar"))


@bp.post("/importar/base")
def importar_base():
    arquivo = request.files.get("arquivo")
    try:
        if arquivo is None:
            raise ImportacaoErro("Nenhum arquivo foi enviado.")
        dados = arquivo.read(MAX_BASE_BYTES + 1)
        validar_arquivo(arquivo.filename, dados, (".csv", ".txt"), MAX_BASE_BYTES)
        base, resumo = ler_base_ca(dados)
        _salvar_base(get_db(), base)
        flash(f"Base de CAs carregada: {_numero(resumo['cas'])} certificados.", "ok")
    except ImportacaoErro as erro:
        flash(f"{erro} Nada foi gravado.", "erro")
    return redirect(url_for("main.importar"))


def _texto_dias(r):
    if r.dias is None:
        return "—"
    if r.dias < 0:
        n = -r.dias
        return f"vencido há {n} dia" + ("" if n == 1 else "s")
    if r.dias == 0:
        return "vence hoje"
    return f"{r.dias} dia" + ("" if r.dias == 1 else "s")


@bp.get("/painel")
def painel():
    db = get_db()
    hoje = date.today()
    cfg = db.scalar(select(Configuracao))
    atencao, critico = cfg.prazo_atencao_dias, cfg.prazo_critico_dias

    q = (request.args.get("q") or "").strip()[:100]
    filtro = request.args.get("situacao", "todas")
    if filtro not in regras.ROTULOS:
        filtro = "todas"
    ordem = request.args.get("ordem", "urgencia")
    if ordem not in ("urgencia", "az"):
        ordem = "urgencia"

    consulta = select(Produto, Certificado).outerjoin(
        Certificado, Certificado.ca_numero == Produto.ca_numero)
    linhas = []
    for produto, cert in db.execute(consulta).all():
        r = regras.classificar(
            produto.ca_numero, cert is not None, cert.validade if cert else None,
            cert.situacao if cert else None, hoje, atencao, critico,
            produto.validade_manual)
        validade = produto.validade_manual or (cert.validade if cert else None)
        linhas.append({"nome": produto.nome, "ca": produto.ca_numero or "—",
                       "validade": validade.strftime("%d/%m/%Y") if validade else "—",
                       "dias_texto": _texto_dias(r), "r": r, "dias": r.dias})

    contagem = Counter(l["r"].status for l in linhas)
    total = len(linhas)

    termo = q.lower()
    digitos = "".join(c for c in q if c.isdigit())
    visiveis = []
    for l in linhas:
        if filtro != "todas" and l["r"].status != filtro:
            continue
        if q and termo not in l["nome"].lower() and not (
                digitos and l["ca"] != "—" and digitos in l["ca"]):
            continue
        visiveis.append(l)

    if ordem == "az":
        visiveis.sort(key=lambda l: l["nome"].lower())
    else:
        visiveis.sort(key=lambda l: (l["r"].urgencia,
                                     l["dias"] if l["dias"] is not None else 10 ** 9,
                                     l["nome"].lower()))

    return render_template(
        "painel.html", linhas=visiveis, contagem=contagem, total=total, q=q,
        filtro=filtro, ordem=ordem, ordem_status=regras.ORDEM_STATUS,
        ultima_carga=_ultima_carga(db), hoje=hoje.strftime("%d/%m/%Y"),
        numero=_numero)