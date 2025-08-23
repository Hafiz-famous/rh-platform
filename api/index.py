# api/index.py
from app import create_app

# Vercel cherche une variable WSGI nommée "app"
app = create_app()

# utile en local uniquement
if __name__ == "__main__":
    app.run()
