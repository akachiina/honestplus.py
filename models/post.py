"""
Post and Comment models
"""

from datetime import datetime
from typing import Optional, List, AsyncIterator, TYPE_CHECKING

from ..enums import ReactionType, PostType, PostVisibility

if TYPE_CHECKING:
    from ..client import Client
    from .user import User


class Comment:
    """
    Represents a comment on a post
    
    Attributes:
        uuid: Comment's unique identifier
        user: User who made the comment
        text: Comment text content
        likes: Number of likes
        dislikes: Number of dislikes
        reaction: Current user's reaction (like/dislike/neutral)
        reply_to_uuid: UUID of parent comment if this is a reply (None for top-level comments)
        created_at: When the comment was created
    """
    
    def __init__(self, data: dict, post_uuid: str, client: "Client"):
        self._client = client
        self._post_uuid = post_uuid
        self._update(data)
        
    def _update(self, data: dict):
        """Update comment data from API response"""
        from .user import User
        
        self.uuid: str = data.get("uuid")
        self.text: str = data.get("text", "")
        self.likes: int = data.get("likes", 0)
        self.dislikes: int = data.get("dislikes", 0)
        self.reaction: str = data.get("reaction", "neutral")
        
        # Parse reply_to_uuid (for threaded replies)
        # API returns a "reply" object: {"uuid": "...", "userId": "...", "userName": "...", "text": "..."}
        reply_obj = data.get("reply")
        if reply_obj and isinstance(reply_obj, dict):
            self.reply_to_uuid: Optional[str] = reply_obj.get("uuid")
        else:
            # Fallback: try flat field names
            self.reply_to_uuid: Optional[str] = (
                data.get("replyToUuid") or
                data.get("reply_to_uuid") or
                data.get("replyTo") or
                data.get("replyId")
            )
        
        # Parse user
        user_data = data.get("user", {})
        self.user: User = User(user_data, self._client)
        
        # Parse timestamp
        created_at = data.get("createdAt")
        self.created_at: Optional[datetime] = None
        if created_at:
            try:
                self.created_at = datetime.fromisoformat(created_at.replace("Z", "+00:00"))
            except:
                pass
                
    def __repr__(self):
        return f"<Comment uuid={self.uuid} user={self.user.nick} text={self.text[:30]}...>"
        
    def __str__(self):
        return f"{self.user.name}: {self.text}"
        
    async def like(self) -> None:
        """Like this comment"""
        await self._client.http.post(
            f"/post/{self._post_uuid}/comments/{self.uuid}/reaction",
            json={"type": ReactionType.LIKE.value}
        )
        self.reaction = ReactionType.LIKE.value
        
    async def dislike(self) -> None:
        """Dislike this comment"""
        await self._client.http.post(
            f"/post/{self._post_uuid}/comments/{self.uuid}/reaction",
            json={"type": ReactionType.DISLIKE.value}
        )
        self.reaction = ReactionType.DISLIKE.value
        
    async def remove_reaction(self) -> None:
        """Remove reaction from this comment"""
        await self._client.http.post(
            f"/post/{self._post_uuid}/comments/{self.uuid}/reaction",
            json={"type": ReactionType.NEUTRAL.value}
        )
        self.reaction = ReactionType.NEUTRAL.value
        
    async def delete(self) -> None:
        """Delete this comment (if you own it)"""
        await self._client.http.delete(f"/post/{self._post_uuid}/comments/{self.uuid}")


