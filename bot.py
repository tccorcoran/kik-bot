import os
from flask import Flask
from flask.ext.sqlalchemy import SQLAlchemy
from kik import KikApi,Configuration


app = Flask(__name__)

access_token = os.environ.get('WIT_SERVER_ACCESS_TOKEN')
BOT_USERNAME = os.environ.get('BOT_USERNAME')
BOT_API_KEY = os.environ.get('KIK_API_KEY')
WEBHOOK = os.environ.get('WEBHOOK')
kik = KikApi(BOT_USERNAME, BOT_API_KEY)
kik.set_configuration(Configuration(webhook=WEBHOOK))
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ['DATABASE_URL']
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)