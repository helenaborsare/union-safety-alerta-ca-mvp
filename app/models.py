from datetime import date, datetime
from typing import Optional

from sqlalchemy import Date, DateTime, Integer, String
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class Usuario(Base):
    __tablename__ = "usuarios"
    id_usuario: Mapped[int] = mapped_column(primary_key=True)
    nome: Mapped[str] = mapped_column(String(100))
    email: Mapped[str] = mapped_column(String(150), unique=True)
    senha_hash: Mapped[str] = mapped_column(String(255))


class Produto(Base):
    __tablename__ = "produtos"
    id_produto: Mapped[int] = mapped_column(primary_key=True)
    codigo: Mapped[str] = mapped_column(String(60), unique=True)
    nome: Mapped[str] = mapped_column(String(300))
    ca_numero: Mapped[Optional[str]] = mapped_column(String(12), index=True, nullable=True)
    estoque: Mapped[int] = mapped_column(Integer, default=0)
    validade_manual: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    data_importacao: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
    faixa_alertada: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)


class Certificado(Base):
    __tablename__ = "certificados"
    ca_numero: Mapped[str] = mapped_column(String(12), primary_key=True)
    validade: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    situacao: Mapped[str] = mapped_column(String(40), default="")
    data_carga: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)


class Configuracao(Base):
    __tablename__ = "configuracoes"
    id_configuracao: Mapped[int] = mapped_column(primary_key=True)
    prazo_atencao_dias: Mapped[int] = mapped_column(Integer, default=90)
    prazo_critico_dias: Mapped[int] = mapped_column(Integer, default=30)