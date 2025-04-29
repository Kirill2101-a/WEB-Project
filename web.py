from flask import Flask, render_template, request, redirect, url_for
import csv
from gigachat import GigaChat
from langchain_core.messages import HumanMessage
from langchain_community.chat_models.gigachat import GigaChat
import sqlite3

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

    def get_connection(self):
        return sqlite3.connect("project.sqlite")

    def add_history(self, prompt, response): #НЕ РАБОТАЕТ НАДО ПОЧИНИТЬ
        con = self.get_connection()
        cur = con.cursor()
        cur.execute(
            "INSERT INTO result(input, output, length, tag) VALUES (?, ?, ?, 0)",
            (prompt, response, len(response))
        )
        con.commit()
        cur.close()
        con.close()

    def get_history(self):
        con = self.get_connection()
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


@app.route('/generate', methods=['POST'])
def generate():
    global conditions_accepted
    if not conditions_accepted:
        return render_template('index.html', error="Примите условия генерации")

    prompt = request.form.get('prompt')
    if not prompt:
        return render_template('index.html', error="Пустой запрос")

    response = generator.generate(prompt)
    print(response)
    manager.add_history(prompt, response)
    print(1)
    return render_template('index.html', output=response)


@app.route('/history')
def show_history():
    history = manager.get_history()
    print(history)
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



if __name__ == '__main__':
    app.run(debug=True)
