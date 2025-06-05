import random
from sqlalchemy import not_, func 
from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from app.forms import MessageForm # Assuming MessageForm exists, might need update
# Make sure to import Connection and Notification models
from app.models import User, Message, Connection, Notification 
from app import db
from sqlalchemy import or_

messages = Blueprint('messages', __name__)

@messages.context_processor
def inject_unread_notification_count():
    if current_user.is_authenticated:
        count = Notification.query.filter_by(
            user_id=current_user.id,
            read_status=False
        ).count()
    else:
        count = 0
    return dict(unread_notification_count=count)
# --- Connection Management Routes --- 

def get_connection_status(user1_id, user2_id):
    if user1_id == user2_id:
        return "self"
    connection = Connection.query.filter(
        or_(
            (Connection.requester_id == user1_id) & (Connection.receiver_id == user2_id),
            (Connection.requester_id == user2_id) & (Connection.receiver_id == user1_id)
        )
    ).first()
    if connection:
        if connection.status == "accepted":
            return "connected"
        elif connection.status == "pending":
            if connection.requester_id == user1_id:
                return "request_sent"
            else:
                return "request_received"
        elif connection.status == "rejected":
            return "rejected"
        elif connection.status == "blocked":
            return "blocked"
    return "not_connected"


@messages.route('/connections/send/<int:receiver_id>', methods=['POST'])
@login_required
def send_connection_request(receiver_id):
    receiver = User.query.get_or_404(receiver_id)
    if receiver == current_user:
        flash('You cannot connect with yourself.', 'warning')
        return redirect(request.referrer or url_for('main.index')) # Redirect back or to a default page

    # Check if a connection or request already exists
    existing_connection = Connection.query.filter(
        ((Connection.requester_id == current_user.id) & (Connection.receiver_id == receiver_id)) |
        ((Connection.requester_id == receiver_id) & (Connection.receiver_id == current_user.id))
    ).first()

    if existing_connection:
        if existing_connection.status == 'accepted':
            flash(f'You are already connected with {receiver.username}.', 'info')
        elif existing_connection.status == 'pending':
            if existing_connection.requester_id == current_user.id:
                flash('Connection request already sent.', 'info')
            else:
                flash(f'{receiver.username} has already sent you a request. Check your pending requests.', 'info')
        elif existing_connection.status == 'rejected':
             flash('A previous connection request was rejected.', 'warning') # Or allow resending?
        elif existing_connection.status == 'blocked':
             flash('Cannot send request due to blocking.', 'danger')
        return redirect(request.referrer or url_for('main.index'))

    # Create new connection request
    connection = Connection(requester_id=current_user.id, receiver_id=receiver_id, status='pending')
    db.session.add(connection)
    
    # Create notification for the receiver
    notification = Notification(
        user_id=receiver_id, 
        type='connection_request', 
        related_id=connection.id, # Store connection id for context
        content=f'{current_user.username} sent you a connection request.'
    )
    db.session.add(notification)
    
    db.session.commit()
    flash(f'Connection request sent to {receiver.username}.', 'success')
    return redirect(request.referrer or url_for('main.index'))

@messages.route('/connections/manage')
@login_required
def manage_connections():
    incoming_requests = Connection.query.filter_by(receiver_id=current_user.id, status='pending').all()
    outgoing_requests = Connection.query.filter_by(requester_id=current_user.id, status='pending').all()
    accepted_connections_query = Connection.query.filter(
        ((Connection.requester_id == current_user.id) | (Connection.receiver_id == current_user.id)),
        Connection.status == 'accepted'
    ).all()
    
    # Extract the actual connected users from the connection objects
    connected_users = []
    for conn in accepted_connections_query:
        if conn.requester_id == current_user.id:
            connected_users.append(conn.receiver)
        else:
            connected_users.append(conn.requester)
            
    # We'll need a template for this page, e.g., 'connections_manage.html'
    return render_template('connections_manage.html', 
                           incoming=incoming_requests, 
                           outgoing=outgoing_requests, 
                           connections=connected_users)

