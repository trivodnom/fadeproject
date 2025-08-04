Документация по проекту FadeProject
1. Обзор проекта
FadeProject — это веб-приложение на Flask для проведения турниров по прогнозам на спортивные матчи. Пользователи могут регистрироваться, участвовать в турнирах, делать прогнозы и соревноваться за призовой фонд. Администраторы могут управлять пользователями, турнирами и результатами матчей.

Технологический стек:

Бэкенд: Python 3.10, Flask, SQLAlchemy (ORM), Flask-Login, Flask-Admin, Flask-WTF.
База данных: SQLite (для простоты разработки).
Фронтенд: HTML, CSS, JavaScript, Jinja2 (шаблонизатор), Bootstrap 4 (тема Black Dashboard).
Внешнее API: api-football.com для получения информации о матчах.
2. Структура проекта
Проект построен по модульному принципу (с использованием Flask Blueprints), что позволяет легко разделять и поддерживать функционал.

/fadeproject
|-- app/                      # Основная папка приложения
|   |-- __init__.py           # Фабрика приложения, инициализация расширений, регистрация блюпринтов
|   |-- api_client.py         # Логика для работы с внешним API (api-football.com)
|   |-- decorators.py         # Кастомные декораторы (например, @admin_or_organizer_required)
|   |-- models.py             # Определение моделей базы данных (User, Tournament, Prediction, etc.)
|   |-- routes.py             # Основные роуты (главная страница)
|   |-- util.py               # Вспомогательные функции (например, форматирование даты)
|   |
|   |-- auth/                 # Модуль аутентификации
|   |   |-- __init__.py       # Определение блюпринта 'auth'
|   |   |-- forms.py          # Формы для логина и регистрации
|   |   +-- routes.py         # Роуты /login, /register, /logout
|   |
|   |-- user/                 # Модуль управления профилем пользователя
|   |   |-- __init__.py       # Определение блюпринта 'profile'
|   |   |-- forms.py          # Формы для редактирования профиля (пользователем и админом)
|   |   +-- routes.py         # Роут /profile
|   |
|   |-- tournament/           # Модуль турниров
|   |   |-- __init__.py       # Определение блюпринта 'tournaments'
|   |   |-- forms.py          # Формы для создания турнира
|   |   |-- utils.py          # Логика подсчета очков и распределения призов
|   |   +-- routes.py         # Все роуты, связанные с турнирами (/tournaments, /tournaments/create, etc.)
|   |
|   +-- templates/            # HTML-шаблоны
|       |-- admin/            # Кастомные шаблоны для админки
|       |   +-- manage_tournament.html
|       |-- auth/
|       |-- tournament/
|       |-- user/
|       +-- base.html         # Базовый шаблон (меню, шапка, подвал)
|       +-- index.html
|
|-- migrations/               # Файлы миграций базы данных (Alembic)
|-- venv/                     # Виртуальное окружение (не включается в Git)
|-- run.py                    # Точка входа для запуска приложения и команд Flask
|-- config.py                 # Конфигурационные переменные (ключи API, секретный ключ)
+-- requirements.txt          # Список зависимостей Python
3. Модели данных (app/models.py)
User: Хранит информацию о пользователях.

id, username, email, password_hash, role ('user' или 'admin'), balance, avatar.
Связи: tournaments (многие-ко-многим), predictions (один-ко-многим), balance_history (один-ко-многим).
Tournament: Описывает турнир.

id, name, description, entry_fee, start_date, end_date, status ('draft', 'open', 'finished'), max_participants, prize_places.
matches_json: Поле TEXT, хранящее JSON-массив с полной информацией о матчах, выбранных для турнира.
Связи: attendees (участники, многие-ко-многим к User), predictions (один-ко-многим).
Prediction: Прогноз конкретного пользователя на конкретный матч в рамках турнира.

id, user_id, tournament_id, match_id (ID матча из API).
home_team, away_team: Названия команд (дублируются для удобства).
home_score_prediction, away_score_prediction: Прогноз пользователя.
home_score_actual, away_score_actual: Реальный счет матча (вводится админом).
points_awarded: Количество очков, начисленных за этот прогноз.
BalanceHistory: Запись об изменении баланса пользователя.

