from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_migrate import Migrate
from flask_bcrypt import Bcrypt
import paypalrestsdk
from flask_mail import Mail
from dotenv import load_dotenv
import os
import datetime
from werkzeug.utils import secure_filename
from flask_wtf.csrf import CSRFProtect
from flask_socketio import SocketIO

# Load environment variables from .env file
load_dotenv()

app = Flask(__name__)


# Set up configurations using environment variables
app.config["SECRET_KEY"] = os.getenv("SECRET_KEY")
app.config["SQLALCHEMY_DATABASE_URI"] = os.getenv("SQLALCHEMY_DATABASE_URI")
app.config["UPLOAD_FOLDER"] = "static/uploads"
app.config["MAIL_SERVER"] = os.getenv("MAIL_SERVER")
app.config["MAIL_PORT"] = int(os.getenv("MAIL_PORT"))
app.config["MAIL_USE_TLS"] = os.getenv("MAIL_USE_TLS").lower() in ["true", "1", "t"]
app.config["MAIL_USERNAME"] = os.getenv("MAIL_USERNAME")
app.config["MAIL_PASSWORD"] = os.getenv("MAIL_PASSWORD")
app.config["MAIL_DEFAULT_SENDER"] = os.getenv("MAIL_DEFAULT_SENDER")


app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
    "pool_pre_ping": True,
    "connect_args": {
        "sslmode": "require",
        "sslcompression": 0
        # If your DB requires a CA cert, also add:
        # "sslrootcert": os.getenv("SSL_ROOT_CERT_PATH")
    }
}

# Initialize extensions
db = SQLAlchemy(app)
bcrypt = Bcrypt(app)
login_manager = LoginManager(app)
migrate = Migrate(app, db)
mail = Mail(app)
socketio = SocketIO(app)

csrf = CSRFProtect()
csrf.init_app(app)

# Flask-Login configurations
login_manager.login_view = "auth.login"
login_manager.login_message_category = "info"

# PayPal SDK configuration
paypalrestsdk.configure({
    "mode": os.getenv("PAYPAL_MODE"),  # "sandbox" or "live"
    "client_id": os.getenv("PAYPAL_CLIENT_ID"),
    "client_secret": os.getenv("PAYPAL_CLIENT_SECRET")
})

# Import User model for Flask-Login
from app.models import User

@app.template_filter("time_ago")
def time_ago(dt):
    if not dt:
        return "Unknown time"
    now = datetime.datetime.utcnow()
    diff = now - dt
    secs = diff.total_seconds()
    if secs < 60:
        return f"{int(secs)} seconds ago"
    mins = secs / 60
    if mins < 60:
        return f"{int(mins)} minutes ago"
    hrs = mins / 60
    if hrs < 24:
        return f"{int(hrs)} hours ago"
    days = hrs / 24
    if days < 7:
        return f"{int(days)} days ago"
    weeks = days / 7
    if weeks < 4:
        return f"{int(weeks)} weeks ago"
    months = days / 30
    if months < 12:
        return f"{int(months)} months ago"
    years = days / 365
    return f"{int(years)} years ago"

# Flask-Login user loader
@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# Register blueprints
from app.routes import register_blueprints  
register_blueprints(app)

# Import models to ensure they are registered with SQLAlchemy
from app import models

# Create database tables within application context
#with app.app_context():
    #db.create_all()

# Import SocketIO event handlers
from app import socket_events


