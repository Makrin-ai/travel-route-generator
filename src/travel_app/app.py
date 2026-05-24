"""Travel with Maki - веб-приложение для подбора городов для путешествий.

Модуль содержит основную логику Flask-приложения:
- Загрузка базы данных городов из JSON
- Фильтрация городов по бюджету, типу отдыха и опыту путешественника
- Маршрутизация страниц (главная, профиль, логин, регистрация, сброс пароля)
- Аутентификация и авторизация пользователей
- Управление списками городов (посещённые и желаемые)
- Загрузка аватарок пользователей

"""

import json
import os
import random
from flask import Flask, render_template, request, redirect, url_for, session, send_from_directory
from flask_sqlalchemy import SQLAlchemy
from werkzeug.utils import secure_filename
from sqlalchemy import or_

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'super_secret_key')

# Настройки базы данных и папки для загрузок
BASE_DIR = os.path.abspath(os.path.dirname(__file__))
app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{os.path.join(BASE_DIR, "users.db")}'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['UPLOAD_FOLDER'] = os.path.join(BASE_DIR, 'static/uploads')

db = SQLAlchemy(app)


# --- МОДЕЛИ БАЗЫ ДАННЫХ ---

class User(db.Model):
    """Модель пользователя.
    
    Attributes:
        id (int): Уникальный идентификатор пользователя
        username (str): Уникальное имя пользователя
        email (str): Уникальный email пользователя
        password (str): Хэшированный пароль (в текущей версии хранится открыто)
        avatar (str): Имя файла аватара пользователя
        visited (relationship): Связь с посещёнными городами
        wishlist (relationship): Связь с городами в списке желаний
    """
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(120), nullable=False)
    avatar = db.Column(db.String(200), default='default.png')
    
    visited = db.relationship('VisitedCity', backref='user', lazy=True)
    wishlist = db.relationship('WishlistCity', backref='user', lazy=True)


class VisitedCity(db.Model):
    """Модель для хранения посещённых городов пользователя.
    
    Attributes:
        id (int): Уникальный идентификатор записи
        user_id (int): ID пользователя (внешний ключ)
        city_name (str): Название города
    """
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    city_name = db.Column(db.String(100), nullable=False)


class WishlistCity(db.Model):
    """Модель для хранения городов в списке желаний пользователя.
    
    Attributes:
        id (int): Уникальный идентификатор записи
        user_id (int): ID пользователя (внешний ключ)
        city_name (str): Название города
    """
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    city_name = db.Column(db.String(100), nullable=False)


# Создание базы данных (если не существует)
with app.app_context():
    db.create_all()


# --- ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ---

