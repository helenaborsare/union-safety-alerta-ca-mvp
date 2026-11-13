"""Cria um usuario (rode uma vez para cada pessoa). A senha nao fica gravada no codigo."""
import getpass

from sqlalchemy import select
from werkzeug.security import generate_password_hash

from app.aplicacao import create_app
from app.models import Usuario

app = create_app()
nome = input("Nome: ").strip()
email = input("E-mail: ").strip().lower()
senha = getpass.getpass("Senha (minimo 8 caracteres): ")
if not nome or not email or len(senha) < 8:
    raise SystemExit("Dados invalidos: informe nome, e-mail e senha com 8 ou mais caracteres.")
if senha != getpass.getpass("Repita a senha: "):
    raise SystemExit("As senhas nao conferem.")

with app.extensions["session_factory"]() as db:
    if db.scalar(select(Usuario).where(Usuario.email == email)):
        raise SystemExit("Ja existe um usuario com esse e-mail.")
    db.add(Usuario(nome=nome, email=email, senha_hash=generate_password_hash(senha)))
    db.commit()
print("Usuario criado.")