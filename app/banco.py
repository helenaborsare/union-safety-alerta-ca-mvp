from flask import current_app, g


def get_db():
    if "db" not in g:
        g.db = current_app.extensions["session_factory"]()
    return g.db


def fechar_db(_erro=None):
    db = g.pop("db", None)
    if db is not None:
        db.close()