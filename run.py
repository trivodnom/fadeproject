# run.py
from app import create_app, db
from app.models import User, Tournament, Prediction, BalanceHistory

app = create_app()

# Это позволяет использовать команды вроде `python run.py shell`
@app.shell_context_processor
def make_shell_context():
    return {'db': db, 'User': User, 'Tournament': Tournament, 'Prediction': Prediction, 'BalanceHistory': BalanceHistory}

# Эта часть нужна, чтобы Flask-Migrate работал из командной строки
# Если файл запущен как главный, он не будет запускать сервер,
# а позволит Flask-Migrate и другим расширениям перехватить управление.
if __name__ == '__main__':
    # Если вы хотите запустить сервер разработки, вы должны будете использовать команду:
    # flask run
    # или настроить запуск здесь, но для работы `db` команд это не нужно.
    # app.run(debug=True) # <-- Закомментируйте или удалите эту строку, если она у вас есть
    pass