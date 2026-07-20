"""
Story model
"""

from datetime import datetime
from typing import Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from ..client import Client
    from .user import User


class Story:
    """
    Represents a story
    
    Attributes:
        uuid: Story's unique identifier
        user: User who posted the story
        items: List of overlays (questions, stickers) on the story
        liked: Whether the current user has liked this story
        media_url: URL to the story image
        created_at: When the story was created
    """
    
    def __init__(self, data: dict, client: "Client", user_data: Optional[dict] = None):
        self._client = client
        self._update(data, user_data)
        
    def _update(self, data: dict, user_data: Optional[dict] = None):
        """Update story data from API response"""
        from .user import User
        
        self.uuid: str = data.get("uuid")
        self.items: list = data.get("items", [])
        self.liked: bool = data.get("liked", False)
        
        # Parse user (from parent object in feed response)
        if user_data:
            self.user: Optional[User] = User(user_data, self._client)
        else:
            user_raw = data.get("user")
            self.user = User(user_raw, self._client) if user_raw else None

        # Media URL — pattern: {user_uuid}/s/{story_uuid}.jpg
        if self.user and self.uuid:
            self.media_url: Optional[str] = f"https://honest.nyc3.digitaloceanspaces.com/{self.user.uuid}/s/{self.uuid}.jpg"
        else:
            self.media_url = None

        # Parse timestamps
        created_at = data.get("createdAt")
        self.created_at: Optional[datetime] = None
        if created_at:
            try:
                self.created_at = datetime.fromisoformat(created_at.replace("Z", "+00:00"))
            except Exception:
                pass

    def has_question_response(self) -> bool:
        """Check if this story is answering a question"""
        return any(item.get("type") == "question" for item in self.items)
    
    def get_question_info(self) -> Optional[dict]:
        """
        Get question info if this story is a response
        
        Returns:
            Question dict with uuid, text, creator, etc. or None
        """
        for item in self.items:
            if item.get("type") == "question":
                return item.get("question")
        return None
    
    def has_stickers(self) -> bool:
        """Check if this story has stickers"""
        return any(item.get("type") == "sticker" for item in self.items)
                
    def __repr__(self):
        return f"<Story uuid={self.uuid} user={self.user.nick if self.user else 'None'}>"
        
    def __str__(self):
        if self.user:
            return f"Story by {self.user.name}"
        return f"Story {self.uuid}"
        
    async def view(self) -> None:
        """Mark story as viewed"""
        await self._client.http.post(f"/story/{self.uuid}/viewed")
        
    async def like(self) -> None:
        """Like this story"""
        await self._client.http.post(f"/story/{self.uuid}/like")
        self.liked = True
        
    async def unlike(self) -> None:
        """Unlike this story"""
        await self._client.http.delete(f"/story/{self.uuid}/like")
        self.liked = False
        
    async def get_info(self) -> dict:
        """
        Get story info (views and likes)
        
        Returns:
            Dict with views and likes data
        """
        return await self._client.http.get(f"/story/{self.uuid}/info")
        
    async def delete(self) -> None:
        """Delete this story (if you own it)"""
        await self._client.http.delete(f"/story/{self.uuid}")
        
    async def refresh(self) -> "Story":
        """Refresh story data from API"""
        response = await self._client.http.get(f"/story/{self.uuid}")
        if response:
            self._update(response)
        return self


class Question:
    """
    Represents a question
    
    Attributes:
        uuid: Question's unique identifier
        user: User who asked (None if anonymous)
        recipient: User who received the question
        text: Question text
        answer: Answer text (if answered)
        is_anonymous: Whether question is anonymous
        is_answered: Whether question has been answered
        created_at: When the question was created
        answered_at: When the question was answered
    """
    
    def __init__(self, data: dict, client: "Client"):
        self._client = client
        self._update(data)
        
    def _update(self, data: dict):
        """Update question data from API response"""
        from .user import User
        
        self.uuid: str = data.get("uuid")
        self.text: str = data.get("text", "")
        self.answer: Optional[str] = data.get("answer")
        self.is_anonymous: bool = data.get("isAnonymous", False)
        self.is_answered: bool = data.get("isAnswered", False)
        
        # Parse user (who asked)
        user_data = data.get("user", {})
        if user_data and not self.is_anonymous:
            self.user: Optional[User] = User(user_data, self._client)
        else:
            self.user = None
            
        # Parse recipient (who received)
        recipient_data = data.get("recipient", {})
        if recipient_data:
            self.recipient: Optional[User] = User(recipient_data, self._client)
        else:
            self.recipient = None
        
        # Parse timestamps
        created_at = data.get("createdAt")
        self.created_at: Optional[datetime] = None
        if created_at:
            try:
                self.created_at = datetime.fromisoformat(created_at.replace("Z", "+00:00"))
            except:
                pass
                
        answered_at = data.get("answeredAt")
        self.answered_at: Optional[datetime] = None
        if answered_at:
            try:
                self.answered_at = datetime.fromisoformat(answered_at.replace("Z", "+00:00"))
            except:
                pass
                
    def __repr__(self):
        return f"<Question uuid={self.uuid} answered={self.is_answered}>"
        
    def __str__(self):
        status = "Answered" if self.is_answered else "Pending"
        return f"[{status}] {self.text[:50]}..."
        
    async def answer(self, text: str) -> None:
        """
        Answer this question
        
        Args:
            text: Answer text
        """
        await self._client.http.post(
            f"/question/{self.uuid}/answer",
            json={"text": text}
        )
        self.answer = text
        self.is_answered = True
        self.answered_at = datetime.now()
        
    async def delete(self) -> None:
        """Delete this question"""
        await self._client.http.delete(f"/question/{self.uuid}")
