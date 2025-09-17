from app import db, socketio
from app.models import Notification, User
from flask_socketio import emit
from datetime import datetime

class NotificationService:
    """Service class for handling notifications"""
    
    @staticmethod
    def create_notification(user_id, notification_type, related_id, content):
        """
        Create a new notification and emit it via SocketIO
        
        Args:
            user_id (int): ID of the user receiving the notification
            notification_type (str): Type of notification (e.g., 'new_message', 'connection_request')
            related_id (int): ID related to the notification (e.g., message_id, connection_id)
            content (str): Notification content/message
            
        Returns:
            Notification: The created notification object
        """
        # Create notification in database
        notification = Notification(
            user_id=user_id,
            type=notification_type,
            related_id=related_id,
            content=content,
            timestamp=datetime.utcnow(),
            read_status=False
        )
        db.session.add(notification)
        db.session.commit()
        
        # Emit notification via SocketIO
        socketio.emit("new_notification", {
            "id": notification.id,
            "type": notification.type,
            "content": notification.content,
            "timestamp": notification.timestamp.isoformat(),
            "read_status": notification.read_status,
            "related_id": notification.related_id
        }, room=str(user_id))
        
        return notification
    
    @staticmethod
    def mark_as_read(notification_id, user_id):
        """
        Mark a notification as read
        
        Args:
            notification_id (int): ID of the notification
            user_id (int): ID of the user who owns the notification
            
        Returns:
            bool: True if successful, False otherwise
        """
        notification = Notification.query.filter_by(
            id=notification_id, 
            user_id=user_id
        ).first()
        
        if not notification:
            return False
            
        notification.read_status = True
        db.session.commit()
        
        # Emit updated notification count
        unread_count = Notification.query.filter_by(
            user_id=user_id, 
            read_status=False
        ).count()
        
        socketio.emit("notification_count_update", {
            "count": unread_count
        }, room=str(user_id))
        
        return True
    
    @staticmethod
    def mark_all_as_read(user_id):
        """
        Mark all notifications for a user as read
        
        Args:
            user_id (int): ID of the user
            
        Returns:
            int: Number of notifications marked as read
        """
        notifications = Notification.query.filter_by(
            user_id=user_id, 
            read_status=False
        ).all()
        
        count = len(notifications)
        
        for notification in notifications:
            notification.read_status = True
        
        db.session.commit()
        
        # Emit updated notification count
        socketio.emit("notification_count_update", {
            "count": 0
        }, room=str(user_id))
        
        return count
    
    @staticmethod
    def get_notifications(user_id, limit=20, offset=0, include_read=True):
        """
        Get notifications for a user
        
        Args:
            user_id (int): ID of the user
            limit (int): Maximum number of notifications to return
            offset (int): Offset for pagination
            include_read (bool): Whether to include read notifications
            
        Returns:
            list: List of notification objects
        """
        query = Notification.query.filter_by(user_id=user_id)
        
        if not include_read:
            query = query.filter_by(read_status=False)
            
        notifications = query.order_by(
            Notification.timestamp.desc()
        ).offset(offset).limit(limit).all()
        
        return notifications
    
    @staticmethod
    def get_unread_count(user_id):
        """
        Get count of unread notifications for a user
        
        Args:
            user_id (int): ID of the user
            
        Returns:
            int: Count of unread notifications
        """
        return Notification.query.filter_by(
            user_id=user_id, 
            read_status=False
        ).count()
    
    @staticmethod
    def delete_notification(notification_id, user_id):
        """
        Delete a notification
        
        Args:
            notification_id (int): ID of the notification
            user_id (int): ID of the user who owns the notification
            
        Returns:
            bool: True if successful, False otherwise
        """
        notification = Notification.query.filter_by(
            id=notification_id, 
            user_id=user_id
        ).first()
        
        if not notification:
            return False
            
        db.session.delete(notification)
        db.session.commit()
        
        return True
    
    @staticmethod
    def delete_all_notifications(user_id):
        """
        Delete all notifications for a user
        
        Args:
            user_id (int): ID of the user
            
        Returns:
            int: Number of notifications deleted
        """
        count = Notification.query.filter_by(user_id=user_id).count()
        Notification.query.filter_by(user_id=user_id).delete()
        db.session.commit()
        
        return count
    
    @staticmethod
    def create_system_notification(user_id, content):
        """
        Create a system notification
        
        Args:
            user_id (int): ID of the user receiving the notification
            content (str): Notification content/message
            
        Returns:
            Notification: The created notification object
        """
        return NotificationService.create_notification(
            user_id=user_id,
            notification_type="system",
            related_id=None,
            content=content
        )
    
    @staticmethod
    def create_message_notification(user_id, sender_id, content=None):
        """
        Create a message notification
        
        Args:
            user_id (int): ID of the user receiving the notification
            sender_id (int): ID of the message sender
            content (str): Optional custom content. If None, a default message is used.
            
        Returns:
            Notification: The created notification object
        """
        sender = User.query.get(sender_id)
        if not sender:
            return None
            
        if not content:
            content = f"New message from {sender.username}."
            
        return NotificationService.create_notification(
            user_id=user_id,
            notification_type="new_message",
            related_id=sender_id,
            content=content
        )
    
    @staticmethod
    def create_connection_request_notification(user_id, requester_id, connection_id):
        """
        Create a connection request notification
        
        Args:
            user_id (int): ID of the user receiving the notification
            requester_id (int): ID of the user sending the connection request
            connection_id (int): ID of the connection
            
        Returns:
            Notification: The created notification object
        """
        requester = User.query.get(requester_id)
        if not requester:
            return None
            
        content = f"{requester.username} sent you a connection request."
            
        return NotificationService.create_notification(
            user_id=user_id,
            notification_type="connection_request",
            related_id=connection_id,
            content=content
        )
    
    @staticmethod
    def create_connection_accepted_notification(user_id, accepter_id, connection_id):
        """
        Create a connection accepted notification
        
        Args:
            user_id (int): ID of the user receiving the notification
            accepter_id (int): ID of the user accepting the connection request
            connection_id (int): ID of the connection
            
        Returns:
            Notification: The created notification object
        """
        accepter = User.query.get(accepter_id)
        if not accepter:
            return None
            
        content = f"{accepter.username} accepted your connection request."
            
        return NotificationService.create_notification(
            user_id=user_id,
            notification_type="connection_accepted",
            related_id=connection_id,
            content=content
        )