@messages.route('/connections/action/<int:connection_id>/<string:action>', methods=['POST'])
@login_required
def handle_connection_action(connection_id, action):
    connection = Connection.query.get_or_404(connection_id)
    
    # Security check: Ensure current user is the receiver for accept/reject
    if action in ['accept', 'reject'] and connection.receiver_id != current_user.id:
        flash('Invalid action.', 'danger')
        return redirect(url_for('messages.manage_connections'))
        
    # Security check: Ensure current user is part of the connection for remove/cancel
    if action in ['remove', 'cancel'] and current_user.id not in [connection.requester_id, connection.receiver_id]:
         flash('Invalid action.', 'danger')
         return redirect(url_for('messages.manage_connections'))

    notification_content = None
    notification_recipient_id = None

    if action == 'accept' and connection.status == 'pending':
        connection.status = 'accepted'
        flash('Connection request accepted.', 'success')
        notification_content = f'{current_user.username} accepted your connection request.'
        notification_recipient_id = connection.requester_id
    elif action == 'reject' and connection.status == 'pending':
        connection.status = 'rejected' # Or delete the record?
        # db.session.delete(connection) 
        flash('Connection request rejected.', 'info')
        # Optional: Notify requester about rejection
        # notification_content = f'{current_user.username} rejected your connection request.'
        # notification_recipient_id = connection.requester_id
    elif action == 'cancel' and connection.status == 'pending' and connection.requester_id == current_user.id:
        # Allow requester to cancel pending request
        db.session.delete(connection)
        flash('Connection request cancelled.', 'info')
    elif action == 'remove' and connection.status == 'accepted':
        # Allow either user to remove an accepted connection
        db.session.delete(connection)
        flash('Connection removed.', 'info')
        # Optional: Notify the other user about removal
        # other_user_id = connection.requester_id if connection.receiver_id == current_user.id else connection.receiver_id
        # notification_content = f'{current_user.username} removed you from their connections.'
        # notification_recipient_id = other_user_id
    else:
        flash('Invalid action or connection status.', 'warning')
        return redirect(url_for('messages.manage_connections'))

    # Create notification if applicable
    if notification_content and notification_recipient_id:
        notification = Notification(
            user_id=notification_recipient_id,
            type='connection_accepted' if action == 'accept' else 'connection_update', # Adjust type as needed
            related_id=connection.id,
            content=notification_content
        )
        db.session.add(notification)

    db.session.commit()
    return redirect(url_for('messages.manage_connections'))


# --- Message Routes (Modified) ---

