from flask import Blueprint, render_template, redirect, url_for, flash
from flask_login import login_required, current_user
from app.forms import MessageForm
from app.models import User, Message
from app import db

messages = Blueprint('messages', __name__)

@messages.route('/messages', methods=['GET', 'POST'])
@login_required
def messages_view():
    form = MessageForm()
    form.recipient.choices = [(user.id, user.username) for user in User.query.all()]
    if form.validate_on_submit():
        message = Message(sender_id=current_user.id, recipient_id=form.recipient.data, content=form.content.data)
        db.session.add(message)
        db.session.commit()
        flash('Message sent successfully', 'success')
        return redirect(url_for('messages.messages_view'))
    received_messages = Message.query.filter_by(recipient_id=current_user.id).all()
    sent_messages = Message.query.filter_by(sender_id=current_user.id).all()
    return render_template('messages.html', form=form, received_messages=received_messages, sent_messages=sent_messages)
