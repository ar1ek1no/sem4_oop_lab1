"""Точка запуска без Flask-CLI: `python main.py`.

Равнозначна `flask --app app run`.
"""
from app import create_app

if __name__ == "__main__":
    create_app().run(debug=True)
