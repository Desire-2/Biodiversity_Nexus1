from flask_wtf import FlaskForm
from flask_login import current_user
from wtforms import StringField, PasswordField, SubmitField, TextAreaField, SelectField, DecimalField, IntegerField, FileField, DateTimeField, HiddenField
from wtforms.validators import DataRequired, Email, Length, EqualTo, ValidationError, NumberRange, Optional, URL
from app.models import User
from flask_wtf.file import FileAllowed, FileRequired

class RegisterForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired()])
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[DataRequired(), Length(min=6)])
    confirm_password = PasswordField('Confirm Password', validators=[DataRequired(), EqualTo('password')])
    submit = SubmitField('Register')
    
    def validate_username(self, username):
       if current_user.is_authenticated and username.data != current_user.username:
           user = User.query.filter_by(username=username.data).first()
           if user:
               raise ValidationError('That username is taken. Please choose a different one.')

    def validate_email(self, email):
        user = User.query.filter_by(email=email.data).first()
        if user:
            raise ValidationError('That email is taken. Please choose a different one.')

class EditProfileForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired()])
    email = StringField('Email', validators=[DataRequired(), Email()])
    picture = FileField('Update Profile Picture', validators=[FileAllowed(['jpg', 'png'])])
    submit = SubmitField('Update')

class LoginForm(FlaskForm):
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[DataRequired()])
    remember = StringField('Remember Me')
    submit = SubmitField('Login')

class EventForm(FlaskForm):
    name = StringField('Event Name', validators=[DataRequired()])
    date = DateTimeField('Event Date', format='%Y-%m-%d %H:%M', validators=[DataRequired()], render_kw={"placeholder": "Select date and time"})
    description = HiddenField('Event Description', validators=[DataRequired()])
    max_attendees = IntegerField('Max Number of Attendees', validators=[DataRequired(), NumberRange(min=1)])
    event_type = SelectField('Event Type', choices=[('virtual', 'Virtual'), ('face-to-face', 'Face-to-Face')], validators=[DataRequired()])
    virtual_link = StringField('Virtual Event Link', validators=[Optional(), URL()])
    event_image = FileField('Event Image', validators=[FileAllowed(['jpg', 'png', 'jpeg', 'heic'], 'Images only!')])
    submit = SubmitField('Submit')

class EventAttendanceForm(FlaskForm):
    user_id = SelectField('User', coerce=int, validators=[DataRequired()])
    submit = SubmitField('Register')

class SearchForm(FlaskForm):
    query = StringField('Search', validators=[DataRequired()])
    submit = SubmitField('Search')

class MessageForm(FlaskForm):
    recipient = SelectField('Recipient', coerce=int, validators=[DataRequired()])
    content = TextAreaField('Message Content', validators=[DataRequired()])
    submit = SubmitField('Send Message')
    
class DonationForm(FlaskForm):
    name = StringField('Name', validators=[DataRequired()])
    email = StringField('Email', validators=[DataRequired(), Email()])
    amount = DecimalField('Amount ($)', validators=[DataRequired(), NumberRange(min=1)])
    submit = SubmitField('Donate')
    
class EditUserForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired()])
    email = StringField('Email', validators=[DataRequired(), Email()])
    role = SelectField('Role', choices=[('user', 'User'), ('admin', 'Admin')], validators=[DataRequired()])
    submit = SubmitField('Update')
    
class ProjectForm(FlaskForm):
    title = StringField('Title', validators=[DataRequired()])
    description = HiddenField('Description', validators=[DataRequired()])
    status = SelectField('Status', choices=[('upcoming', 'Upcoming'), ('completed', 'Completed'), ('on hold', 'On Hold')], validators=[DataRequired()])
    image_url = FileField('Project Image', validators=[FileAllowed(['jpg', 'png', 'jpeg'], 'Images only!')])
    progress = IntegerField('Progress', validators=[DataRequired(), NumberRange(min=0, max=100)])
    submit = SubmitField('Submit')
    
class VolunteerForm(FlaskForm):
    name = StringField('Name', validators=[DataRequired()])
    email = StringField('Email', validators=[DataRequired(), Email()])
    submit = SubmitField('Sign Up')
    
class GalleryItemForm(FlaskForm):
    title = StringField('Title', validators=[DataRequired()])
    description = TextAreaField('Description')
    file = FileField('File', validators=[DataRequired()])
    category = SelectField('Category', choices=[('Uncategorized', 'Uncategorized'), ('Nature', 'Nature'), ('Wildlife', 'Wildlife'), ('Events', 'Events')], validators=[DataRequired()])
    tags = StringField('Tags (comma separated)')
    location = StringField('Location')
    date_taken = DateTimeField('Date Taken', format='%Y-%m-%d')
    submit = SubmitField('Add to Gallery')

class PostForm(FlaskForm):
    title = StringField('Title', validators=[DataRequired()])
    content = TextAreaField('Content', validators=[DataRequired()])
    submit = SubmitField('Post')

class ThreadForm(FlaskForm):
    title = StringField('Title', validators=[DataRequired()])
    submit = SubmitField('Create Thread')

class CommentForm(FlaskForm):
    content = TextAreaField('Content', validators=[DataRequired()])
    submit = SubmitField('Comment')