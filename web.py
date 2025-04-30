from flask import Flask, render_template, request, redirect, url_for
from gigachat import GigaChat
from langchain_core.messages import HumanMessage
from langchain_community.chat_models.gigachat import GigaChat
import sqlite3
from flask import session
import hashlib


app = Flask(__name__)
app.secret_key = 'secret'
conditions_accepted = False

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
    def __init__(self):
        pass


    def add_history(self, prompt, response):
        con = sqlite3.connect("project.sqlite")
        cur = con.cursor()
        cur.execute(
            "INSERT INTO result(input, output, lenght, tag) VALUES (?, ?, ?, 0)",
            (prompt, response, len(response))
        )
        con.commit()


    def get_history(self):
        con = sqlite3.connect("project.sqlite")
        cur = con.cursor()
        rows = cur.execute("SELECT * FROM result").fetchall()
        cur.close()
        con.close()
        print(rows)
        return [{'prompt': row[1], 'response': row[2]} for row in rows]


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

    response = generator.generate(prompt)
    manager.add_history(prompt, response)
    return render_template('index.html', output=response)


@app.route('/history')
def show_history():
    history = manager.get_history()
    return render_template('history.html', history=history)


@app.route('/conditions')
def show_conditions():
    global conditions_accepted
    if request.args.get('accept') == '1':
        conditions_accepted = True
        return redirect(url_for('index'))
    return render_template('conditions.html')


@app.route('/premium', methods=['GET', 'POST'])
def premium():
    global conditions_accepted
    if not conditions_accepted:
        return render_template('premium.html', error="Примите условия генерации")

    if request.method == 'POST':
        prompt = request.form.get('prompt')
        if not prompt:
            return render_template('premium.html', error="Пустой запрос")

        responses = [
            generator.generate(prompt + " Очень подробно, подумай хорошо"),
            generator.generate(prompt + " Без ошибок, но кратко"),
            generator.generate(prompt + " Просто, но правильно")
        ]

        for i in responses:
            manager.add_history(prompt, i)

        return render_template('premium.html', responses=responses, prompt=prompt)

    return render_template('premium.html')


@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        login = request.form.get('login')
        password = request.form.get('password')
        name = request.form.get('name')

        con = sqlite3.connect("project.sqlite")
        cur = con.cursor()


        existing_user = cur.execute("SELECT * FROM users WHERE login = ?", (login,)).fetchone()
        if existing_user:
            con.close()
            return render_template('register.html', error="Логин уже занят")

        if len(password) < 8:
            return render_template('register.html', error="Пароль должен быть не короче 8 символов")

        code1 = bin(len(password))
        pasw1 = hashlib.md5(password.encode()).digest()
        pasw2 = hashlib.md5(pasw1).hexdigest()
        hash = f"{code1}{pasw2}"

        cur.execute(
            "INSERT INTO users (login, password, name) VALUES (?, ?, ?)",
            (login, hash, name)
        )
        con.commit()
        con.close()

        session['user'] = login
        return redirect(url_for('index'))

    return render_template('register.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        login = request.form.get('login')
        password = request.form.get('password')

        con = sqlite3.connect("project.sqlite")
        cur = con.cursor()
        user = cur.execute("SELECT * FROM users WHERE login = ?", (login,)).fetchone()
        con.close()

        if not user:
            return render_template('login.html', error="Логин не найден")


        code1 = bin(len(password))
        pasw1 = hashlib.md5(password.encode()).digest()
        pasw2 = hashlib.md5(pasw1).hexdigest()
        hash = f"{code1}{pasw2}"

        if user[2] != hash:
            return render_template('login.html', error="Неверный пароль")

        session['user'] = login
        return redirect(url_for('index'))

    return render_template('login.html')


@app.route('/logout')
def logout():
    session.pop('user', None)
    return redirect(url_for('index'))


if __name__ == '__main__':
    app.run(debug=True)
