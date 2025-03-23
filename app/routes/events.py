import os
import uuid
import smtplib
import secrets
import logging
from datetime import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from functools import wraps
from PIL import Image
from sqlalchemy.exc import IntegrityError
import traceback

from flask import Blueprint, render_template, redirect, url_for, flash, request, current_app
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename

from app import db
from app.forms import EventForm
from app.models import Event, EventAttendance

events = Blueprint('events', __name__)

# Allowed image extensions
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}


def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def save_event_image(form_image):
    """
    Saves an uploaded image to the static folder with a unique name.
    Returns the filename if successful; otherwise, returns None.
    """
    try:
        if not hasattr(form_image, 'filename') or form_image.filename == '':
            flash("No image file provided.", "warning")
            return None

        if not allowed_file(form_image.filename):
            flash("File type not allowed. Allowed types: png, jpg, jpeg, gif", "warning")
            return None

        # Use secure_filename to prevent directory traversal issues
        filename = secure_filename(form_image.filename)
        random_hex = secrets.token_hex(8)
        _, f_ext = os.path.splitext(filename)
        picture_fn = random_hex + f_ext
        picture_path = os.path.join(current_app.root_path, 'static/event_images', picture_fn)

        output_size = (500, 500)
        i = Image.open(form_image)
        i.thumbnail(output_size)
        i.save(picture_path)

        return picture_fn
    except Exception as e:
        logging.error(f"Error saving event image: {e}")
        flash(f'An error occurred while saving the image: {e}', 'danger')
        return None


