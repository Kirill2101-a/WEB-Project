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
    def add_history(self, prompt, response, user_id):
        con = sqlite3.connect("project.sqlite")
        cur = con.cursor()
        cur.execute(
            "INSERT INTO result(input, output, lenght, tag, user_id) VALUES (?, ?, ?, 0, ?)",
            (prompt, response, len(response), user_id)
        )
        con.commit()

    def get_history(self, user_id, search_query=None, search_type='both'):
        con = sqlite3.connect("project.sqlite")
        cur = con.cursor()

        query = "SELECT * FROM result WHERE user_id = ?"
        params = [user_id]

        if search_query:
            search_term = f"%{search_query}%"
            if search_type == 'prompt':
                query += " AND input LIKE ?"
                params.append(search_term)
            elif search_type == 'response':
                query += " AND output LIKE ?"
                params.append(search_term)
            else:
                query += " AND (input LIKE ? OR output LIKE ?)"
                params.extend([search_term, search_term])

        rows = cur.execute(query, tuple(params)).fetchall()
        con.close()
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
    con = sqlite3.connect("project.sqlite")
    cur = con.cursor()
    user_id = cur.execute("SELECT id FROM users WHERE login = ?", (session['user'],)).fetchone()[0]
    con.close()

    global conditions_accepted
    if not conditions_accepted:
        return render_template('index.html', error="Примите условия генерации")

    prompt = request.form.get('prompt')
    if not prompt:
        return render_template('index.html', error="Пустой запрос")

    response = generator.generate(prompt)
    manager.add_history(prompt, response, user_id)
    return render_template('index.html', output=response)


@app.route('/history')
def show_history():
    if 'user' not in session:
        return redirect(url_for('login'))

    con = sqlite3.connect("project.sqlite")
    cur = con.cursor()
    user_id = cur.execute("SELECT id FROM users WHERE login = ?", (session['user'],)).fetchone()[0]
    con.close()

    search_query = request.args.get('search', '')
    search_type = request.args.get('search_type', 'both')

    history = manager.get_history(user_id=user_id,
        search_query=search_query,
        search_type=search_type)

    return render_template('history.html', history=history,
                           search=search_query,
                           search_type=search_type)


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
    con = sqlite3.connect("project.sqlite")
    cur = con.cursor()
    user_id = cur.execute("SELECT id FROM users WHERE login = ?", (session['user'],)).fetchone()[0]
    con.close()
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

        session['premium_responses'] = responses
        session['premium_prompt'] = prompt

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
        code2 = bin(len(login))
        code3 = hashlib.md5(login.encode()).digest()
        pasw1 = hashlib.md5(password.encode()).digest()
        pasw2 = hashlib.md5(pasw1).hexdigest()
        hash = f"{code1}{code2}{code3}{pasw2}"

        cur.execute(
            "INSERT INTO users (login, password, name) VALUES (?, ?, ?)",
            (login, hash, name)
        )
        con.commit()
        con.close()

        session['user'] = login
        return redirect(url_for('index'))

    return render_template('register.html')


@app.route('/premium/save', methods=['POST'])
def save_premium_response():
    if 'user' not in session:
        return redirect(url_for('login'))

    ind = request.form.get('selected_response')
    prompt = request.form.get('prompt')

    if not ind:
        return render_template('premium.html', error="Выберите ответ для сохранения")
    ngx = int(ind)


    responses = session.get('premium_responses')
    if not responses or not prompt:
        return render_template('premium.html', error="Сессия устарела")

    con = sqlite3.connect("project.sqlite")
    cur = con.cursor()
    user_id = cur.execute("SELECT id FROM users WHERE login = ?", (session['user'],)).fetchone()[0]
    con.close()

    manager.add_history(prompt, responses[ngx], user_id)

    session.pop('premium_responses', None)
    session.pop('premium_prompt', None)

    return redirect(url_for('premium'))


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
        code2 = bin(len(login))
        code3 = hashlib.md5(login.encode()).digest()
        pasw1 = hashlib.md5(password.encode()).digest()
        pasw2 = hashlib.md5(pasw1).hexdigest()
        hash = f"{code1}{code2}{code3}{pasw2}"

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
