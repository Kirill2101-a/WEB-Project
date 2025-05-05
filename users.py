from database import db

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    login = db.Column(db.Text, unique=True, nullable=False)
    password = db.Column(db.Text, nullable=False)
    name = db.Column(db.Text)