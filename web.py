# Серверная часть (Flask)
from flask import Flask, render_template, request, jsonify, session
import csv
from gigachat import GigaChat
from langchain_core.messages import HumanMessage
from langchain_community.chat_models.gigachat import GigaChat

app = Flask(__name__)
app.secret_key = 'secret'


class work:
    def __init__(self):
        self.giga = GigaChat(
            credentials="YWFiNjI4YzUtYWU3ZC00YjM2LTg2ZjgtODU0ZDg5Yjg2MmMyOmJjOTM3NzMzLTVjODYtNDNhOC04MzQwLTM2OWM3MDA4NGE3NA==",
            scope="GIGACHAT_API_PERS",
            model="GigaChat",
            verify_ssl_certs=False
        )

    def generate(self, prompt):
        response = self.giga.invoke([HumanMessage(content=prompt)])
        return response.content


class HistoryManager:
    def __init__(self):
        self.h_file = 'history.csv'

    def add_record(self, prompt, response):
        with open(self.h_file, 'a', newline='') as f:
            write = csv.writer(f)
            write.writerow([prompt, response])

    def get_history(self):
        story = []
        with open(self.h_file, 'r') as f:
            reader = csv.reader(f)
            for i in reader:
                story.append({'prompt': i[0], 'response': i[1]})
        return story


generator = work()
manager = HistoryManager()


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/generate', methods=['POST'])
def generate():
    prompt = request.json.get('prompt')
    if not prompt:
        return jsonify({'error': 'Пустой запрос'}), 400

    sp = generator.generate(prompt)
    manager.add_record(prompt, sp)

    return jsonify({'response': sp})


@app.route('/history')
def show_history():
    ss = manager.get_history()
    return render_template('history.html', history=ss)

if __name__ == '__main__':
    app.run()