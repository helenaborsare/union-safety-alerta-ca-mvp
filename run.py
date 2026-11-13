import os

from app.aplicacao import create_app

app = create_app()

if __name__ == "__main__":
    host = os.environ.get("HOST", "127.0.0.1")
    porta = int(os.environ.get("PORT", "5000"))
    try:
        from waitress import serve
    except ImportError:
        app.run(host=host, port=porta, debug=False)
    else:
        print(f"Sistema em http://{host}:{porta}  (Ctrl+C para parar)")
        serve(app, host=host, port=porta)
    