"""
Notification model
"""

from datetime import datetime
from typing import Optional, TYPE_CHECKING

from ..enums import NotificationType

if TYPE_CHECKING:
    from ..client import Client
    from .user import User


class Notification:
    """
    Represents a notification
    
    Attributes:
        uuid: Notification's unique identifier
        user: User who triggered the notification
        type: Notification type (follow, comment, reply, etc)
        action: Action UUID (post UUID, comment UUID, etc)
        data: Additional data (varies by type)
        is_read: Whether the notification has been read
        updated_at: When the notification was last updated
    """
    
    def __init__(self, data: dict, client: "Client"):
        self._client = client
        self._update(data)
        
    def _update(self, data: dict):
        """Update notification data from API response"""
        from .user import User
        
        self.uuid: str = data.get("uuid")
        self.type: str = data.get("type")
        self.action: str = data.get("action")
        self.data: any = data.get("data")
        self.is_read: bool = data.get("isRead", False)
        
        # Parse user
        user_data = data.get("user", {})
        self.user: User = User(user_data, self._client)
        
        # Parse timestamp
        updated_at = data.get("updatedAt")
        self.updated_at: Optional[datetime] = None
        if updated_at:
            try:
                self.updated_at = datetime.fromisoformat(updated_at.replace("Z", "+00:00"))
            except:
                pass
                
    def __repr__(self):
        return f"<Notification uuid={self.uuid} type={self.type} user={self.user.nick}>"
        
    def __str__(self):
        type_messages = {
            NotificationType.FOLLOW.value: f"{self.user.name} followed you",
            NotificationType.COMMENT.value: f"{self.user.name} commented on your post",
            NotificationType.REPLY.value: f"{self.user.name} replied to your comment",
            NotificationType.MENTION.value: f"{self.user.name} mentioned you",
            NotificationType.POST_REACTION.value: f"{self.user.name} reacted to your post",
            NotificationType.POST_COMMENT_REACTION.value: f"{self.user.name} reacted to your comment",
        }
        return type_messages.get(self.type, f"{self.user.name} - {self.type}")
        
    async def mark_as_read(self) -> None:
        """Mark this notification as read"""
        try:
            # Mark as read via API (correct endpoint from app logs)
            await self._client.http.put(f"/notification/{self.uuid}")
            self.is_read = True
        except Exception:
            # If API call fails, just mark locally
            # This prevents the notification from being processed again in the same session
            self.is_read = True
        
    async def get_post(self):
        """Get the post associated with this notification (if applicable)"""
        if self.type in [NotificationType.COMMENT.value, NotificationType.POST_REACTION.value, 
                         NotificationType.REPLY.value, NotificationType.MENTION.value]:
            return await self._client.get_post(self.action)
        return None


class NotificationResume:
    """
    Represents a summary of unread notifications
    
    Attributes:
        questions: Number of unread questions
        notifications: Number of unread notifications
        chats: Number of unread chat messages
    """
    
    def __init__(self, data: dict):
        self.questions: int = data.get("questions", 0)
        self.notifications: int = data.get("notifications", 0)
        self.chats: int = data.get("chats", 0)
        
    def __repr__(self):
        return f"<NotificationResume notifications={self.notifications} chats={self.chats} questions={self.questions}>"
        
    def __str__(self):
        return f"Notifications: {self.notifications}, Chats: {self.chats}, Questions: {self.questions}"
        
    @property
    def total(self) -> int:
        """Total number of unread items"""
        return self.questions + self.notifications + self.chats
        
    @property
    def has_unread(self) -> bool:
        """Whether there are any unread items"""
        return self.total > 0
