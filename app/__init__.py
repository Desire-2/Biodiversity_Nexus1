from flask import Flask, flash
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_migrate import Migrate
from flask_bcrypt import Bcrypt
import paypalrestsdk
from flask_mail import Mail
from dotenv import load_dotenv
import os
from werkzeug.utils import secure_filename

# Load environment variables from .env file
load_dotenv()



app = Flask(__name__)

# Set up configurations using environment variables
app.config['SECRET_KEY'] = os.getenv("SECRET_KEY")
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv("SQLALCHEMY_DATABASE_URI")
app.config['UPLOAD_FOLDER'] = 'static/uploads'
app.config['MAIL_SERVER'] = os.getenv("MAIL_SERVER")
app.config['MAIL_PORT'] = int(os.getenv("MAIL_PORT"))
app.config['MAIL_USE_TLS'] = os.getenv("MAIL_USE_TLS").lower() in ['true', '1', 't']
app.config['MAIL_USERNAME'] = os.getenv("MAIL_USERNAME")
app.config['MAIL_PASSWORD'] = os.getenv("MAIL_PASSWORD")
app.config['MAIL_DEFAULT_SENDER'] = os.getenv("MAIL_DEFAULT_SENDER")

# Initialize extensions
db = SQLAlchemy(app)
bcrypt = Bcrypt(app)
login_manager = LoginManager(app)
migrate = Migrate(app, db)
mail = Mail(app)

# Flask-Login configurations
login_manager.login_view = 'auth.login'
login_manager.login_message_category = 'info'

# PayPal SDK configuration
paypalrestsdk.configure({
    "mode": os.getenv("PAYPAL_MODE"),  # 'sandbox' or 'live'
    "client_id": os.getenv("PAYPAL_CLIENT_ID"),
    "client_secret": os.getenv("PAYPAL_CLIENT_SECRET")
})

# --- Firebase Admin SDK Integration ---
import firebase_admin
from firebase_admin import credentials, firestore

firebase_cert_path = os.getenv("FIREBASE_CERT")
if not firebase_cert_path:
    raise ValueError("FIREBASE_CERT environment variable is not set.")

# Initialize the Firebase Admin SDK with your service account key
cred = credentials.Certificate(firebase_cert_path)
firebase_admin.initialize_app(cred)
# Create a Firestore client (you can also initialize other Firebase services here)
firestore_db = firestore.client()
# --- End Firebase Integration ---

# Import User model for Flask-Login
from app.models import User

# Flask-Login user loader
@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# Register blueprints
from app.routes import register_blueprints  
register_blueprints(app)

# Import models to ensure they are registered with SQLAlchemy
from app import models