def load_cities():
    """Загружает список городов из JSON-файла.
    
    Функция ищет файл cities.json в папке data на уровень выше проекта.
    
    Returns:
        list: Список словарей с информацией о городах.
              При отсутствии файла или ошибке чтения возвращает пустой список.
    
    Пример возвращаемого элемента:
        {
            "city": "Париж",
            "country": "Франция",
            "type": "культурный",
            "budget_level": "high",
            "daily_cost": 150,
            "experience_required": false
        }
    """
    current_dir = os.path.dirname(os.path.abspath(__file__))
    parent_dir = os.path.dirname(current_dir)
    grandparent_dir = os.path.dirname(parent_dir)
    json_path = os.path.join(grandparent_dir, 'data', 'cities.json')
    
    if not os.path.exists(json_path):
        return []
    
    try:
        with open(json_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except (json.JSONDecodeError, Exception):
        return []


# --- МАРШРУТЫ (ROUTES) ---

@app.route('/')
def index():
    """Главная страница приложения.
    
    Отображает форму поиска и результаты фильтрации городов.
    
    Returns:
        str: HTML-шаблон index.html с переданными городами и данными пользователя.
    """
    current_user = None
    if 'user' in session:
        current_user = User.query.filter_by(username=session['user']).first()
    return render_template('index.html', cities=[], current_user=current_user)


@app.route('/register', methods=['GET', 'POST'])
def register():
    """Регистрация нового пользователя (двухшаговая форма).
    
    Шаг 1: Проверка уникальности имени пользователя.
    Шаг 2: Проверка email, пароля и создание пользователя в БД.
    
    Returns:
        str: HTML-шаблон register.html с соответствующим шагом регистрации.
    """
    if request.method == 'POST':
        if 'username' in request.form and 'email' not in request.form:
            username = request.form.get('username')
            if User.query.filter_by(username=username).first():
                return render_template('register.html', step=1, error="Это имя уже занято.")
            return render_template('register.html', step=2, username=username)

        if 'email' in request.form:
            username = request.form.get('username')
            email = request.form.get('email')
            password = request.form.get('password')
            confirm_password = request.form.get('confirm_password')

            if password != confirm_password:
                return render_template('register.html', step=2, username=username, error="Пароли не совпадают.")
            
            if User.query.filter_by(email=email).first():
                return render_template('register.html', step=2, username=username, error="Почта уже используется.")

            new_user = User(username=username, email=email, password=password)
            db.session.add(new_user)
            db.session.commit()
            session['user'] = username
            return redirect(url_for('index'))

    return render_template('register.html', step=1)


@app.route('/login', methods=['GET', 'POST'])
def login():
    """Авторизация пользователя.
    
    Поддерживает вход как по имени пользователя, так и по email.
    
    Returns:
        str: HTML-шаблон login.html или перенаправление на главную страницу.
    """
    if request.method == 'POST':
        login_input = request.form.get('username')
        password = request.form.get('password')
        
        user = User.query.filter(
            or_(User.username == login_input, User.email == login_input)
        ).first()
        
        if user and user.password == password:
            session['user'] = user.username
            return redirect(url_for('index'))
        else:
            return render_template('login.html', error="Неверные данные для входа")
            
    return render_template('login.html')


@app.route('/logout')
def logout():
    """Выход пользователя из системы.
    
    Удаляет данные пользователя из сессии.
    
    Returns:
        redirect: Перенаправление на главную страницу.
    """
    session.pop('user', None)
    return redirect(url_for('index'))


@app.route('/reset_password', methods=['GET', 'POST'])
def reset_password():
    """Сброс пароля пользователя по email.
    
    Проверяет существование пользователя с указанным email
    и обновляет пароль при совпадении новых паролей.
    
    Returns:
        str: HTML-шаблон reset_password.html с сообщением об ошибке или успехе.
    """
    error = None
    success = None
    
    if request.method == 'POST':
        email = request.form.get('email')
        new_password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')
        
        user = User.query.filter_by(email=email).first()
        
        if not user:
            error = "Пользователь с такой почтой не найден."
        elif new_password != confirm_password:
            error = "Пароли не совпадают."
        else:
            user.password = new_password
            db.session.commit()
            success = "Пароль успешно изменен! Теперь вы можете войти."
            
    return render_template('reset_password.html', error=error, success=success)


@app.route('/profile', methods=['GET', 'POST'])
def profile():
    """Личный кабинет пользователя.
    
    Поддерживает:
    - Загрузку аватара пользователя
    - Отображение посещённых городов и списка желаний
    
    Returns:
        str: HTML-шаблон profile.html или перенаправление на страницу входа.
    """
    if 'user' not in session:
        return redirect(url_for('login'))
    
    user = User.query.filter_by(username=session['user']).first()
    
    if request.method == 'POST':
        if 'avatar' in request.files:
            file = request.files['avatar']
            if file and file.filename:
                filename = secure_filename(file.filename)
                os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
                file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
                user.avatar = filename
                db.session.commit()
    
    all_cities = load_cities()
    
    user_data = {
        'username': user.username,
        'email': user.email,
        'avatar': user.avatar,
        'visited': [city.city_name for city in user.visited],
        'wishlist': [city.city_name for city in user.wishlist]
    }
    
    return render_template('profile.html', user_data=user_data, cities_data=all_cities)


@app.route('/add_visited/<city_name>')
def add_visited(city_name):
    """Добавляет город в список посещённых.
    
    Args:
        city_name (str): Название города для добавления.
    
    Returns:
        redirect: Перенаправление на страницу профиля.
    """
    if 'user' in session:
        user = User.query.filter_by(username=session['user']).first()
        exists = VisitedCity.query.filter_by(user_id=user.id, city_name=city_name).first()
        if not exists:
            new_city = VisitedCity(user_id=user.id, city_name=city_name)
            db.session.add(new_city)
            db.session.commit()
    return redirect(url_for('profile'))


@app.route('/add_wishlist/<city_name>')
def add_wishlist(city_name):
    """Добавляет город в список желаний.
    
    Args:
        city_name (str): Название города для добавления.
    
    Returns:
        redirect: Перенаправление на страницу профиля.
    """
    if 'user' in session:
        user = User.query.filter_by(username=session['user']).first()
        exists = WishlistCity.query.filter_by(user_id=user.id, city_name=city_name).first()
        if not exists:
            new_city = WishlistCity(user_id=user.id, city_name=city_name)
            db.session.add(new_city)
            db.session.commit()
    return redirect(url_for('profile'))


@app.route('/remove_visited/<city_name>')
def remove_visited(city_name):
    """Удаляет город из списка посещённых.
    
    Args:
        city_name (str): Название города для удаления.
    
    Returns:
        redirect: Перенаправление на страницу профиля.
    """
    if 'user' in session:
        user = User.query.filter_by(username=session['user']).first()
        city = VisitedCity.query.filter_by(user_id=user.id, city_name=city_name).first()
        if city:
            db.session.delete(city)
            db.session.commit()
    return redirect(url_for('profile'))


@app.route('/remove_wishlist/<city_name>')
def remove_wishlist(city_name):
    """Удаляет город из списка желаний.
    
    Args:
        city_name (str): Название города для удаления.
    
    Returns:
        redirect: Перенаправление на страницу профиля.
    """
    if 'user' in session:
        user = User.query.filter_by(username=session['user']).first()
        city = WishlistCity.query.filter_by(user_id=user.id, city_name=city_name).first()
        if city:
            db.session.delete(city)
            db.session.commit()
    return redirect(url_for('profile'))


@app.route('/static/uploads/<filename>')
def uploaded_file(filename):
    """Отдаёт загруженный файл (аватарку) пользователя.
    
    Args:
        filename (str): Имя файла для отдачи.
    
    Returns:
        file: Запрошенный файл из папки uploads.
    """
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)


