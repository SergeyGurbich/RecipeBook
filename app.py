'''Код приложения для записи и хранения кулинарных рецептов'''
import datetime
import sqlalchemy
from sqlalchemy.exc import IntegrityError
from flask import Flask, render_template, request, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
from forms import AddRecipe, Search, RegistrationForm, LoginForm
from flask_login import UserMixin, LoginManager, login_required, login_user, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.config["SECRET_KEY"] = "green"
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///myDB.db'
#app.config['SQLALCHEMY_DATABASE_URI'] ='sqlite:///' + os.path.join(os.getcwd(), 'myDB.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

login_manager = LoginManager()
login_manager.init_app(app)

with app.app_context():
    # Создаем таблицы для рецептов и для пользователей в базе данных
    db = SQLAlchemy(app)

    class Recipy(db.Model):
        id = db.Column(db.Integer, primary_key = True) #primary key column, automatically generated IDs
        title = db.Column(db.String(100), index = True, unique = True) 
        author = db.Column(db.String(40), index = True, unique = False) 
        ingredients = db.Column(db.String(500), index = True, unique = False) 
        instructions = db.Column(db.String(4000), index = True, unique = False) 

    class User(UserMixin, db.Model):
        id = db.Column(db.Integer, primary_key=True)
        username = db.Column(db.String(64), index=True, unique=True)
        email = db.Column(db.String(120), index=True, unique=True)
        password_hash = db.Column(db.String(128))
        joined_at_date = db.Column(db.DateTime(), index=True, default=datetime.datetime.utcnow())

        def __repr__(self):
            return '<User {}>'.format(self.username)

        def set_password(self, password):
            self.password_hash = generate_password_hash(password)

        def check_password(self, password):
            return check_password_hash(self.password_hash, password)

    db.create_all()
'''    
# Код для главной страницы, куда теперь нельзя попасть, т.к. после залогина - страница юзера
@app.route('/')
@login_required
def index():
    #rows=Recipy.query
    rows=Recipy.query.order_by(Recipy.title)
    search_form = Search(csrf_enabled=False)
    return render_template("home.html", rows=rows, search_form=search_form)	 # Главная страница со списком ссылок на рецепты
'''

@app.route('/')
def index():
    return redirect (url_for('login'))#, form=LoginForm)

@app.route("/recipe/<int:id>")
def recipe(id):
  return render_template("recipe.html", recipe_name=Recipy.query.get(id).title,
   ingredients = Recipy.query.get(id).ingredients.split('\n'),
   instructions = Recipy.query.get(id).instructions.split('\n'),
   id=Recipy.query.get(id).id)

@app.route("/add", methods=["GET", "POST"])
def add():
    
    if request.method == "POST":
        recipe_form = AddRecipe(csrf_enabled=False)
        if recipe_form.validate_on_submit():
            title = recipe_form.title.data
            ingredients = recipe_form.ingredients.data
            instructions = recipe_form.instructions.data
            author = current_user.username
            new_recipe=Recipy(title=title, ingredients=ingredients, instructions=instructions, author= author)
        
            db.session.add(new_recipe)
            db.session.commit()
        return redirect(url_for("index"))
    else: 
        recipe_form = AddRecipe(csrf_enabled=False)
        return render_template("form_add.html", template_form=recipe_form)

@app.route("/edit/<int:id>", methods=["GET", "POST"])
def edit(id):
    if request.method == "POST":
        recipe_form = AddRecipe(csrf_enabled=False)
        
        if recipe_form.validate_on_submit():
            edited = Recipy.query.get(id)
            edited.title = recipe_form.title.data
            edited.ingredients = recipe_form.ingredients.data
            edited.instructions = recipe_form.instructions.data
            db.session.commit() 
        #return redirect("/recipe/<id>") # Это почему-то не работает - не находит страницу
        return redirect(url_for("index"))

    else:
        recipe_form = AddRecipe(csrf_enabled=False)
        recipe_form.title.data=Recipy.query.get(id).title
        recipe_form.ingredients.data=Recipy.query.get(id).ingredients
        recipe_form.instructions.data=Recipy.query.get(id).instructions
        return render_template("edit.html", id=id, template_form=recipe_form,
        title = recipe_form.title.data, 
        ingredients = recipe_form.ingredients.data, 
        instructions = recipe_form.instructions.data)

@app.route("/delete/<id>")
def delete(id):
    deleted = Recipy.query.get(id)
    db.session.delete(deleted)
    db.session.commit() 
    return redirect(url_for("index"))

@app.route("/search", methods=['GET', 'POST'])
def search():
    search_form = Search(csrf_enabled=False)
    word = request.form['word']
    rows=Recipy.query.filter(Recipy.title.like('%'+word+'%'))
    return render_template("search.html", rows=rows, search_form=search_form)

# Зарегистрировать нового пользователя и добавить в БД
@app.route('/register', methods=['GET', 'POST'])
def register():
    form = RegistrationForm()
    if form.validate_on_submit():
        try:
            user = User(username=form.username.data, email=form.email.data, 
            password_hash = generate_password_hash(form.password.data))

            db.session.add(user)
            db.session.commit()
            return redirect (url_for('login'))
        except IntegrityError:
            text = 'Sorry, this name or email are already registered in the database. Please choose another username'
            return render_template('register.html', template_form =form, txt=text)
    return render_template('register.html', template_form=form)

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id)) 

# Залогинить и перенаправлять на следующие страницы
@app.route('/login', methods=['GET','POST'])
def login():
    if request.method == "GET":
        if current_user.is_authenticated:
            return redirect(url_for('user', username = current_user.username))
        else:
            form = LoginForm(csrf_enabled=False)	
            return render_template('login.html', form=form, txt="")
    elif request.method == "POST":
        form = LoginForm(csrf_enabled=False)	# Заявляем форму
        if form.validate_on_submit():			# При нажатии на Сабмит
            user = User.query.filter_by(email=form.email.data).first()	# Создается юзер
            if user and user.check_password(form.password.data):		# Проверяется пароль
                login_user(user, remember=form.remember.data)		
                #next_page = request.args.get('next')
                username=user.username
                return redirect(url_for('user', username=username))	# то ему рендерится следующая страница по его запросу или домашняя
            else:			# если же email не находится или пароль неправильный
                text = 'Sorry, this email is not in the database or the password does not match'
                return render_template('login.html', form=form, txt=text)
    return render_template('login.html', form=form, txt="") # а до нажатия Сабмит - рендерить форму логина
# но эта строка дублирует строку в разделе "GET", так что ее нужно убрать после всех проверок

@app.route('/user/<username>')
@login_required
def user(username):
    rows=Recipy.query.order_by(Recipy.title)
    search_form = Search(csrf_enabled=False)
    user = User.query.filter_by(username=username).first_or_404()
    return render_template('user.html', user=user, username=username, rows=rows, search_form=search_form)

@app.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

@app.route('/favicon.ico')
def favicon():
    return url_for('static', filename='favicon.ico')

if __name__ == '__main__':
    app.run()
