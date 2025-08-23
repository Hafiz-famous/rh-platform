# api/index.py
import os, sys
# S'assurer que le package "app" (à la racine) est importable depuis api/
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app import create_app  # create_app() doit exister dans app/__init__.py

# Objet WSGI attendu par Vercel
app = create_app()

# Pour test local uniquement
if __name__ == "__main__":
    app.run()
