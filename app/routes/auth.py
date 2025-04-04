from flask import Blueprint, render_template, redirect, request, url_for, flash
from flask_login import login_user, logout_user, login_required, current_user
from app.forms import RegisterForm, LoginForm
from app.models import User
from app import db, bcrypt

auth = Blueprint('auth', __name__)

@auth.route("/register", methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('main.index'))
    
    form = RegisterForm()
    
    if form.validate_on_submit():
        # Check if the username or email already exists
        existing_user = User.query.filter((User.username == form.username.data) | (User.email == form.email.data)).first()
        if existing_user:
            flash('Username or email already exists. Please choose a different one.', 'danger')
        else:
            hashed_password = bcrypt.generate_password_hash(form.password.data).decode('utf-8')
            user = User(username=form.username.data, email=form.email.data, password=hashed_password)
            db.session.add(user)
            db.session.commit()
            flash('Your account has been created! You are now able to log in', 'success')
            return redirect(url_for('auth.login'))
    
    return render_template('register.html', title='Register', form=form)

@auth.route("/login", methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('main.index'))
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        if user and bcrypt.check_password_hash(user.password, form.password.data):
            login_user(user, remember=form.remember.data)
            next_page = request.args.get('next')
            flash('Login Successful.', 'success')
            return redirect(next_page) if next_page else redirect(url_for('main.index'))
        else:
            flash('Login Unsuccessful. Please check email and password', 'danger')
    return render_template('login.html', title='Login', form=form)

@auth.route("/admin/add_user", methods=['GET', 'POST'])
@login_required
def admin_add_user():
    if current_user.role != 'admin':
        flash('You do not have permission to access this page.', 'danger')
        return redirect(url_for('main.index'))
    
    form = RegisterForm()
    
    if form.validate_on_submit():
        # Check if the username or email already exists
        existing_user = User.query.filter((User.username == form.username.data) | (User.email == form.email.data)).first()
        if existing_user:
            flash('Username or email already exists. Please choose a different one.', 'danger')
        else:
            hashed_password = bcrypt.generate_password_hash(form.password.data).decode('utf-8')
            user = User(username=form.username.data, email=form.email.data, password=hashed_password)
            db.session.add(user)
            db.session.commit()
            flash('New user has been created successfully!', 'success')
            return redirect(url_for('auth.admin_add_user'))
    
    return render_template('admin/admin_add_user.html', title='Add User', form=form)

@auth.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('main.index'))


