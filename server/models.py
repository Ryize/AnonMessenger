from datetime import datetime

from server.application import db, DATETIME_TEMPLATE
from server.crypt import Crypt


class ORMMixin:
    @classmethod
    def create(cls, **kwargs):
        obj = cls(**kwargs)
        db.session.add(obj)
        db.session.commit()
        return obj


class User(db.Model, ORMMixin):
    id = db.Column(db.Integer, primary_key=True)
    login = db.Column(db.String(24), unique=True)

    def __repr__(self):
        return f'{self.code}'

    def __str__(self):
        return f'{self.code}'


class Message(db.Model, ORMMixin):
    id = db.Column(db.Integer, primary_key=True)
    sender = db.Column(db.Integer, db.ForeignKey('user.id'))
    recipient = db.Column(db.Integer, db.ForeignKey('user.id'))
    message = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_list(self) -> dict:
        sender = User.query.get(self.sender).login
        recipient = User.query.get(self.recipient).login
        return {
            'id': self.id,
            'sender': sender,
            'recipient': recipient,
            'message': self.message,
            'created_at': self.created_at.strftime(DATETIME_TEMPLATE)
        }


db.create_all()
