# create_admin.py

from app import create_app, db
from app.models import User

# Создаем экземпляр приложения, чтобы получить доступ к его контексту
app = create_app()

# with app.app_context() гарантирует, что мы работаем
# в правильном окружении Flask
with app.app_context():
    print("Checking for existing admin...")
    # Проверим, может админ уже есть
    if User.query.filter_by(username='admin').first():
        print("Admin user already exists.")
    else:
        print("Creating new admin user...")
        # Создаем пользователя
        u = User(username='admin', email='admin@admin.admin', role='admin', balance=0)
        # Устанавливаем пароль 'admin'
        u.set_password('SArt7062785!')

        # Сохраняем в базу данных
        db.session.add(u)
        db.session.commit()
        print("Admin user 'admin' with password 'admin' created successfully!")