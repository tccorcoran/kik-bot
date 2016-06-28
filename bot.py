import os
from flask import Flask
from flask.ext.sqlalchemy import SQLAlchemy
from kik import KikApi,Configuration



app = Flask(__name__)


DATABASE = {
        'NAME': os.environ['DB_NAME'],
        'USER': os.environ['DB_USERNAME'],
        'PASSWORD': os.environ['DB_PASSWORD'],
        'HOST': os.environ['DB_URL'],
}
DB_URI = 'postgres://{USER}:{PASSWORD}@{HOST}:5432/{NAME}'.format(**DATABASE)

access_token = os.environ.get('WIT_SERVER_ACCESS_TOKEN')
BOT_USERNAME = os.environ.get('BOT_USERNAME')
BOT_API_KEY = os.environ.get('KIK_API_KEY')
WEBHOOK = os.environ.get('WEBHOOK')
kik = KikApi(BOT_USERNAME, BOT_API_KEY)
kik.set_configuration(Configuration(webhook=WEBHOOK))
app.config['SQLALCHEMY_DATABASE_URI'] = DB_URI
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)