class Post:
    """
    Represents a Honest+ post
    
    Attributes:
        uuid: Post's unique identifier
        user: User who created the post
        type: Post type (text, photo, video)
        text: Post text content
        media: Media UUID if post contains media
        comments: Number of comments
        likes: Number of likes
        dislikes: Number of dislikes
        reaction: Current user's reaction (like/dislike/neutral)
        created_at: When the post was created
        visibility: Post visibility (public/private/followers)
    """
    
    def __init__(self, data: dict, client: "Client"):
        self._client = client
        self._update(data)
        
    def _update(self, data: dict):
        """Update post data from API response"""
        from .user import User
        
        self.uuid: str = data.get("uuid")
        self.type: str = data.get("type", PostType.TEXT.value)
        self.text: Optional[str] = data.get("text")
        self.media: Optional[str] = data.get("media")
        self.comments: int = data.get("comments", 0)
        self.likes: int = data.get("likes", 0)
        self.dislikes: int = data.get("dislikes", 0)
        self.reaction: str = data.get("reaction", ReactionType.NEUTRAL.value)
        self.visibility: Optional[str] = data.get("visibility")
        
        # Parse user
        user_data = data.get("user", {})
        self.user: User = User(user_data, self._client)
        
        # Parse timestamp
        created_at = data.get("createdAt")
        self.created_at: Optional[datetime] = None
        if created_at:
            try:
                self.created_at = datetime.fromisoformat(created_at.replace("Z", "+00:00"))
            except:
                pass
                
    def __repr__(self):
        text_preview = self.text[:30] + "..." if self.text and len(self.text) > 30 else self.text
        return f"<Post uuid={self.uuid} user={self.user.nick} text={text_preview}>"
        
    def __str__(self):
        return f"{self.user.name}: {self.text or '[media]'}"
        
    @property
    def media_url(self) -> Optional[str]:
        """Get the full URL for post media"""
        if self.media:
            return f"https://api.honest.plus/v1/media/{self.media}"
        return None
        
    async def like(self) -> None:
        """Like this post"""
        await self._client.http.post(
            f"/post/{self.uuid}/reaction",
            json={"type": ReactionType.LIKE.value}
        )
        self.reaction = ReactionType.LIKE.value
        self.likes += 1
        
    async def dislike(self) -> None:
        """Dislike this post"""
        await self._client.http.post(
            f"/post/{self.uuid}/reaction",
            json={"type": ReactionType.DISLIKE.value}
        )
        self.reaction = ReactionType.DISLIKE.value
        self.dislikes += 1
        
    async def remove_reaction(self) -> None:
        """Remove reaction from this post"""
        await self._client.http.post(
            f"/post/{self.uuid}/reaction",
            json={"type": ReactionType.NEUTRAL.value}
        )
        self.reaction = ReactionType.NEUTRAL.value
        
    async def follow(self) -> None:
        """Follow this post (get notifications for new comments)"""
        await self._client.http.put(f"/post/{self.uuid}/follow")
        
    async def unfollow(self) -> None:
        """Unfollow this post"""
        await self._client.http.delete(f"/post/{self.uuid}/follow")
        
    async def comment(self, text: str, reply_id: Optional[str] = None) -> Comment:
        """
        Add a comment to this post
        
        Args:
            text: Comment text
            reply_id: Optional UUID of comment to reply to
            
        Returns:
            Comment object
        """
        payload = {"text": text}
        if reply_id:
            payload["replyId"] = reply_id
        
        response = await self._client.http.post(
            f"/post/{self.uuid}/comments",
            json=payload
        )
        
        # Fetch the comment to get full data
        # Note: API might return the comment directly, adjust if needed
        self.comments += 1
        return Comment({"uuid": response.get("uuid"), "text": text, "user": self._client.user.__dict__}, self.uuid, self._client)
        
    async def get_comments(self) -> List[Comment]:
        """
        Get all comments on this post
        
        Returns:
            List of Comment objects
        """
        response = await self._client.http.get(f"/post/{self.uuid}/comments")
        
        if not response:
            return []
            
        comments = []
        for comment_data in response if isinstance(response, list) else response.get("data", []):
            comments.append(Comment(comment_data, self.uuid, self._client))
            
        return comments
        
    async def delete(self) -> None:
        """Delete this post (if you own it)"""
        await self._client.http.delete(f"/post/{self.uuid}")
        
    async def refresh(self) -> "Post":
        """Refresh post data from API"""
        response = await self._client.http.get(f"/post/{self.uuid}")
        if response:
            self._update(response)
        return self
