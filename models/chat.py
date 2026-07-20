"""
Chat and Message models
"""

from datetime import datetime
from typing import Optional, List, AsyncIterator, TYPE_CHECKING

from ..enums import MessageType

if TYPE_CHECKING:
    from ..client import Client
    from .user import User


class Message:
    """
    Represents a chat message
    
    Attributes:
        id: Message ID
        user: User who sent the message
        type: Message type (text, photo, video)
        text: Message text content
        media: Media UUID if message contains media
        date: When the message was sent
        is_read: Whether the message has been read
    """
    
    def __init__(self, data: dict, chat_uuid: str, client: "Client"):
        self._client = client
        self._chat_uuid = chat_uuid
        self._update(data)
        
    def _update(self, data: dict):
        """Update message data from API response"""
        from .user import User
        
        self.id: str = data.get("id")
        self.type: str = data.get("type", MessageType.TEXT.value)
        self.text: Optional[str] = data.get("text")
        self.media: Optional[str] = data.get("media")
        self.is_read: Optional[bool] = data.get("isRead")
        
        # Parse user
        user_data = data.get("user", {})
        if user_data:
            self.user: User = User(user_data, self._client)
        else:
            self.user = None
        
        # Parse timestamp
        date = data.get("date")
        self.date: Optional[datetime] = None
        if date:
            try:
                self.date = datetime.fromisoformat(date.replace("Z", "+00:00"))
            except:
                pass
                
    def __repr__(self):
        text_preview = self.text[:30] + "..." if self.text and len(self.text) > 30 else self.text
        return f"<Message id={self.id} type={self.type} text={text_preview}>"
        
    def __str__(self):
        if self.user:
            return f"{self.user.name}: {self.text or '[media]'}"
        return self.text or '[media]'
        
    @property
    def media_url(self) -> Optional[str]:
        """Get the full URL for message media"""
        if self.media and self.user:
            return f"https://honest.nyc3.digitaloceanspaces.com/{self.user.uuid}/c/{self.media}.jpg"
        return None
        
    async def reply(self, text: str) -> "Message":
        """
        Reply to this message
        
        Args:
            text: Reply text
            
        Returns:
            Message object
        """
        chat = Chat({"uuid": self._chat_uuid}, self._client)
        return await chat.send(text)


class Chat:
    """
    Represents a chat conversation
    
    Attributes:
        uuid: Chat's unique identifier
        user: Other user in the chat
        last_message: Last message in the chat
        last_view: When the chat was last viewed
        unread_count: Number of unread messages
    """
    
    def __init__(self, data: dict, client: "Client"):
        self._client = client
        self._update(data)
        
    def _update(self, data: dict):
        """Update chat data from API response"""
        from .user import User
        
        self.uuid: str = data.get("uuid") or data.get("token")
        self.unread_count: int = data.get("unreadCount", 0)
        
        # Parse user
        user_data = data.get("user", {})
        if user_data:
            self.user: Optional[User] = User(user_data, self._client)
        else:
            self.user = None
        
        # Parse last message
        last_message_data = data.get("lastMessage")
        if last_message_data:
            self.last_message: Optional[Message] = Message(last_message_data, self.uuid, self._client)
        else:
            self.last_message = None
            
        self.last_message_text = data.get("message")
        self.updated_at = data.get("updatedAt")
            
        # Parse last view
        last_view = data.get("lastView")
        self.last_view: Optional[datetime] = None
        if last_view:
            try:
                self.last_view = datetime.fromisoformat(last_view.replace("Z", "+00:00"))
            except:
                pass
                
    def __repr__(self):
        user_str = f"user={self.user.nick}" if self.user else "user=None"
        return f"<Chat uuid={self.uuid} {user_str}>"
        
    def __str__(self):
        if self.user:
            return f"Chat with {self.user.name}"
        return f"Chat {self.uuid}"
        
    async def send(self, text: str) -> Message:
        """
        Send a text message in this chat
        
        Args:
            text: Message text
            
        Returns:
            Message object
        """
        response = await self._client.http.post(
            f"/chat/{self.uuid}/historic",
            json={"type": MessageType.TEXT.value, "text": text}
        )
        
        # Create message object from response
        message_data = {
            "id": response.get("id"),
            "date": response.get("date"),
            "type": MessageType.TEXT.value,
            "text": text,
            "user": self._client.user.__dict__ if hasattr(self._client, 'user') else {}
        }
        return Message(message_data, self.uuid, self._client)
        
    async def send_photo(self, file_path: str) -> Message:
        """
        Send a photo in this chat
        
        Args:
            file_path: Path to the image file
            
        Returns:
            Message object
        """
        # Upload media first
        media_uuid = await self._client.upload_photo(file_path, media_type="chat")
        
        # Wait for processing
        await self._client.wait_for_media(media_uuid)
        
        # Send message with media
        response = await self._client.http.post(
            f"/chat/{self.uuid}/historic",
            json={"type": MessageType.PHOTO.value, "media": media_uuid}
        )
        
        message_data = {
            "id": response.get("id"),
            "date": response.get("date"),
            "type": MessageType.PHOTO.value,
            "media": media_uuid,
            "user": self._client.user.__dict__ if hasattr(self._client, 'user') else {}
        }
        return Message(message_data, self.uuid, self._client)
        
    async def send_story(self, story_uuid: str, text: Optional[str] = None) -> Message:
        """
        Send a story in this chat
        
        Args:
            story_uuid: UUID of the story to send
            text: Optional text message
            
        Returns:
            Message object
        """
        data = {
            "type": "story",
            "media": story_uuid,
        }
        
        if text:
            data["text"] = text
            
        response = await self._client.http.post(
            f"/chat/{self.uuid}/historic",
            json=data
        )
        
        message_data = {
            "id": response.get("id"),
            "date": response.get("date"),
            "type": "story",
            "media": story_uuid,
            "text": text,
            "user": self._client.user.__dict__ if hasattr(self._client, 'user') else {}
        }
        return Message(message_data, self.uuid, self._client)
        
    async def typing(self) -> None:
        """Send typing indicator"""
        await self._client.http.put(f"/chat/{self.uuid}/typing")
        
    async def mark_as_read(self) -> None:
        """Mark chat as read"""
        await self._client.http.put(
            f"/chat/{self.uuid}/view",
            json={"date": datetime.utcnow().isoformat() + "Z"}
        )
        
    async def get_history(self, limit: int = 50) -> List[Message]:
        """
        Get chat message history
        
        Args:
            limit: Maximum number of messages to retrieve
            
        Returns:
            List of Message objects
        """
        response = await self._client.http.get(f"/chat/{self.uuid}/historic")
        
        if not response:
            return []
            
        messages = []
        message_list = response if isinstance(response, list) else response.get("data", [])
        
        for message_data in message_list[:limit]:
            messages.append(Message(message_data, self.uuid, self._client))
            
        return messages
        
    async def get_new_messages(self, since: datetime) -> List[Message]:
        """
        Get new messages since a specific time
        
        Args:
            since: Get messages after this timestamp
            
        Returns:
            List of Message objects
        """
        date_str = since.isoformat().replace("+00:00", "Z")
        response = await self._client.http.get(
            f"/chat/{self.uuid}/historic/new",
            params={"date": date_str}
        )
        
        if not response:
            return []
            
        messages = []
        message_list = response if isinstance(response, list) else response.get("data", [])
        
        for message_data in message_list:
            messages.append(Message(message_data, self.uuid, self._client))
            
        return messages
        
    async def get_info(self) -> dict:
        """Get chat info (last view time, etc)"""
        return await self._client.http.get(f"/chat/{self.uuid}/info")
