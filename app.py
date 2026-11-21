"""Entry point Flask dan kompatibilitas import create_app untuk pengujian."""

from webapp import create_app

app = create_app()

if __name__ == "__main__":
    app.run(host="127.0.0.1", debug=False)
