import random
from sqlalchemy import not_, func 
from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from app.forms import MessageForm 
from app.models import User, Message, Connection, Notification 
from app import db, socketio
from sqlalchemy import or_
from flask_socketio import emit

messages = Blueprint("messages", __name__)

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


@messages.route("/connections/send/<int:receiver_id>", methods=["POST"])
@login_required
def send_connection_request(receiver_id):
    receiver = User.query.get_or_404(receiver_id)
    if receiver == current_user:
        flash("You cannot connect with yourself.", "warning")
        return redirect(request.referrer or url_for("main.index")) 

    existing_connection = Connection.query.filter(
        ((Connection.requester_id == current_user.id) & (Connection.receiver_id == receiver_id)) |
        ((Connection.requester_id == receiver_id) & (Connection.receiver_id == current_user.id))
    ).first()

    if existing_connection:
        if existing_connection.status == "accepted":
            flash(f"You are already connected with {receiver.username}.", "info")
        elif existing_connection.status == "pending":
            if existing_connection.requester_id == current_user.id:
                flash("Connection request already sent.", "info")
            else:
                flash(f"{receiver.username} has already sent you a request. Check your pending requests.", "info")
        elif existing_connection.status == "rejected":
             flash("A previous connection request was rejected.", "warning") 
        elif existing_connection.status == "blocked":
             flash("Cannot send request due to blocking.", "danger")
        return redirect(request.referrer or url_for("main.index"))

    connection = Connection(requester_id=current_user.id, receiver_id=receiver_id, status="pending")
    db.session.add(connection)
    
    notification = Notification(
        user_id=receiver_id, 
        type="connection_request", 
        related_id=connection.id, 
        content=f"{current_user.username} sent you a connection request."
    )
    db.session.add(notification)
    
    db.session.commit()

    # Emit notification via SocketIO
    socketio.emit("new_notification", {
        "type": notification.type,
        "content": notification.content,
        "timestamp": notification.timestamp.isoformat(),
        "read_status": notification.read_status
    }, room=str(receiver_id))

    flash(f"Connection request sent to {receiver.username}.", "success")
    return redirect(request.referrer or url_for("main.index"))

@messages.route("/connections/manage")
@login_required
def manage_connections():
    incoming_requests = Connection.query.filter_by(receiver_id=current_user.id, status="pending").all()
    outgoing_requests = Connection.query.filter_by(requester_id=current_user.id, status="pending").all()
    accepted_connections_query = Connection.query.filter(
        ((Connection.requester_id == current_user.id) | (Connection.receiver_id == current_user.id)),
        Connection.status == "accepted"
    ).all()
    
    connected_users = []
    for conn in accepted_connections_query:
        if conn.requester_id == current_user.id:
            connected_users.append(conn.receiver)
        else:
            connected_users.append(conn.requester)
            
    return render_template("connections_manage.html", 
                           incoming=incoming_requests, 
                           outgoing=outgoing_requests, 
                           connections=connected_users)

@messages.route("/connections/action/<int:connection_id>/<string:action>", methods=["POST"])
@login_required
def handle_connection_action(connection_id, action):
    connection = Connection.query.get_or_404(connection_id)
    
    if action in ["accept", "reject"] and connection.receiver_id != current_user.id:
        flash("Invalid action.", "danger")
        return redirect(url_for("messages.manage_connections"))
        
    if action in ["remove", "cancel"] and current_user.id not in [connection.requester_id, connection.receiver_id]:
         flash("Invalid action.", "danger")
         return redirect(url_for("messages.manage_connections"))

    notification_content = None
    notification_recipient_id = None

    if action == "accept" and connection.status == "pending":
        connection.status = "accepted"
        flash("Connection request accepted.", "success")
        notification_content = f"{current_user.username} accepted your connection request."
        notification_recipient_id = connection.requester_id
    elif action == "reject" and connection.status == "pending":
        connection.status = "rejected" 
        flash("Connection request rejected.", "info")
    elif action == "cancel" and connection.status == "pending" and connection.requester_id == current_user.id:
        db.session.delete(connection)
        flash("Connection request cancelled.", "info")
    elif action == "remove" and connection.status == "accepted":
        db.session.delete(connection)
        flash("Connection removed.", "info")
    else:
        flash("Invalid action or connection status.", "warning")
        return redirect(url_for("messages.manage_connections"))

    if notification_content and notification_recipient_id:
        notification = Notification(
            user_id=notification_recipient_id,
            type="connection_accepted" if action == "accept" else "connection_update", 
            related_id=connection.id,
            content=notification_content
        )
        db.session.add(notification)
        socketio.emit("new_notification", {
            "type": notification.type,
            "content": notification.content,
            "timestamp": notification.timestamp.isoformat(),
            "read_status": notification.read_status
        }, room=str(notification_recipient_id))

    db.session.commit()
    return redirect(url_for("messages.manage_connections"))


