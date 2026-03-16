from models import init_db
from app import App

if __name__ == "__main__": # проверка, есть ли таблицы
    init_db()

    # интерфейс
    app = App()
    app.mainloop()