@messages.route("/messages", methods=["GET", "POST"])
@messages.route("/messages/<int:chat_with_id>", methods=["GET", "POST"])
@login_required
def messages_view(chat_with_id=None):
    form = MessageForm() 
    chat_with_user = None
    messages = []
    
    # --- Get Connection Info --- 
    connections = Connection.query.filter(
        or_(Connection.requester_id == current_user.id, Connection.receiver_id == current_user.id)
    ).all()
    
    connected_user_ids = set()
    pending_sent_ids = set()
    pending_received_ids = set()
    involved_user_ids = set() # All users with any connection status
    
    for conn in connections:
        other_user_id = conn.requester_id if conn.receiver_id == current_user.id else conn.receiver_id
        involved_user_ids.add(other_user_id)
        if conn.status == "accepted":
            connected_user_ids.add(other_user_id)
        elif conn.status == "pending":
            if conn.requester_id == current_user.id:
                pending_sent_ids.add(other_user_id)
            else:
                pending_received_ids.add(other_user_id)
        # Ignore rejected/blocked for now in these sets

    # --- Handle POST (Sending Message) --- 
    if chat_with_id and form.validate_on_submit():
        recipient_id = chat_with_id # Recipient is determined by the URL
        # Check if recipient is a valid connection
        if recipient_id not in connected_user_ids:
             flash("You can only send messages to accepted connections.", "danger")
             return redirect(url_for("messages.messages_view", chat_with_id=chat_with_id))
             
        message = Message(sender_id=current_user.id, recipient_id=recipient_id, content=form.content.data)
        db.session.add(message)
        
        # Create notification for the recipient
        notification = Notification(
            user_id=recipient_id,
            type="new_message",
            related_id=current_user.id, # Store sender ID
            content=f"New message from {current_user.username}."
        )
        db.session.add(notification)
            
        db.session.commit()
        # No flash message needed, just reload the chat
        return redirect(url_for("messages.messages_view", chat_with_id=chat_with_id))

    # --- Handle GET (Displaying View) --- 
    
    # Fetch conversations (user, last message, time, unread count)
    # This requires a more complex query later. For now, just list connected users.
    conversations_users = User.query.filter(User.id.in_(connected_user_ids)).all()
    # Dummy conversation data for now
    conversations = [
        {
            "user": user,
            "last_message_content": "Click to chat...",
            "last_message_time": None, # Fetch actual last message time later
            "unread_count": 0 # Fetch actual unread count later
        } for user in conversations_users
    ]
    # Sort conversations by some logic later (e.g., last message time)

    # Fetch messages if a chat is selected
    if chat_with_id:
        if chat_with_id not in connected_user_ids:
            flash("You are not connected with this user.", "warning")
            return redirect(url_for("messages.messages_view"))
        chat_with_user = User.query.get_or_404(chat_with_id)
        messages = Message.query.filter(
            or_(
                (Message.sender_id == current_user.id) & (Message.recipient_id == chat_with_id),
                (Message.sender_id == chat_with_id) & (Message.recipient_id == current_user.id)
            )
        ).order_by(Message.date_sent.asc()).all()
        # Mark messages as read? (Add later)

    # --- Fetch Discover Users --- 
    # Users not self, not involved in any connection (accepted, pending, etc.)
    eligible_user_ids_query = User.query.with_entities(User.id).filter(User.id != current_user.id)
    
    # Subquery for users involved in any connection with current_user
    involved_subquery = db.session.query(Connection.requester_id).filter(Connection.receiver_id == current_user.id).union(
        db.session.query(Connection.receiver_id).filter(Connection.requester_id == current_user.id)
    ).subquery()
    
    eligible_users = User.query.filter(
        User.id != current_user.id,
        ~User.id.in_(involved_subquery)
    ).all()
    
    # Get Recommended Users (random subset of eligible)
    num_recommendations = min(5, len(eligible_users))
    recommended_users = random.sample(eligible_users, num_recommendations)
    
    # Get Discoverable Users (all eligible, could add pagination later)
    # For now, discoverable_users is the same as eligible_users
    discoverable_users = eligible_users 
    # Add connection status to discoverable users for the template
    discoverable_users_with_status = [
        {"user": user, "status": get_connection_status(current_user.id, user.id)} 
        for user in discoverable_users
    ]

    # Fetch unread notification count
    unread_notification_count = Notification.query.filter_by(user_id=current_user.id, read_status=False).count()

    return render_template("messages.html", 
                           form=form, 
                           conversations=conversations, 
                           chat_with_user=chat_with_user,
                           messages=messages,
                           unread_notification_count=unread_notification_count,
                           recommended_users=recommended_users,
                           discoverable_users=discoverable_users_with_status # Pass users with status
                           )

# Placeholder for notification routes (e.g., mark as read, view all)
@messages.route('/notifications')
@login_required
def view_notifications():
    user_notifications = Notification.query.\
        filter_by(user_id=current_user.id).\
        order_by(Notification.timestamp.desc()).all()
    # Optionally don’t auto‐mark as read here if you want explicit control
    read_count = sum(1 for n in user_notifications if n.read_status)
    unread_count = len(user_notifications) - read_count
    return render_template(
        'notifications.html',
        notifications=user_notifications,
        read_count=read_count,
        unread_count=unread_count
    )

@messages.route('/notifications/read/all', methods=['POST'])
@login_required
def mark_all_notifications_read():
    notifs = Notification.query.filter_by(
        user_id=current_user.id, read_status=False
    ).all()
    for n in notifs:
        n.read_status = True
    db.session.commit()
    flash('All notifications marked as read.', 'success')
    return redirect(request.referrer or url_for('messages.view_notifications'))

@messages.route('/notifications/clear/all', methods=['POST'])
@login_required
def clear_all_notifications():
    Notification.query.filter_by(user_id=current_user.id).delete()
    db.session.commit()
    flash('All notifications cleared.', 'info')
    return redirect(request.referrer or url_for('messages.view_notifications'))

@messages.route('/notifications/read/<int:notification_id>', methods=['POST'])
@login_required
def mark_notification_read(notification_id):
    notification = Notification.query.filter_by(id=notification_id, user_id=current_user.id).first_or_404()
    notification.read_status = True
    db.session.commit()
    flash('Notification marked as read.', 'success')
    return redirect(request.referrer or url_for('messages.view_notifications'))


