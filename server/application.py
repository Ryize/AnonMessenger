from quart import Quart
from flask_sqlalchemy import SQLAlchemy

application = Quart(__name__)
application.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///app.db'
application.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(application)
