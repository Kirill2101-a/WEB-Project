from flask import Flask, render_template, request, redirect, url_for
import csv
from gigachat import GigaChat
from langchain_core.messages import HumanMessage
from langchain_community.chat_models.gigachat import GigaChat

app = Flask(__name__)
app.secret_key = 'secret'


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
        self.h_file = 'history.csv'

    def add_history(self, prompt, response):
        with open(self.h_file, 'a', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow([prompt, response])

    def get_history(self):
        story = []
        try:
            with open(self.h_file, 'r', encoding='utf-8') as f:
                reader = csv.reader(f)
                for row in reader:
                    story.append({'prompt': row[0], 'response': row[1]})
        except FileNotFoundError:
            pass  # Если файл истории не существует, просто возвращаем пустой список
        return story


generator = Work()
manager = History()


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/generate', methods=['POST'])
def generate():
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
    return render_template('conditions.html')


@app.route('/accept_conditions', methods=['POST'])
def accept_conditions():
    return redirect(url_for('index'))


if __name__ == '__main__':
    app.run(debug=True)