def admin_required(f):
    """
    Decorator to restrict routes to admin users.
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if current_user.role != "admin":
            flash('You do not have permission to access this page.', 'danger')
            return redirect(url_for('events.events_view'))
        return f(*args, **kwargs)
    return decorated_function


@events.route('/events', methods=['GET'])
@login_required
def events_view():
    now = datetime.now()
    upcoming_events = Event.query.filter(Event.date >= now).all()
    past_events = Event.query.filter(Event.date < now).all()
    attendance = EventAttendance.query.filter_by(user_id=current_user.id).all()
    return render_template('events.html',
                           upcoming_events=upcoming_events,
                           attendance=attendance,
                           past_events=past_events,
                           EventAttendance=EventAttendance)


@events.route('/events/<int:event_id>')
@login_required
def events_detail(event_id):
    event = Event.query.get_or_404(event_id)
    # Only fetch attendance records for this event
    event_attendees = EventAttendance.query.filter_by(event_id=event_id).all()
    return render_template('event_detail.html',
                           event=event,
                           event_attendees=event_attendees,
                           EventAttendance=EventAttendance)


@events.route('/event/create', methods=['GET', 'POST'])
@login_required
@admin_required
def create_event():
    form = EventForm()
    if form.validate_on_submit():
        image_file = None
        if form.event_image.data:
            image_file = save_event_image(form.event_image.data)

        event = Event(
            name=form.name.data,
            date=form.date.data,
            description=form.description.data,
            max_attendees=form.max_attendees.data,
            event_type=form.event_type.data,
            virtual_link=form.virtual_link.data,
            event_image=image_file
        )
        try:
            db.session.add(event)
            db.session.commit()
            flash('Event created successfully!', 'success')
            return redirect(url_for('events.admin_events_view'))
        except Exception as e:
            db.session.rollback()
            logging.error(f"Error creating event: {e}")
            flash('Failed to create event. Please try again later.', 'danger')
    return render_template('create_event.html',
                           title='Create Event',
                           form=form,
                           legend='Create Event')


def generate_confirmation_code(event, user):
    """Generates a unique confirmation code based on UUID and timestamp."""
    return f"{uuid.uuid4()}-{datetime.utcnow().timestamp()}"


def build_email_body(event, user, confirmation_code):
    """Builds the HTML body for the confirmation email."""
    link_message = (f'Here is your link to join the virtual event: '
                    f'<a href="{event.virtual_link}">{event.virtual_link}</a>'
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
                <a href="https://www.facebook.com/profile.php?id=61563059986794"><img src="https://img.icons8.com/color/48/000000/facebook.png" alt="Facebook"></a>
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
    """Sends a confirmation email to the user with retries."""
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
            server.sendmail(msg['From'], msg['To'], msg.as_bytes())
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
    existing_registration = EventAttendance.query.filter_by(
        user_id=current_user.id, 
        event_id=id
    ).first()

    if existing_registration:
        flash('You are already registered for this event.', 'warning')
        return redirect(url_for('events.events_view'))

    if event.is_full():
        flash('Event is already full.', 'warning')
        return redirect(url_for('events.events_view'))

    try:
        # Generate confirmation code first
        confirmation_code = generate_confirmation_code(event, current_user)
        
        # Create attendance record
        attendance = EventAttendance(
            user_id=current_user.id,
            event_id=event.id,
            confirmation_code=confirmation_code
        )
        
        # Add to session and commit first
        db.session.add(attendance)
        db.session.commit()
        
        # Only send email AFTER successful commit
        if send_confirmation_email(event, current_user, confirmation_code):
            flash('Registered successfully! Confirmation email sent.', 'success')
        else:
            flash('Registration successful, but confirmation email failed to send.', 'warning')
            
    except IntegrityError as e:
        db.session.rollback()
        logging.error(f"Integrity Error: {str(e.orig)}")
        if "confirmation_code" in str(e.orig):
            flash('Confirmation code collision - please retry', 'danger')
        elif "_user_event_uc" in str(e.orig):
            flash('Already registered for this event', 'warning')
        else:
            flash('Registration failed due to database conflict', 'danger')

    except Exception as e:
        db.session.rollback()
        logging.error(f"Error Type: {type(e)}")
        logging.error(f"Error Message: {str(e)}")
        logging.error(traceback.format_exc())
        flash('Failed to complete registration. Please try again.', 'danger')

    return redirect(url_for('events.events_view'))


@events.route('/event/<int:event_id>/update', methods=['GET', 'POST'])
@login_required
@admin_required
def update_event(event_id):
    event = Event.query.get_or_404(event_id)
    form = EventForm(obj=event)  # Prepopulate form with existing event data

    if form.validate_on_submit():
        form.populate_obj(event)  # Efficiently update the event object

        # Handle event image update
        if form.event_image.data:
            image_file = save_event_image(form.event_image.data)
            if image_file:
                event.event_image = image_file  # Update image only if a new one is provided

        try:
            db.session.commit()
            flash('Event updated successfully!', 'success')
            return redirect(url_for('events.events_view'))
        except Exception as e:
            db.session.rollback()
            logging.error(f"Error updating event: {e}")
            flash('Failed to update event. Please try again later.', 'danger')

    return render_template('create_event.html',
                           title='Update Event',
                           form=form,
                           legend='Update Event')



@events.route('/event/cancel_registration/<int:id>', methods=['POST'])
@login_required
def cancel_registration(id):
    attendance = EventAttendance.query.filter_by(user_id=current_user.id, event_id=id).first()
    if attendance:
        try:
            db.session.delete(attendance)
            db.session.commit()
            flash('Event registration canceled successfully.', 'success')
        except Exception as e:
            db.session.rollback()
            logging.error(f"Error canceling registration: {e}")
            flash('Failed to cancel registration. Please try again later.', 'danger')
    else:
        flash('You are not registered for this event.', 'warning')
    return redirect(url_for('events.events_view'))


@events.route('/event/<int:event_id>/delete', methods=['POST'])
@login_required
def delete_event(event_id):
    event = Event.query.get_or_404(event_id)
    try:
        # Check if the event has any attendees
        attendees = EventAttendance.query.filter_by(event_id=event.id).all()
        if attendees:
            flash('Cannot delete event with registered attendees.', 'warning')
            return redirect(url_for('events.events_view'))
        
        # Delete the event
        db.session.delete(event)
        db.session.commit()
        
        flash('Event deleted successfully!', 'success')
    except Exception as e:
        db.session.rollback()
        logging.error(f"Error deleting event: {e}")
        flash('Failed to delete event. Please try again later.', 'danger')
    return redirect(url_for('events.admin_events_view'))


@events.route('/admin/events', methods=['GET'])
@login_required
@admin_required
def admin_events_view():
    """Displays a list of all events for admin."""
    all_events = Event.query.all()
    return render_template('admin/admin_events.html', events=all_events)
