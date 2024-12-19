from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from urllib.parse import quote
from flask_login import LoginManager
import cloudinary

app = Flask(__name__)
app.secret_key = 'dfdfsfasdasdasdas'
app.config["SQLALCHEMY_DATABASE_URI"] = "mysql+pymysql://root:%s@localhost/bookdb?charset=utf8mb4" % quote('Admin@123')
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = True
app.config["PAGE_SIZE"] = 3

db = SQLAlchemy(app)
login = LoginManager(app)

cloudinary.config(
    cloud_name="dehkjrhjw",
    api_key="631329619766517",
    api_secret="-c_KBF3udbFM441q4CMa29ZwdwE",
    secure=True
)
