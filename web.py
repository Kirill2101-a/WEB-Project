from flask import Flask, render_template, request, redirect, url_for, session
from gigachat import GigaChat
from langchain_core.messages import HumanMessage
from langchain_community.chat_models.gigachat import GigaChat
from database import db
from all_models import User, Result
import hashlib

app = Flask(__name__)
app.secret_key = 'secret'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///project.sqlite'
conditions_accepted = False

db.init_app(app)
with app.app_context():
    db.create_all()


class Work:
    def __init__(self):
        self.giga = GigaChat(
            credentials="YWFiNjI4YzUtYWU3ZC00YjM2LTg2ZjgtODU0ZDg5Yjg2MmMyOmQ1YTZlZDI2LTVhYzktNGRhMi1iOGJkLTg1ZmZlYWJmY2JjZQ==",
            scope="GIGACHAT_API_PERS",
            model="GigaChat",
            verify_ssl_certs=False
        )

    def generate(self, prompt):
        response = self.giga.invoke([HumanMessage(content=prompt)])
        return response.content


class History:
    def add_history(self, prompt, response, user_id):
        result = Result(
            input=prompt,
            output=response,
            lenght=len(response),
            user_id=user_id
        )
        db.session.add(result)
        db.session.commit()

    def get_history(self, user_id, search_query=None, search_type='both'):
        query = Result.query.filter_by(user_id=user_id)

        if search_query:
            search_term = f"%{search_query}%"
            if search_type == 'prompt':
                query = query.filter(Result.input.like(search_term))
            elif search_type == 'response':
                query = query.filter(Result.output.like(search_term))
            else:
                query = query.filter(db.or_(
                    Result.input.like(search_term),
                    Result.output.like(search_term)
                ))

        results = query.all()
        return [{'prompt': res.input, 'response': res.output} for res in results]


generator = Work()
manager = History()


@app.context_processor
def inject_conditions():
    return dict(conditions_accepted=conditions_accepted)


@app.route('/')
def index():
    return render_template('index.html')


@app.context_processor
def inject_user():
    return dict(user=session.get('user'))


@app.route('/generate', methods=['POST'])
def generate():
    if 'user' not in session:
        return redirect(url_for('login'))

    global conditions_accepted
    if not conditions_accepted:
        return render_template('index.html', error="Примите условия генерации")

    prompt = request.form.get('prompt')
    if not prompt:
        return render_template('index.html', error="Пустой запрос")

    try:
        user = User.query.filter_by(login=session['user']).first()
        if not user:
            return redirect(url_for('login'))

        response = generator.generate(prompt)
        manager.add_history(prompt, response, user.id)
        return render_template('index.html', output= response)
    except Exception as e:
        return render_template('index.html', error=f"Ошибка генерации: {str(e)}")


@app.route('/history')
def show_history():
    if 'user' not in session:
        return redirect(url_for('login'))

    try:
        user = User.query.filter_by(login=session['user']).first()
        if not user:
            return redirect(url_for('login'))

        search_query = request.args.get('search', '')
        search_type = request.args.get('search_type', 'both')

        history= manager.get_history(
            user_id=user.id,
            search_query=search_query,
            search_type=search_type
        )

        return render_template(
            'history.html',
            history=history,
            search=search_query,
            search_type=search_type
        )
    except Exception as e:
        return render_template('index.html', error=str(e))


@app.route('/conditions')
def show_conditions():
    global conditions_accepted
    if request.args.get('accept') == '1':
        conditions_accepted = True
        return redirect(url_for('index'))
    return render_template('conditions.html')


@app.route('/premium', methods=['GET', 'POST'])
def premium():
    if 'user' not in session:
        return redirect(url_for('login'))

    global conditions_accepted
    if not conditions_accepted:
        return render_template('premium.html', error="Примите условия генерации")

    try:
        user = User.query.filter_by(login=session['user']).first()
        if not user:
            return redirect(url_for('login'))

        if request.method == 'POST':
            prompt = request.form.get('prompt')
            file = request.files.get('file')

            file_content = ""
            if file and file.filename != '':
                if not file.filename.endswith('.txt'):
                    return render_template('premium.html', error="Допустимы только .txt файлы")
                try:
                    file_content = file.read().decode('utf-8')
                except Exception as e:
                    return render_template('premium.html', error=f"Ошибка чтения файла: {str(e)}")

            full_prompt = f"{prompt}\nКонтекст из файла:\n{file_content}" if file_content else prompt

            if not full_prompt.strip():
                return render_template('premium.html', error="Пустой запрос")

            responses = [
                generator.generate(full_prompt + " Очень подробно, подумай хорошо"),
                generator.generate(full_prompt + " Без ошибок, но кратко"),
                generator.generate(full_prompt + " Просто, но правильно")
            ]

            session['premium_responses'] = responses
            session['premium_prompt'] = full_prompt

            return render_template('premium.html', responses=responses,
                                   prompt=prompt,
                                   show_ad=True)
        return render_template('premium.html', show_ad=False)
    except Exception as e:
        return render_template('error.html', error=str(e))


