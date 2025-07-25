from flask import Blueprint, render_template

# Создаем Blueprint с именем 'main'
main_bp = Blueprint('main', __name__)

@main_bp.route('/')
@main_bp.route('/index')
def index():
    return render_template("index.html", title='Home')