id, user_id, change_amount, new_balance, description, timestamp.
4. Ключевые маршруты и логика
Создание турнира (модуль tournament)
/create (create_tournament): Шаг 1. Админ заполняет основную информацию (название, взнос).
/<id>/select_matches (select_matches): Шаг 2. Админ выбирает матчи из разных лиг. JavaScript собирает информацию о выбранных матчах в JSON и отправляет на сервер.
Сервер сохраняет этот JSON в поле Tournament.matches_json, вычисляет start_date и end_date и делает турнир активным.
Участие в турнире
/tournaments/<id> (tournament_details): Отображает всю информацию о турнире.
/tournaments/<id>/action (POST join_or_leave_tournament): Обрабатывает вступление/выход из турнира. Списывает/возвращает entry_fee с баланса и создает запись в BalanceHistory.
Прогнозы
/tournaments/<id>/predict (POST make_prediction): Принимает прогноз от пользователя. Находит или создает запись Prediction и сохраняет счет.
Подсчет очков (кастомная админка)
/admin/tournament/<id>/manage (manage_tournament): Кастомная страница в админке, недоступная через стандартное меню Flask-Admin.
GET-запрос: Страница отображает все матчи из tournament.matches_json и поля для ввода реального счета. Уже введенные результаты подгружаются из существующих прогнозов.
POST-запрос:
Сервер принимает введенные счета.
Для каждого матча, где был введен счет, он находит все прогнозы (Prediction) от всех участников этого турнира.
Вызывает функцию calculate_points из app/tournament/utils.py для каждого прогноза.
Сохраняет реальный счет и начисленные очки в каждую запись Prediction.
5. Переменные окружения и конфигурация (config.py)
Для работы приложения необходимо задать следующие переменные:

SECRET_KEY: Секретный ключ Flask для защиты сессий и форм.
API_HOST: Хост API (например, v3.football.api-sports.io).
API_KEY: Ваш ключ доступа к API.
SQLALCHEMY_DATABASE_URI: Путь к файлу базы данных (например, sqlite:///app.db).
6. Как развернуть и запустить
Клонировать репозиторий.
Создать и активировать виртуальное окружение: python -m venv venv && source venv/bin/activate.
Установить зависимости: pip install -r requirements.txt.
Создать файл .env (по аналогии с config.py) и прописать в нем все необходимые переменные.
Применить миграции базы данных: flask db upgrade.
Запустить приложение: flask run.
Эта документация описывает текущее состояние проекта. Ее можно сохранить в файл README.md или DOCUMENTATION.md в корне проекта.

-----------------------------
-----------------------------

Детальная архитектура и взаимосвязи файлов
Сценарий 1: Пользователь открывает страницу турнира
Цель: Показать вам страницу с деталями турнира, списком матчей, вашими прогнозами и таблицей лидеров.

Вы кликаете на ссылку -> Браузер отправляет GET-запрос на /tournaments/<id>.

app/tournament/routes.py:

Срабатывает роут @tournament_bp.route('/<int:tournament_id>'), который вызывает функцию tournament_details(tournament_id).
models.py: Функция обращается к базе данных через Tournament.query.get_or_404(tournament_id), чтобы получить объект турнира.
models.py: Получает список участников через tournament.attendees.
Извлекает JSON матчей из tournament.matches_json.
models.py: Запрашивает все прогнозы текущего пользователя для этого турнира: Prediction.query.filter_by(user_id=current_user.id, ...).
models.py: Делает сложный запрос к БД для построения таблицы лидеров, объединяя (join) таблицы Prediction и User и суммируя очки.
app/tournament/utils.py: Вызывает функцию calculate_prize_distribution() для расчета призовых.
render_template(): В конце, собрав все эти данные (объект турнира, список матчей, прогнозы, лидерборд, призы), передает их в шаблон.
app/templates/tournament/details.html:

Получает все данные от render_template.
В цикле {% for match in matches %} отрисовывает каждый матч.
Для каждой строки проверяет, есть ли ваш прогноз в словаре user_predictions, и отображает либо форму для ввода, либо уже сделанный прогноз.
Отображает информацию о призах и лидерборд.
Связанные файлы: routes.py (оркестратор) -> models.py (данные) -> utils.py (бизнес-логика) -> details.html (отображение).

Сценарий 2: Администратор вводит результаты матчей
Цель: Сохранить реальный счет матчей и пересчитать очки для всех участников.

Админ заходит в админку -> видит список турниров.

app/__init__.py:

Класс TournamentAdminView отвечает за отображение списка.
Специальная функция _format_manage_link генерирует для каждой строки HTML-кнопку "Manage Scores", которая ведет на уникальный URL.
Админ нажимает "Manage Scores" -> Браузер отправляет GET-запрос на /admin/tournament/<id>/manage.

app/tournament/routes.py:

Срабатывает роут @tournament_bp.route('/admin/tournament/<int:tournament_id>/manage'), который вызывает функцию manage_tournament(tournament_id).
models.py: Функция получает турнир по ID.
Извлекает matches_json.
models.py: Запрашивает все прогнозы, у которых уже есть реальный счет, чтобы предзаполнить поля в форме (existing_results).
render_template(): Передает все это в специальный админский шаблон.
app/templates/admin/manage_tournament.html:

Отрисовывает таблицу со всеми матчами турнира и полями для ввода счета.
Если для матча уже есть результат в existing_results, поле заполняется этим значением.
Админ вводит счета и нажимает "Save Scores..." -> Браузер отправляет POST-запрос на тот же URL /admin/tournament/<id>/manage.

app/tournament/routes.py:

Снова срабатывает manage_tournament, но на этот раз заходит в блок if request.method == 'POST'.
Цикл по матчам: Скрипт итерируется по всем матчам из matches_json.
Для каждого матча он ищет в request.form поля с именами home_score_... и away_score_....
models.py: Если счет введен, он находит все прогнозы на этот матч: Prediction.query.filter_by(tournament_id=..., match_id=...).
Цикл по прогнозам: Теперь он итерируется по всем найденным прогнозам.
app/tournament/utils.py: Для каждого прогноза вызывается функция calculate_points(prediction, actual_home, actual_away).
Результат ее работы (0, 1, 2, 3 или 5) записывается в prediction.points_awarded.
Реальный счет также сохраняется в prediction.home_score_actual и prediction.away_score_actual.
db.session.commit(): После завершения всех циклов одним махом сохраняет все изменения в базу данных.
Связанные файлы: __init__.py (точка входа в админку) -> routes.py (обработчик POST-запроса) -> utils.py (расчет очков) -> models.py (массовое обновление данных).

Сценарий 3: Регистрация блюпринтов и запуск приложения
Это самый корень, объясняющий, как все модули собираются вместе.

Запускается run.py.
Он импортирует create_app из app/__init__.py и вызывает ее.
app/__init__.py: Функция create_app() выполняет ключевые действия:
Создает экземпляр app = Flask(__name__).
Инициализирует все расширения: db.init_app(app), login.init_app(app), admin.init_app(app).
Регистрирует блюпринты:
from app.auth import auth_bp
app.register_blueprint(auth_bp, url_prefix='/auth')
Это говорит Flask: "Все роуты из auth_bp (которые лежат в app/auth/routes.py) будут доступны с префиксом /auth". Например, @auth_bp.route('/login') становится /auth/login.
То же самое происходит для user_bp (profile_bp) и tournament_bp.
Настраивает админку:
admin.add_view(UserAdminView(User, db.session))
Эта строка создает стандартную CRUD-страницу для модели User в админке.
Возвращает готовый к работе экземпляр app.
Эта архитектура позволяет каждому модулю (auth, user, tournament) иметь свои собственные роуты, формы и шаблоны, не мешая друг другу, а главный файл __init__.py собирает их всех вместе.