@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        login = request.form.get('login')
        password = request.form.get('password')
        name = request.form.get('name')

        try:
            existing_user = User.query.filter_by(login=login).first()
            if existing_user:
                return render_template('register.html', error="Логин уже занят")

            if len(password) < 8:
                return render_template('register.html', error="Пароль должен быть не короче 8 символов")

            code1 = bin(len(password))
            code2 = bin(len(login))
            code3 = hashlib.md5(login.encode()).digest()
            pasw1 = hashlib.md5(password.encode()).digest()
            pasw2 = hashlib.md5(pasw1).hexdigest()
            hash = f"{code1}{code2}{code3}{pasw2}"

            new_user = User(login=login, password=hash, name=name)
            db.session.add(new_user)
            db.session.commit()

            session['user'] = login
            return redirect(url_for('index'))
        except Exception as e:
            db.session.rollback()
            return render_template('register.html', error=f"Ошибка регистрации: {str(e)}")

    return render_template('register.html')


@app.route('/premium/save', methods=['POST'])
def save_premium_response():
    if 'user' not in session:
        return redirect(url_for('login'))

    try:
        ind = request.form.get('selected_response')
        prompt = request.form.get('prompt')

        if not ind:
            return render_template('premium.html', error="Выберите ответ для сохранения")

        ngx = int(ind)
        responses = session.get('premium_responses')

        if not responses or not prompt:
            return render_template('premium.html', error="Сессия устарела")

        user = User.query.filter_by(login=session['user']).first()
        if not user:
            return redirect(url_for('login'))

        manager.add_history(prompt, responses[ngx], user.id)

        session.pop('premium_responses', None)
        session.pop('premium_prompt', None)

        return redirect(url_for('premium'))
    except Exception as e:
        return render_template('error.html', error=str(e))


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        login = request.form.get('login')
        password = request.form.get('password')

        try:
            user = User.query.filter_by(login=login).first()

            if not user:
                return render_template('login.html', error="Логин не найден")

            code1 = bin(len(password))
            code2 = bin(len(login))
            code3 = hashlib.md5(login.encode()).digest()
            pasw1 = hashlib.md5(password.encode()).digest()
            pasw2 = hashlib.md5(pasw1).hexdigest()
            hash = f"{code1}{code2}{code3}{pasw2}"

            if user.password != hash:
                return render_template('login.html', error="Неверный пароль")

            session['user'] = login
            return redirect(url_for('index'))
        except Exception as e:
            return render_template('login.html', error=f"Ошибка входа: {str(e)}")

    return render_template('login.html')


@app.route('/logout')
def logout():
    session.pop('user', None)
    return redirect(url_for('index'))


@app.route('/profile', methods=['GET', 'POST'])
def profile():
    if 'user' not in session:
        return redirect(url_for('login'))

    user = User.query.filter_by(login=session['user']).first()
    if not user:
        return redirect(url_for('login'))

    if request.method == 'POST':
        try:
            new_name = request.form.get('name')
            new_password = request.form.get('password')

            if new_name:
                user.name = new_name

            if new_password:
                if len(new_password) < 8:
                    return render_template('profile.html', user=user, error="Пароль должен быть не короче 8 символов")

                code1 = bin(len(new_password))
                code2 = bin(len(user.login))
                code3 = hashlib.md5(user.login.encode()).digest()
                pasw1 = hashlib.md5(new_password.encode()).digest()
                pasw2 = hashlib.md5(pasw1).hexdigest()
                user.password = f"{code1}{code2}{code3}{pasw2}"

            db.session.commit()
            return redirect(url_for('profile'))
        except Exception as e:
            db.session.rollback()
            return render_template('profile.html', user=user, error=f"Ошибка обновления: {str(e)}")

    return render_template('profile.html', user=user)


if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)
