from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from app.forms import EventForm
from app.models import Event, EventAttendance
from app import db, mail, app
from flask_mail import Message
from datetime import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import logging
import uuid
import os
import smtplib
import secrets
from PIL import Image
from werkzeug.utils import secure_filename



events = Blueprint('events', __name__)

def save_event_image(form_image):
    try:
        if not hasattr(form_image, 'filename'):
            raise ValueError("Invalid file object")

        random_hex = secrets.token_hex(8)
        _, f_ext = os.path.splitext(form_image.filename)
        picture_fn = random_hex + f_ext
        picture_path = os.path.join(app.root_path, 'static/event_images', picture_fn)

        output_size = (500, 500)
        i = Image.open(form_image)
        i.thumbnail(output_size)
        i.save(picture_path)

        return picture_fn
    except Exception as e:
        flash(f'An error occurred while saving the file: {e}', 'danger')
        return None

@events.route('/events', methods=['GET'])
@login_required
def events_view():
    events = Event.query.filter(Event.date >= datetime.now()).all()
    attendence = EventAttendance.query.filter_by(user_id=current_user.id).all()
    return render_template('events.html', events=events, attendence=attendence, EventAttendance=EventAttendance)

@events.route('/events/<int:event_id>')
@login_required
def events_detail(event_id):
    event_attendees = EventAttendance.query.all()
    event = Event.query.get_or_404(event_id)
    return render_template('event_detail.html', name=event.name, event=event, event_attendees=event_attendees, EventAttendance=EventAttendance)

@events.route('/event/create', methods=['GET', 'POST'])
@login_required
def create_event():
    if current_user.role != "admin":
        flash('You do not have permission to access this page.', 'danger')
        return redirect(url_for('events.events_view'))
    
    form = EventForm()
    if form.validate_on_submit():
        event_image = save_event_image(form.event_image.data)
        event = Event(name=form.name.data,
                      date=form.date.data,
                      description=form.description.data,
                      max_attendees=form.max_attendees.data,
                      event_type=form.event_type.data,
                      virtual_link=form.virtual_link.data,
                      )
        if event_image:
            image_file = save_event_image(form.event_image.data)
            event.event_image = image_file
        else:
            event.event_image = None
        db.session.add(event)
        db.session.commit()
        flash('Event created successfully!', 'success')
        return redirect(url_for('events.events_view'))
    return render_template('create_event.html', title='Create Event', form=form, legend='Create Event')


def generate_confirmation_code(event, user):
    """Generates a unique confirmation code based on UUID and timestamp."""
    return f"{uuid.uuid4()}-{datetime.utcnow().timestamp()}"

def build_email_body(event, user, confirmation_code):
    """Builds the HTML body for the confirmation email."""
    link_message = (f'Here is your link to join the virtual event: <a href="{event.virtual_link}">{event.virtual_link}</a>'
                    if event.event_type == 'virtual'
                    else "Please bring this confirmation to the event for entry.")
    return f'''
<!DOCTYPE html>
<html>
<head>
    <style>
        body {{
            font-family: Arial, sans-serif;
            color: #333;
        }}
        .container {{
            margin: 0 auto;
            padding: 20px;
            max-width: 600px;
            background-color: #f9f9f9;
            border: 1px solid #ddd;
            border-radius: 5px;
        }}
        .header {{
            font-size: 24px;
            margin-bottom: 20px;
            color: #4CAF50;
        }}
        .event-details {{
            margin-bottom: 20px;
        }}
        .footer {{
            font-size: 12px;
            color: #777;
            margin-top: 20px;
        }}
        .social-icons img {{
            width: 24px;
            height: 24px;
            margin-right: 10px;
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">Event Registration Confirmation</div>
        <p>Dear {user.username},</p>
        <p>Thank you for registering for the event: <strong>{event.name}</strong>.</p>
        <div class="event-details">
            <p><strong>Event Details:</strong></p>
            <p>📅 <strong>Name:</strong> {event.name}</p>
            <p>📆 <strong>Date:</strong> {event.date}</p>
            <p>📝 <strong>Description:</strong> {event.description}</p>
            <p>🏷️ <strong>Event Type:</strong> {event.event_type}</p>
            <p>🔒 <strong>Confirmation Code:</strong> {confirmation_code}</p>
            <p>{link_message}</p>
        </div>
        <p>We look forward to seeing you there!</p>
        <p>Best Regards,<br>The Events Team</p>
        <div class="footer">
            <p>This message was sent to {user.username} because you registered for the event.</p>
            <p>📧 Contact us: biodiversitynexus@yahoo.com</p>
            <p>🌐 Visit our website: <a href="http://biodiversitynexus.me/">www.biodiversitynexus.me/</a></p>
            <p>📱 Follow us on social media:</p>
            <div class="social-icons">
                <a href="https://https://www.facebook.com/profile.php?id=61563059986794"><img src="https://img.icons8.com/color/48/000000/facebook.png" alt="Facebook"></a>
                <a href="https://x.com/Biod_Nexus"><img src="https://img.icons8.com/color/48/000000/twitter.png" alt="Twitter"></a>
                <a href="https://www.instagram.com/biodiversitynexus/"><img src="https://img.icons8.com/color/48/000000/instagram-new.png" alt="Instagram"></a>
                <a href="https://www.linkedin.com/company/biodiversity-nexus/company/example"><img src="https://img.icons8.com/color/48/000000/linkedin.png" alt="LinkedIn"></a>
            </div>
        </div>
    </div>
</body>
</html>
'''