@app.route('/generate', methods=['POST'])
def generate_route():
    """Генерация маршрутов с фильтрацией по критериям.
    
    Фильтрует города по:
    - Бюджету (общая стоимость = daily_cost * количество дней)
    - Типу отдыха (культурный/пляжный/активный)
    - Опыту путешественника (новичок/эксперт)
    
    Returns:
        str: HTML-шаблон index.html с отфильтрованным списком городов.
    """
    user_budget = request.form.get('money', type=int)
    user_days = request.form.get('days', type=int) or 1
    user_type = request.form.get('type')
    user_experience = request.form.get('experience')
    
    all_cities = load_cities()
    filtered_cities = []

    current_user = None
    if 'user' in session:
        current_user = User.query.filter_by(username=session['user']).first()

    for city in all_cities:
        total_cost = city.get('daily_cost', 0) * user_days
        city['total_cost'] = total_cost

        if user_budget and total_cost > user_budget:
            continue

        if user_type and user_type != "Все":
            if city['type'].lower() != user_type.lower():
                continue

        if user_experience:
            if user_experience == 'beginner' and city.get('experience_required', False):
                continue
            if user_experience == 'expert' and not city.get('experience_required', False):
                continue

        filtered_cities.append(city)

    return render_template('index.html', cities=filtered_cities, current_user=current_user)


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
