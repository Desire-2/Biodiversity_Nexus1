import os
import logging
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from functools import wraps
from flask import Blueprint, render_template, redirect, url_for, flash, request, current_app
from flask_login import login_required, current_user
from app import db
from app.models import Event, EventAttendance

event_features = Blueprint('event_features', __name__)

# Reusable decorator for admin-only routes.
def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if current_user.role != 'admin':
            flash("You do not have permission to access this page", "danger")
            return redirect(url_for('events.events_view'))
        return f(*args, **kwargs)
    return decorated_function

def build_reminder_email_body(event, user):
    """Constructs an HTML body for the event reminder email."""
    return f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <title>Event Reminder</title>
        <style>
            body {{
                font-family: Arial, sans-serif;
                color: #333;
            }}
            .container {{
                max-width: 600px;
                margin: 0 auto;
                padding: 20px;
                background-color: #f9f9f9;
                border: 1px solid #ddd;
                border-radius: 5px;
            }}
            .header {{
                font-size: 24px;
                margin-bottom: 20px;
                color: #4CAF50;
            }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">Event Reminder: {event.name}</div>
            <p>Dear {user.username},</p>
            <p>This is a friendly reminder for the upcoming event.</p>
            <p><strong>Date:</strong> {event.date}</p>
            <p><strong>Description:</strong> {event.description}</p>
            <p>We look forward to your participation!</p>
            <p>Best regards,<br>The Events Team</p>
        </div>
    </body>
    </html>
    """

def send_reminder_email(event, user):
    """Sends a reminder email for an event to a given user."""
    msg = MIMEMultipart()
    msg['From'] = os.getenv("MAIL_USERNAME")
    msg['To'] = user.email
    msg['Subject'] = 'Event Reminder'
    
    body = build_reminder_email_body(event, user)
    msg.attach(MIMEText(body, 'html', 'utf-8'))
    
    server = smtplib.SMTP(os.getenv("MAIL_SERVER"), int(os.getenv("MAIL_PORT")))
    server.starttls()
    server.login(os.getenv("MAIL_USERNAME"), os.getenv("MAIL_PASSWORD"))
    server.sendmail(msg['From'], msg['To'], msg.as_bytes())
    server.quit()

@event_features.route('/event/<int:event_id>/checkin', methods=['POST'])
@login_required
def event_checkin(event_id):
    """
    Allows a registered user to check in to an event.
    Assumes that the EventAttendance model has a boolean field `checked_in` (default False).
    """
    attendance = EventAttendance.query.filter_by(event_id=event_id, user_id=current_user.id).first()
    if not attendance:
        flash("You are not registered for this event.", "warning")
        return redirect(url_for("events.events_detail", event_id=event_id))
    
    if getattr(attendance, 'checked_in', False):
        flash("You have already checked in.", "info")
        return redirect(url_for("events.events_detail", event_id=event_id))
    
    attendance.checked_in = True
    try:
        db.session.commit()
        flash("Checked in successfully!", "success")
    except Exception as e:
        db.session.rollback()
        logging.error(f"Error during event check-in: {e}")
        flash("Failed to check in. Please try again later.", "danger")
    
    return redirect(url_for("events.events_detail", event_id=event_id))

@event_features.route('/admin/event/<int:event_id>/send_reminders', methods=['POST'])
@login_required
@admin_required
def send_event_reminders(event_id):
    """
    Admin-only route to send reminder emails to all registered attendees for the given event.
    """
    event = Event.query.get_or_404(event_id)
    attendees = EventAttendance.query.filter_by(event_id=event.id).all()
    sent_count = 0

    for attendance in attendees:
        # Assumes that the EventAttendance model defines a relationship to the User model as 'user'
        user = attendance.user  
        try:
            send_reminder_email(event, user)
            sent_count += 1
        except Exception as e:
            logging.error(f"Failed to send reminder email to {user.email}: {e}")

    flash(f"Sent reminder emails to {sent_count} attendee(s).", "success")
    return redirect(url_for("events.events_detail", event_id=event.id))