def send_confirmation_email(event, user, confirmation_code):
    """Sends a confirmation email to the user."""
    max_retries = 3
    for attempt in range(max_retries):
        try:
            msg = MIMEMultipart()
            msg['From'] = os.getenv("MAIL_USERNAME")
            msg['To'] = user.email
            msg['Subject'] = 'Event Registration Confirmation'

            body = build_email_body(event, user, confirmation_code)
            msg.attach(MIMEText(body, 'html', 'utf-8'))

            server = smtplib.SMTP(os.getenv("MAIL_SERVER"), int(os.getenv("MAIL_PORT")))
            server.starttls()
            server.login(os.getenv("MAIL_USERNAME"), os.getenv("MAIL_PASSWORD"))
            server.sendmail(msg['From'], msg['To'], msg.as_bytes())  # Use as_bytes() instead of as_string()
            server.quit()
            return True
        except (smtplib.SMTPServerDisconnected, smtplib.SMTPException) as e:
            logging.error(f"Failed to send confirmation email (attempt {attempt + 1}/{max_retries}): {e}")
            if attempt == max_retries - 1:
                return False

@events.route('/event/register/<int:id>', methods=['GET', 'POST'])
@login_required
def register_event(id):
    event = Event.query.get_or_404(id)
    existing_registration = EventAttendance.query.filter_by(user_id=current_user.id, event_id=id).first()

    if existing_registration:
        flash('You are already registered for this event.', 'warning')
        return redirect(url_for('events.events_view'))

    if event.is_full():
        flash('Event is already full.', 'warning')
        return redirect(url_for('events.events_view'))

    confirmation_code = generate_confirmation_code(event, current_user)
    if send_confirmation_email(event, current_user, confirmation_code):
        try:
            attendance = EventAttendance(user_id=current_user.id, event_id=event.id, confirmation_code=confirmation_code)
            db.session.add(attendance)
            db.session.commit()
            flash('Registered for the event successfully. Confirmation email sent.', 'success')
        except Exception as e:
            db.session.rollback()
            logging.error(f"Failed to register for the event: {e}")
            flash('Failed to register for the event. Please try again later.', 'danger')
    else:
        flash('Failed to send confirmation email. Please try to register for the event again later.', 'danger')

    return redirect(url_for('events.events_view'))

@events.route('/event/<int:event_id>/update', methods=['GET', 'POST'])
@login_required
def update_event(event_id):
    events = Event.query.get_or_404(event_id)
    if not current_user.role == "admin":
        flash('You do not have permission to access this page.', 'danger')
        return redirect(url_for('events.event_view'))

    form = EventForm()
    if form.validate_on_submit():
        events.name = form.name.data
        events.date = form.date.data
        events.description = form.description.data
        events.max_attendees = form.max_attendees.data
        events.event_type = form.event_type.data
        events.virtual_link = form.virtual_link.data
        events.event_image = form.event_image.data
        db.session.commit()
        flash('Your project has been updated!', 'success')
        return redirect(url_for('projects.project_list'))
    elif request.method == 'GET':
        
        form.name.data = events.name
        form.date.data = events.date
        form.description.data = events.description
        form.max_attendees.data = events.max_attendees
        form.event_type.data = events.event_type
        form.virtual_link.data = events.virtual_link
        form.event_image.data = events.event_image
    return render_template('create_event.html', title='Update Event', form=form, legend='Update Event')

@events.route('/event/cancel_registration/<int:id>', methods=['POST'])
@login_required
def cancel_registration(id):
    attendance = EventAttendance.query.filter_by(user_id=current_user.id, event_id=id).first()
    if attendance:
        db.session.delete(attendance)
        db.session.commit()
        flash('Event registration canceled successfully.', 'success')
    else:
        flash('You are not registered for this event.', 'warning')
    return redirect(url_for('events.events_view'))

@events.route('/event/delete/<int:event_id>')
@login_required
def delete_event(event_id):
    if current_user.role != 'admin':
        return redirect(url_for('manage_events.manage_events_view'))
    
    event = Event.query.get_or_404(id)
    
    # Delete related event attendance records
    event_attendances = EventAttendance.query.filter_by(event_id=id).all()
    for attendance in event_attendances:
        db.session.delete(attendance)
    
    db.session.delete(event)
    db.session.commit()
    
    flash('Event deleted successfully!', 'success')
    return redirect(url_for('events.events_view', event_id=event.id))

@events.route('/admin/events', methods=['GET'])
@login_required
def admin_events_view():
    """Displays a list of all events for admin."""
    if current_user.role != "admin":
        flash('You do not have permission to access this page.', 'danger')
        return redirect(url_for('main.index'))

    events = Event.query.all()
    return render_template('admin/admin_events.html', events=events)