from flask_socketio import SocketIO, emit, join_room, leave_room
from app import socketio, db
from app.models import Message, Notification, User, Connection
from flask_login import current_user
from datetime import datetime
from sqlalchemy import or_

@socketio.on("connect")
def handle_connect():
    if current_user.is_authenticated:
        print(f"Client connected: {current_user.username} (ID: {current_user.id})")
        # Join a personal room for notifications
        join_room(str(current_user.id))
    else:
        print("Anonymous client connected.")

@socketio.on("disconnect")
def handle_disconnect():
    if current_user.is_authenticated:
        print(f"Client disconnected: {current_user.username} (ID: {current_user.id})")
    else:
        print("Anonymous client disconnected.")

@socketio.on("join")
def handle_join(data):
    """Join a room for personal notifications"""
    room = data.get("room")
    if room and current_user.is_authenticated:
        join_room(room)
        print(f"{current_user.username} joined notification room {room}")

@socketio.on("join_chat_room")
def handle_join_chat_room(data):
    room_id = data.get("room_id")
    if room_id and current_user.is_authenticated:
        join_room(room_id)
        print(f"{current_user.username} joined room {room_id}")
        emit("status_message", {"msg": f"{current_user.username} has joined the chat."}, room=room_id)

@socketio.on("leave_chat_room")
def handle_leave_chat_room(data):
    room_id = data.get("room_id")
    if room_id and current_user.is_authenticated:
        leave_room(room_id)
        print(f"{current_user.username} left room {room_id}")
        emit("status_message", {"msg": f"{current_user.username} has left the chat."}, room=room_id)

@socketio.on("send_message")
def handle_send_message(data):
    if not current_user.is_authenticated:
        return

    recipient_id = data.get("recipient_id")
    content = data.get("content")
    room_id = data.get("room_id") # This should be a consistent room ID for a 1-on-1 chat

    if not recipient_id or not content or not room_id:
        return

    # Save message to DB
    new_message = Message(
        sender_id=current_user.id,
        recipient_id=recipient_id,
        content=content,
        date_sent=datetime.utcnow()
    )
    db.session.add(new_message)

    # Create notification for the recipient
    notification = Notification(
        user_id=recipient_id,
        type="new_message",
        related_id=current_user.id, # Store sender ID
        content=f"New message from {current_user.username}."
    )
    db.session.add(notification)
    db.session.commit()

    # Emit message to both sender and recipient in their shared room
    emit("new_message", {
        "sender_id": current_user.id,
        "sender_username": current_user.username,
        "content": content,
        "date_sent": new_message.date_sent.isoformat() # Send as ISO format string
    }, room=room_id)

    # Emit notification to recipient's personal notification room
    emit("new_notification", {
        "id": notification.id,
        "type": notification.type,
        "content": notification.content,
        "timestamp": notification.timestamp.isoformat(),
        "read_status": notification.read_status,
        "related_id": notification.related_id
    }, room=str(recipient_id))

@socketio.on("typing")
def handle_typing(data):
    recipient_id = data.get("recipient_id")
    room_id = data.get("room_id")
    is_typing = data.get("is_typing")

    if not current_user.is_authenticated or not recipient_id or not room_id:
        return

    # Emit typing status to the other user in the chat room
    emit("typing_status", {
        "sender_id": current_user.id,
        "sender_username": current_user.username,
        "is_typing": is_typing
    }, room=room_id, include_self=False)

@socketio.on("mark_notification_read")
def handle_mark_notification_read(data):
    """Mark a notification as read"""
    if not current_user.is_authenticated:
        return

    notification_id = data.get("notification_id")
    if not notification_id:
        return

    notification = Notification.query.filter_by(
        id=notification_id, 
        user_id=current_user.id
    ).first()

    if notification:
        notification.read_status = True
        db.session.commit()
        
        # Emit updated notification count
        unread_count = Notification.query.filter_by(
            user_id=current_user.id, 
            read_status=False
        ).count()
        
        emit("notification_count_update", {
            "count": unread_count
        }, room=str(current_user.id))

@socketio.on("mark_all_notifications_read")
def handle_mark_all_notifications_read():
    """Mark all notifications as read"""
    if not current_user.is_authenticated:
        return

    notifications = Notification.query.filter_by(
        user_id=current_user.id, 
        read_status=False
    ).all()

    for notification in notifications:
        notification.read_status = True
    
    db.session.commit()
    
    # Emit updated notification count (which will be 0)
    emit("notification_count_update", {
        "count": 0
    }, room=str(current_user.id))

