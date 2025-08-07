import sys
from app import create_app, db
from app.models import User

# Создаем экземпляр приложения, чтобы иметь доступ к его контексту
app = create_app()

def grant_admin_role(username):
    """
    Находит пользователя по имени и присваивает ему роль 'admin'.
    """
    # with app.app_context() необходим для работы с базой данных вне веб-запроса
    with app.app_context():
        user = User.query.filter_by(username=username).first()
        if user:
            if user.role == 'admin':
                print(f"Пользователь '{username}' уже является администратором.")
            else:
                user.role = 'admin'
                db.session.commit()
                print(f"Роль 'admin' успешно присвоена пользователю '{username}'.")
        else:
            print(f"Ошибка: Пользователь с именем '{username}' не найден.")

def create_admin_user(username, email, password):
    """
    Создает нового пользователя и сразу присваивает ему роль 'admin'.
    """
    with app.app_context():
        if User.query.filter_by(username=username).first():
            print(f"Ошибка: Пользователь с именем '{username}' уже существует.")
            return
        if User.query.filter_by(email=email).first():
            print(f"Ошибка: Пользователь с email '{email}' уже существует.")
            return

        new_admin = User(username=username, email=email, role='admin')
        new_admin.set_password(password)
        db.session.add(new_admin)
        db.session.commit()
        print(f"Новый администратор '{username}' успешно создан.")


def clean_default_avatars():
    """
    Находит пользователей с некорректной записью об аватаре по умолчанию
    и очищает ее до NULL.
    """
    with app.app_context():
 # Ищем пользователей, у которых в поле avatar записано что-то вроде 'default.jpg'
 # Вы можете изменить 'default.jpg' на то значение, которое у вас могло записаться
        users_to_fix = User.query.filter(User.avatar.like('%default%')).all()

        if not users_to_fix:
            print("Не найдено пользователей с некорректными записями об аватаре.")
            return

        print(f"Найдено {len(users_to_fix)} пользователей для исправления...")

        for user in users_to_fix:
            print(f" - Очистка аватара для пользователя '{user.username}' (было: '{user.avatar}')")
            user.avatar = None

        db.session.commit()
        print("Готово! Все некорректные записи об аватарах были очищены.")
# ----- КОНЕЦ НОВОГО КОДА -----


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Использование:")
        print(" python manage.py grant-admin <имя_пользователя>")
        print(" python manage.py create-admin <имя> <email> <пароль>")
 # ----- ИЗМЕНЕНИЕ: Добавляем новую команду в справку -----
        print(" python manage.py clean-avatars - Очистить некорректные дефолтные аватары")
        sys.exit(1)

    command = sys.argv[1]

    if command == 'grant-admin':
        if len(sys.argv) != 3:
            print("Использование: python manage.py grant-admin <имя_пользователя>")
            sys.exit(1)
        grant_admin_role(sys.argv[2])

    elif command == 'create-admin':
        if len(sys.argv) != 5:
            print("Использование: python manage.py create-admin <имя> <email> <пароль>")
            sys.exit(1)
        create_admin_user(sys.argv[2], sys.argv[3], sys.argv[4])


    elif command == 'clean-avatars':
        clean_default_avatars()

    else:
        print(f"Неизвестная команда: {command}")
        sys.exit(1)