@messages.route("/messages", methods=["GET", "POST"])
@messages.route("/messages/<int:chat_with_id>", methods=["GET", "POST"])
@login_required
def messages_view(chat_with_id=None):
    form = MessageForm() 
    chat_with_user = None
    messages = []
    
    connections = Connection.query.filter(
        or_(Connection.requester_id == current_user.id, Connection.receiver_id == current_user.id)
    ).all()
    
    connected_user_ids = set()
    pending_sent_ids = set()
    pending_received_ids = set()
    involved_user_ids = set() 
    
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

    # Handle POST (Sending Message) - Now handled by SocketIO, so remove direct DB operations
    if chat_with_id and form.validate_on_submit():
        # This part will be handled by SocketIO, so we just redirect to clear the form
        return redirect(url_for("messages.messages_view", chat_with_id=chat_with_id))

    conversations_users = User.query.filter(User.id.in_(connected_user_ids)).all()
    conversations = [
        {
            "user": user,
            "last_message_content": "Click to chat...",
            "last_message_time": None, 
            "unread_count": 0 
        } for user in conversations_users
    ]

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

    eligible_user_ids_query = User.query.with_entities(User.id).filter(User.id != current_user.id)
    
    involved_subquery = db.session.query(Connection.requester_id).filter(Connection.receiver_id == current_user.id).union(
        db.session.query(Connection.receiver_id).filter(Connection.requester_id == current_user.id)
    ).subquery()
    
    eligible_users = User.query.filter(
        User.id != current_user.id,
        ~User.id.in_(involved_subquery)
    ).all()
    
    num_recommendations = min(5, len(eligible_users))
    recommended_users = random.sample(eligible_users, num_recommendations)
    
    discoverable_users = eligible_users 
    discoverable_users_with_status = [
        {"user": user, "status": get_connection_status(current_user.id, user.id)} 
        for user in discoverable_users
    ]

    unread_notification_count = Notification.query.filter_by(user_id=current_user.id, read_status=False).count()

    return render_template("messages.html", 
                           form=form, 
                           conversations=conversations, 
                           chat_with_user=chat_with_user,
                           messages=messages,
                           unread_notification_count=unread_notification_count,
                           recommended_users=recommended_users,
                           discoverable_users=discoverable_users_with_status 
                           )

@messages.route("/notifications")
@login_required
def view_notifications():
    user_notifications = Notification.query.\
        filter_by(user_id=current_user.id).\
        order_by(Notification.timestamp.desc()).all()
    read_count = sum(1 for n in user_notifications if n.read_status)
    unread_count = len(user_notifications) - read_count
    return render_template(
        "notifications.html",
        notifications=user_notifications,
        read_count=read_count,
        unread_count=unread_count
    )

@messages.route("/notifications/read/all", methods=["POST"])
@login_required
def mark_all_notifications_read():
    notifs = Notification.query.filter_by(
        user_id=current_user.id, read_status=False
    ).all()
    for n in notifs:
        n.read_status = True
    db.session.commit()
    flash("All notifications marked as read.", "success")
    return redirect(request.referrer or url_for("messages.view_notifications"))

@messages.route("/notifications/clear/all", methods=["POST"])
@login_required
def clear_all_notifications():
    Notification.query.filter_by(user_id=current_user.id).delete()
    db.session.commit()
    flash("All notifications cleared.", "info")
    return redirect(request.referrer or url_for("messages.view_notifications"))

@messages.route("/notifications/read/<int:notification_id>", methods=["POST"])
@login_required
def mark_notification_read(notification_id):
    notification = Notification.query.filter_by(id=notification_id, user_id=current_user.id).first_or_404()
    notification.read_status = True
    db.session.commit()
    flash("Notification marked as read.", "success")
    return redirect(request.referrer or url_for("messages.view_notifications"))