@socketio.on("get_notifications")
def handle_get_notifications():
    """Get all notifications for the current user"""
    if not current_user.is_authenticated:
        return

    notifications = Notification.query.filter_by(
        user_id=current_user.id
    ).order_by(Notification.timestamp.desc()).all()

    notification_list = [{
        "id": n.id,
        "type": n.type,
        "content": n.content,
        "timestamp": n.timestamp.isoformat(),
        "read_status": n.read_status,
        "related_id": n.related_id
    } for n in notifications]

    emit("notifications_list", {
        "notifications": notification_list
    }, room=str(current_user.id))

@socketio.on("send_connection_request")
def handle_send_connection_request(data):
    """Send a connection request to another user"""
    if not current_user.is_authenticated:
        return

    receiver_id = data.get("receiver_id")
    if not receiver_id:
        return

    # Check if user exists
    receiver = User.query.get(receiver_id)
    if not receiver or receiver.id == current_user.id:
        return

    # Check if a connection already exists
    existing_connection = Connection.query.filter(
        or_(
            (Connection.requester_id == current_user.id) & (Connection.receiver_id == receiver_id),
            (Connection.requester_id == receiver_id) & (Connection.receiver_id == current_user.id)
        )
    ).first()

    if existing_connection:
        # Connection already exists, return status
        return {
            "status": "error",
            "message": f"A connection with {receiver.username} already exists with status: {existing_connection.status}"
        }

    # Create new connection
    connection = Connection(
        requester_id=current_user.id,
        receiver_id=receiver_id,
        status="pending"
    )
    db.session.add(connection)

    # Create notification
    notification = Notification(
        user_id=receiver_id,
        type="connection_request",
        related_id=connection.id,
        content=f"{current_user.username} sent you a connection request."
    )
    db.session.add(notification)
    db.session.commit()

    # Emit notification to receiver
    emit("new_notification", {
        "id": notification.id,
        "type": notification.type,
        "content": notification.content,
        "timestamp": notification.timestamp.isoformat(),
        "read_status": notification.read_status,
        "related_id": notification.related_id
    }, room=str(receiver_id))

    return {
        "status": "success",
        "message": f"Connection request sent to {receiver.username}"
    }

@socketio.on("handle_connection_action")
def handle_connection_action(data):
    """Handle connection request actions (accept, reject, cancel, remove)"""
    if not current_user.is_authenticated:
        return

    connection_id = data.get("connection_id")
    action = data.get("action")

    if not connection_id or not action:
        return

    connection = Connection.query.get(connection_id)
    if not connection:
        return {
            "status": "error",
            "message": "Connection not found"
        }

    # Security checks
    if action in ["accept", "reject"] and connection.receiver_id != current_user.id:
        return {
            "status": "error",
            "message": "You are not authorized to perform this action"
        }

    if action in ["remove", "cancel"] and current_user.id not in [connection.requester_id, connection.receiver_id]:
        return {
            "status": "error",
            "message": "You are not authorized to perform this action"
        }

    notification_content = None
    notification_recipient_id = None

    if action == "accept" and connection.status == "pending":
        connection.status = "accepted"
        notification_content = f"{current_user.username} accepted your connection request."
        notification_recipient_id = connection.requester_id
        message = "Connection request accepted"
    
    elif action == "reject" and connection.status == "pending":
        connection.status = "rejected"
        message = "Connection request rejected"
    
    elif action == "cancel" and connection.status == "pending" and connection.requester_id == current_user.id:
        db.session.delete(connection)
        message = "Connection request cancelled"
    
    elif action == "remove" and connection.status == "accepted":
        db.session.delete(connection)
        message = "Connection removed"
    
    else:
        return {
            "status": "error",
            "message": "Invalid action or connection status"
        }

    # Create notification if applicable
    if notification_content and notification_recipient_id:
        notification = Notification(
            user_id=notification_recipient_id,
            type="connection_accepted" if action == "accept" else "connection_update",
            related_id=connection.id,
            content=notification_content
        )
        db.session.add(notification)
        
        # Emit notification to recipient
        emit("new_notification", {
            "id": notification.id,
            "type": notification.type,
            "content": notification.content,
            "timestamp": notification.timestamp.isoformat(),
            "read_status": notification.read_status,
            "related_id": notification.related_id
        }, room=str(notification_recipient_id))

    db.session.commit()

    return {
        "status": "success",
        "message": message
    }

@socketio.on("get_online_status")
def handle_get_online_status(data):
    """Get online status of users"""
    if not current_user.is_authenticated:
        return

    user_ids = data.get("user_ids", [])
    if not user_ids:
        return

    # In a real application, you would check if these users are actually online
    # For now, we'll just return a mock status
    online_status = {
        user_id: True for user_id in user_ids
    }

    emit("online_status_update", {
        "status": online_status
    }, room=str(current_user.id))

