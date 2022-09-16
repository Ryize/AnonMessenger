from server.application import db


class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.Text, unique=True)

    def __repr__(self):
        return f'{self.code}'

    def __str__(self):
        return f'{self.code}'


class Message(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    sender = db.Column(db.Integer, db.ForeignKey('user.id'))
    recipient = db.Column(db.Integer, db.ForeignKey('user.id'))
    message = db.Column(db.Text, nullable=False)


db.create_all()
