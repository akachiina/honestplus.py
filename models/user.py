"""
User and Profile models
"""

from datetime import datetime
from typing import Optional, List, TYPE_CHECKING

if TYPE_CHECKING:
    from ..client import Client


class User:
    """
    Represents a Honest+ user
    
    Attributes:
        uuid: User's unique identifier
        name: User's display name
        nick: User's username/nickname
        photo: Photo UUID (can be used to construct image URL)
        last_story: Timestamp of last story posted
        is_admin: Whether user is an admin
    """
    
    def __init__(self, data: dict, client: "Client"):
        self._client = client
        self._update(data)
        
    def _update(self, data: dict):
        """Update user data from API response"""
        self.uuid: str = data.get("uuid")
        self.name: str = data.get("name")
        self.nick: str = data.get("nick")
        self.profile_photo: Optional[str] = data.get("photo")
        self.is_admin: bool = data.get("isAdmin", False)

        # Parse last_story timestamp
        last_story = data.get("lastStory")
        self.last_story: Optional[datetime] = None
        if last_story:
            try:
                self.last_story = datetime.fromisoformat(last_story.replace("Z", "+00:00"))
            except:
                pass

    def __repr__(self):
        return f"<User uuid={self.uuid} nick={self.nick} name={self.name}>"

    def __str__(self):
        return f"{self.name} (@{self.nick})"

    @property
    def profile_photo_url(self) -> Optional[str]:
        """Get the full URL for the profile photo"""
        if self.profile_photo:
            return f"https://honest.nyc3.digitaloceanspaces.com/{self.uuid}/p/{self.profile_photo}.jpg"
        return None

    async def follow(self) -> None:
        """Follow this user"""
        await self._client.http.post(f"/follow/{self.uuid}")
        
    async def unfollow(self) -> None:
        """Unfollow this user"""
        await self._client.http.delete(f"/follow/{self.uuid}")
        
    async def get_profile(self) -> "Profile":
        """Get detailed profile for this user"""
        return await self._client.get_profile(self.nick)
        
    async def get_posts(self, limit: int = 20):
        """Get posts from this user (if implemented by API)"""
        # Note: This endpoint might not exist, needs verification
        raise NotImplementedError("User posts endpoint not yet implemented")


class Profile:
    """
    Represents a detailed user profile
    
    Attributes:
        user: Basic user information
        header_photo: Header/banner photo UUID
        description: User's bio/description
        following: Number of users they follow
        followers: Number of followers
        is_following: Whether the authenticated user follows this profile
        is_private: Whether the profile is private
        allow_anonymous: Whether anonymous questions are allowed
        common: List of common followers/following
        interests: List of user interests
        networks: List of social networks
        highlights: List of story highlights
        photos: List of photo UUIDs with timestamps
    """
    
    def __init__(self, data: dict, client: "Client"):
        self._client = client
        self._update(data)
        
    def _update(self, data: dict):
        """Update profile data from API response"""
        # Basic user info
        user_data = data.get("user", {})
        self.user = User(user_data, self._client)
        
        # Profile details
        self.header_photo: Optional[str] = data.get("headerPhoto")
        self.description: Optional[str] = data.get("description")
        self.following: int = data.get("following", 0)
        self.followers: int = data.get("followers", 0)
        self.is_following: bool = data.get("isFollowing", False)
        self.is_private: bool = data.get("isPrivate", False)
        self.allow_anonymous: bool = data.get("allowAnonymous", False)
        
        # Lists
        self.common: List[dict] = data.get("common", [])
        self.interests: List[str] = data.get("interests", [])
        self.networks: List[dict] = data.get("networks", [])
        self.highlights: List[dict] = data.get("highlights", [])
        
        # Gallery photos with timestamps
        self.gallery_photos: List[dict] = []
        for photo in data.get("photos", []):
            photo_data = {
                "uuid": photo.get("uuid"),
                "created_at": None,
            }
            created_at = photo.get("createdAt")
            if created_at:
                try:
                    photo_data["created_at"] = datetime.fromisoformat(created_at.replace("Z", "+00:00"))
                except:
                    pass
            self.gallery_photos.append(photo_data)
            
    def __repr__(self):
        return f"<Profile user={self.user.nick} followers={self.followers} following={self.following}>"
        
    def __str__(self):
        return f"{self.user.name} (@{self.user.nick}) - {self.followers} followers"
        
    @property
    def header_photo_url(self) -> Optional[str]:
        """Get the full URL for header photo"""
        if self.header_photo:
            return f"https://honest.nyc3.digitaloceanspaces.com/{self.user.uuid}/h/{self.header_photo}.jpg"
        return None
        
    def get_gallery_photo_url(self, photo_uuid: str, thumbnail: bool = False) -> str:
        """
        Get URL for a gallery photo
        
        Args:
            photo_uuid: UUID of the photo from the gallery
            thumbnail: If True, returns thumbnail version (_thumb.jpg)
        
        Returns:
            Full URL to the photo
        """
        if thumbnail:
            return f"https://honest.nyc3.digitaloceanspaces.com/{self.user.uuid}/f/{photo_uuid}_thumb.jpg"
        else:
            return f"https://honest.nyc3.digitaloceanspaces.com/{self.user.uuid}/f/{photo_uuid}.jpg"
    
    @property
    def gallery_photo_urls(self) -> List[dict]:
        """
        Get URLs for all gallery photos
        
        Returns:
            List of dicts with 'uuid', 'created_at', 'url', and 'thumbnail_url'
        """
        urls = []
        for photo in self.gallery_photos:
            urls.append({
                'uuid': photo.get('uuid'),
                'created_at': photo.get('created_at'),
                'url': self.get_gallery_photo_url(photo.get('uuid'), thumbnail=False),
                'thumbnail_url': self.get_gallery_photo_url(photo.get('uuid'), thumbnail=True),
            })
        return urls
        
    async def follow(self) -> None:
        """Follow this user"""
        await self.user.follow()
        self.is_following = True
        
    async def unfollow(self) -> None:
        """Unfollow this user"""
        await self.user.unfollow()
        self.is_following = False
        
    async def refresh(self) -> "Profile":
        """Refresh profile data from API"""
        updated_profile = await self._client.get_profile(self.user.nick)
        self._update(updated_profile.__dict__)
        return self
