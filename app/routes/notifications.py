from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify
from flask_login import login_required, current_user
from app.models import Notification
from app import db
from app.notification_service import NotificationService

notifications = Blueprint("notifications", __name__)

@notifications.route("/notifications")
@login_required
def view_notifications():
    """View all notifications for the current user"""
    user_notifications = NotificationService.get_notifications(current_user.id)
    read_count = sum(1 for n in user_notifications if n.read_status)
    unread_count = len(user_notifications) - read_count
    
    return render_template(
        "notifications.html",
        notifications=user_notifications,
        read_count=read_count,
        unread_count=unread_count
    )

@notifications.route("/notifications/read/all", methods=["POST"])
@login_required
def mark_all_notifications_read():
    """Mark all notifications as read"""
    count = NotificationService.mark_all_as_read(current_user.id)
    flash(f"All {count} notifications marked as read.", "success")
    return redirect(request.referrer or url_for("notifications.view_notifications"))

@notifications.route("/notifications/clear/all", methods=["POST"])
@login_required
def clear_all_notifications():
    """Delete all notifications"""
    count = NotificationService.delete_all_notifications(current_user.id)
    flash(f"All {count} notifications cleared.", "info")
    return redirect(request.referrer or url_for("notifications.view_notifications"))

@notifications.route("/notifications/read/<int:notification_id>", methods=["POST"])
@login_required
def mark_notification_read(notification_id):
    """Mark a specific notification as read"""
    success = NotificationService.mark_as_read(notification_id, current_user.id)
    
    if success:
        flash("Notification marked as read.", "success")
    else:
        flash("Notification not found.", "danger")
        
    return redirect(request.referrer or url_for("notifications.view_notifications"))

@notifications.route("/notifications/delete/<int:notification_id>", methods=["POST"])
@login_required
def delete_notification(notification_id):
    """Delete a specific notification"""
    success = NotificationService.delete_notification(notification_id, current_user.id)
    
    if success:
        flash("Notification deleted.", "success")
    else:
        flash("Notification not found.", "danger")
        
    return redirect(request.referrer or url_for("notifications.view_notifications"))

# API endpoints for AJAX requests

@notifications.route("/api/notifications/count", methods=["GET"])
@login_required
def get_notification_count():
    """Get the count of unread notifications"""
    count = NotificationService.get_unread_count(current_user.id)
    return jsonify({"count": count})

@notifications.route("/api/notifications", methods=["GET"])
@login_required
def get_notifications():
    """Get notifications for the current user"""
    limit = request.args.get("limit", 10, type=int)
    offset = request.args.get("offset", 0, type=int)
    include_read = request.args.get("include_read", "true").lower() == "true"
    
    notifications = NotificationService.get_notifications(
        current_user.id, 
        limit=limit, 
        offset=offset, 
        include_read=include_read
    )
    
    result = [{
        "id": n.id,
        "type": n.type,
        "content": n.content,
        "timestamp": n.timestamp.isoformat(),
        "read_status": n.read_status,
        "related_id": n.related_id
    } for n in notifications]
    
    return jsonify({
        "notifications": result,
        "total_unread": NotificationService.get_unread_count(current_user.id)
    })

@notifications.route("/api/notifications/read/<int:notification_id>", methods=["POST"])
@login_required
def api_mark_notification_read(notification_id):
    """Mark a notification as read (API endpoint)"""
    success = NotificationService.mark_as_read(notification_id, current_user.id)
    
    if success:
        return jsonify({
            "success": True,
            "message": "Notification marked as read",
            "unread_count": NotificationService.get_unread_count(current_user.id)
        })
    else:
        return jsonify({
            "success": False,
            "message": "Notification not found"
        }), 404

@notifications.route("/api/notifications/read/all", methods=["POST"])
@login_required
def api_mark_all_notifications_read():
    """Mark all notifications as read (API endpoint)"""
    count = NotificationService.mark_all_as_read(current_user.id)
    
    return jsonify({
        "success": True,
        "message": f"All {count} notifications marked as read",
        "unread_count": 0
    })

@notifications.context_processor
def inject_unread_notification_count():
    """Inject unread notification count into all templates"""
    if current_user.is_authenticated:
        count = NotificationService.get_unread_count(current_user.id)
    else:
        count = 0
    return dict(unread_notification_count=count)

