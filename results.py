from database import db
from users import User

class Result(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    input = db.Column(db.Text, nullable=False)
    output = db.Column(db.Text, nullable=False)
    lenght = db.Column(db.Integer)
    tag = db.Column(db.Integer, default=0)
    user_id = db.Column(db.Integer, db.ForeignKey(User.id), nullable=False)