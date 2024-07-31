from flask import Blueprint, render_template, redirect, url_for, flash, request, current_app
from flask_login import login_required, current_user
from app.models import Event, Post, Thread, Photo, User, Project, EventAttendance
from app.forms import EditProfileForm
from werkzeug.utils import secure_filename
import os
from app import app, db
from PIL import Image
import secrets


main = Blueprint('main', __name__)

@main.route('/')
def index():
    # Query the top 3 recent events
    recent_events = Event.query.order_by(Event.date.desc()).limit(3).all()
    # Query the most recent project
    recent_projects = Project.query.order_by(Project.date_posted.desc()).limit(3).all()
    
    event_attendees = EventAttendance.query.all()
    
    return render_template('index.html', recent_events=recent_events, event_attendees=event_attendees, recent_projects=recent_projects, EventAttendance=EventAttendance)

@main.route('/about')
def about():
    return render_template('about.html')


@main.route('/posts')
@login_required
def posts():
    posts = Post.query.all()
    return render_template('posts.html', posts=posts)

@main.route('/threads')
@login_required
def threads():
    threads = Thread.query.all()
    return render_template('threads.html', threads=threads)

@main.route('/profile')
@login_required
def profile():
    user = User.query.get(current_user.id)
    return render_template('profile.html', user=user)

def save_picture(form_picture):
    random_hex = secrets.token_hex(8)
    _, f_ext = os.path.splitext(form_picture.filename)
    picture_fn = random_hex + f_ext
    picture_path = os.path.join(current_app.root_path, 'static/profile_pics', picture_fn)

    output_size = (125, 125)
    i = Image.open(form_picture)
    i.thumbnail(output_size)
    i.save(picture_path)

    return picture_fn

@main.route('/edit_profile', methods=['GET', 'POST'])
@login_required
def edit_profile():
    form = EditProfileForm()
    if form.validate_on_submit():
        if form.picture.data:
            picture_file = save_picture(form.picture.data)
            current_user.image_file = picture_file
        current_user.username = form.username.data
        db.session.commit()
        flash('Your account has been updated!', 'success')
        return redirect(url_for('main.edit_profile'))
    elif request.method == 'GET':
        form.username.data = current_user.username
    image_file = url_for('static', filename='profile_pics/' + current_user.image_file)
    return render_template('edit_profile.html', title='Edit Profile', image_file=image_file, form=form)

@main.route('/subscribe')
@login_required
def subscribe():
    return render_template('subscribe.html')
