import json
import random
import os
from flask import Flask, render_template, request, redirect, url_for, session, send_from_directory
from flask_sqlalchemy import SQLAlchemy
from werkzeug.utils import secure_filename
from sqlalchemy import or_

app = Flask(__name__)
app.secret_key = 'super_secret_key'

# Настройки базы данных и папки для загрузок
BASE_DIR = os.path.abspath(os.path.dirname(__file__))
app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{os.path.join(BASE_DIR, "users.db")}'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['UPLOAD_FOLDER'] = os.path.join(BASE_DIR, 'static/uploads')

db = SQLAlchemy(app)

# --- МОДЕЛИ БАЗЫ ДАННЫХ ---

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(120), nullable=False)
    avatar = db.Column(db.String(200), default='default.png')
    
    # Связи с таблицами городов
    visited = db.relationship('VisitedCity', backref='user', lazy=True)
    wishlist = db.relationship('WishlistCity', backref='user', lazy=True)

class VisitedCity(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    city_name = db.Column(db.String(100), nullable=False)

class WishlistCity(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    city_name = db.Column(db.String(100), nullable=False)

# Создание базы данных
with app.app_context():
    db.create_all()

# --- ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ---

def load_cities():
    """Загружает список городов из JSON."""
    # Поднимаемся на 2 уровня вверх: из travel_app -> src -> travel_generator, затем заходим в data
    current_dir = os.path.dirname(os.path.abspath(__file__))  # /Users/.../travel_app
    parent_dir = os.path.dirname(current_dir)  # /Users/.../src
    grandparent_dir = os.path.dirname(parent_dir)  # /Users/.../travel_generator
    json_path = os.path.join(grandparent_dir, 'data', 'cities.json')
    
    print(f"📍 Текущая директория: {current_dir}")
    print(f"🔍 Ищу файл по пути: {json_path}")
    
    if not os.path.exists(json_path):
        print(f"❌ Файл не найден: {json_path}")
        return []
    
    try:
        with open(json_path, 'r', encoding='utf-8') as f:
            cities = json.load(f)
            print(f"✅ Успешно загружено {len(cities)} городов")
            # Выводим первые 5 городов для проверки
            for i, city in enumerate(cities[:5]):
                print(f"   {i+1}. {city.get('city', 'Unknown')}")
            return cities
    except json.JSONDecodeError as e:
        print(f"❌ Ошибка парсинга JSON: {e}")
        return []
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        return []

# --- МАРШРУТЫ (ROUTES) ---

@app.route('/')
def index():
    current_user = None
    if 'user' in session:
        current_user = User.query.filter_by(username=session['user']).first()
    return render_template('index.html', cities=[], current_user=current_user)

@app.route('/register', methods=['GET', 'POST'])
def register():
    """
    Регистрация пользователя. Исправленная логика.
    """
    error = None
    if request.method == 'POST':
        # Если пришло только имя пользователя (Шаг 1)
        if 'username' in request.form and 'email' not in request.form:
            username = request.form.get('username')
            # Просто проверяем имя и идем на шаг 2, ничего не сохраняя в БД
            if User.query.filter_by(username=username).first():
                return render_template('register.html', step=1, error="Это имя уже занято.")
            return render_template('register.html', step=2, username=username)

        # Если пришли все данные (Шаг 2)
        if 'email' in request.form:
            username = request.form.get('username')
            email = request.form.get('email')
            password = request.form.get('password')
            confirm_password = request.form.get('confirm_password')

            if password != confirm_password:
                return render_template('register.html', step=2, username=username, error="Пароли не совпадают.")
            
            if User.query.filter_by(email=email).first():
                return render_template('register.html', step=2, username=username, error="Почта уже используется.")

            # Вот здесь мы создаем пользователя только тогда, когда есть ВСЕ данные
            new_user = User(username=username, email=email, password=password)
            db.session.add(new_user)
            db.session.commit()
            
            session['user'] = username
            return redirect(url_for('index'))

    return render_template('register.html', step=1)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        # login_input — это то, что юзер ввел в поле (может быть логином или почтой)
        login_input = request.form.get('username') 
        password = request.form.get('password')
        
        print(f"Попытка входа: {login_input}") 

        # Ищем пользователя, у которого ЛИБО username равен вводу, ЛИБО email равен вводу
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
    session.pop('user', None)
    return redirect(url_for('index'))

@app.route('/reset_password', methods=['GET', 'POST'])
def reset_password():
    error = None
    success = None
    if request.method == 'POST':
        email = request.form.get('email')
        new_password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')
        
        # 1. Проверяем, существует ли пользователь с такой почтой
        user = User.query.filter_by(email=email).first()
        
        if not user:
            error = "Пользователь с такой почтой не найден."
        elif new_password != confirm_password:
            error = "Пароли не совпадают."
        else:
            # 2. Если всё ок, обновляем пароль
            user.password = new_password
            db.session.commit()
            success = "Пароль успешно изменен! Теперь вы можете войти."
            
    return render_template('reset_password.html', error=error, success=success)

@app.route('/profile', methods=['GET', 'POST'])
def profile():
    """Личный кабинет с поддержкой загрузки аватарки и отображением списков."""
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
    
    # Загружаем данные о всех городах для модального окна
    all_cities = load_cities()
    
    # Подготовка данных для передачи в шаблон
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
    """Добавить город в список 'Где я был'."""
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
    """Добавить город в 'Список желаний'."""
    if 'user' in session:
        user = User.query.filter_by(username=session['user']).first()
        exists = WishlistCity.query.filter_by(user_id=user.id, city_name=city_name).first()
        if not exists:
            new_city = WishlistCity(user_id=user.id, city_name=city_name)
            db.session.add(new_city)
            db.session.commit()
    return redirect(url_for('profile'))

@app.route('/static/uploads/<filename>')
def uploaded_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

@app.route('/generate', methods=['POST'])
def generate_route():
    """Генерация маршрутов с фильтрацией"""
    # Получаем данные из формы
    user_budget = request.form.get('money', type=int)
    user_days = request.form.get('days', type=int) or 1
    user_type = request.form.get('type')
    user_experience = request.form.get('experience')  # ДОБАВЛЕНО
    
    print(f"📊 Параметры фильтрации: бюджет={user_budget}, дней={user_days}, тип={user_type}, опыт={user_experience}")
    
    all_cities = load_cities()
    filtered_cities = []

    current_user = None
    if 'user' in session:
        current_user = User.query.filter_by(username=session['user']).first()

    for city in all_cities:
        # 1. Считаем стоимость
        total_cost = city.get('daily_cost', 0) * user_days
        city['total_cost'] = total_cost

        # 2. Фильтр по бюджету (если введен)
        if user_budget and total_cost > user_budget:
            print(f"❌ {city['city']} - превышает бюджет")
            continue

        # 3. Фильтр по типу отдыха
        if user_type and user_type != "Все":
            if city['type'].lower() != user_type.lower():
                print(f"❌ {city['city']} - не подходит по типу (нужен {user_type})")
                continue

        # 4. ДОБАВЛЕНО: Фильтр по опыту
        if user_experience:
            if user_experience == 'beginner' and city.get('experience_required', False):
                print(f"❌ {city['city']} - нужен опыт, а пользователь новичок")
                continue
            if user_experience == 'expert' and not city.get('experience_required', False):
                print(f"❌ {city['city']} - не требует опыта, а пользователь эксперт")
                continue

        # Если все фильтры пройдены - добавляем город
        print(f"✅ {city['city']} - подходит!")
        filtered_cities.append(city)

    print(f"🎯 Найдено городов: {len(filtered_cities)}")
    return render_template('index.html', cities=filtered_cities, current_user=current_user)

@app.route('/remove_visited/<city_name>')
def remove_visited(city_name):
    """Удалить город из списка 'Где я был'."""
    if 'user' in session:
        user = User.query.filter_by(username=session['user']).first()
        city = VisitedCity.query.filter_by(user_id=user.id, city_name=city_name).first()
        if city:
            db.session.delete(city)
            db.session.commit()
    return redirect(url_for('profile'))

@app.route('/remove_wishlist/<city_name>')
def remove_wishlist(city_name):
    """Удалить город из списка желаний."""
    if 'user' in session:
        user = User.query.filter_by(username=session['user']).first()
        city = WishlistCity.query.filter_by(user_id=user.id, city_name=city_name).first()
        if city:
            db.session.delete(city)
            db.session.commit()
    return redirect(url_for('profile'))

if __name__ == '__main__':
    app.run(debug=True)