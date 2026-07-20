"""
Main client for honestplus.py
"""

import asyncio
import logging
from datetime import datetime
from typing import Optional, List, Callable, AsyncIterator, Dict, Any

from .http import HTTPClient
from .errors import ValidationError, MediaProcessingError
from .enums import PostVisibility, ReactionType, MediaType
from .models.user import User, Profile
from .models.post import Post, Comment
from .models.notification import Notification, NotificationResume
from .models.chat import Chat, Message
from .models.story import Story, Question

logger = logging.getLogger(__name__)


class Client:
    """
    Main client for interacting with Honest+ API
    
    This is the primary interface for the library. It handles authentication,
    API requests, and event dispatching.
    
    Example:
        ```python
        import honestplus
        
        client = honestplus.Client(token="your_token_here")
        
        @client.event
        async def on_ready():
            print(f"Logged in as {client.user.name}")
        
        await client.start()
        ```
    
    Attributes:
        user: The authenticated user (available after login)
        http: HTTP client for making requests
    """
    
    def __init__(
        self,
        token: Optional[str] = None,
        language: str = "en",
        platform: str = "android",
        version: str = "90",
    ):
        """
        Initialize the Honest+ client
        
        Args:
            token: JWT token for authentication (optional, can login later)
            language: Language code (default: "en")
            platform: Platform identifier (default: "android")
            version: App version (default: "90")
        """
        self.http = HTTPClient(
            token=token,
            language=language,
            platform=platform,
            version=version,
        )
        
        self.user: Optional[User] = None
        self._events: Dict[str, List[Callable]] = {}
        self._running = False
        self._poll_task: Optional[asyncio.Task] = None
        self._last_notification_check: Optional[datetime] = None
        
    async def __aenter__(self):
        await self.http.start()
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()
        
    async def close(self):
        """Close the client and cleanup resources"""
        self._running = False
        if self._poll_task:
            self._poll_task.cancel()
            try:
                await self._poll_task
            except asyncio.CancelledError:
                pass
        await self.http.close()
        logger.info("Client closed")
        
    # ==================== Authentication ====================
    # It is currently broken/unstable; it is better to login using a manual user token

    async def login_google(self, google_token: str, device_id: str, name: Optional[str] = None) -> User:
        """
        Login with Google OAuth token
        
        Args:
            google_token: Google OAuth JWT token
            device_id: Device identifier (e.g., "TQ3A.230901.001")
            name: Optional display name
            
        Returns:
            User object for the authenticated user
        """
        response = await self.http.post(
            "/auth/login/google",
            json={
                "id": device_id,
                "name": name,
                "token": google_token,
            }
        )
        
        if not response or response.get("type") != "logged":
            raise ValidationError("Login failed: Invalid response from server")
            
        # Update token
        self.http.token = response.get("token")
        
        # Create user object
        user_data = response.get("user", {})
        self.user = User(user_data, self)
        
        logger.info(f"Logged in as {self.user.name} (@{self.user.nick})")
        return self.user
        
    async def register_google(self, google_token: str, device_id: str, name: str, nick: str) -> User:
        """
        Register a new account with Google OAuth
        
        Note: This uses the same endpoint as login. If the account doesn't exist,
        it will be created automatically.
        
        Args:
            google_token: Google OAuth JWT token
            device_id: Device identifier
            name: Display name for the new account
            nick: Username/nickname for the new account
            
        Returns:
            User object for the newly created account
        """
        # Honest+ creates accounts automatically on first login
        return await self.login_google(google_token, device_id, name)
        
    async def login_facebook(self, facebook_token: str, device_id: str, name: Optional[str] = None) -> User:
        """
        Login with Facebook OAuth token
        
        Args:
            facebook_token: Facebook OAuth token
            device_id: Device identifier
            name: Optional display name
            
        Returns:
            User object for the authenticated user
        """
        response = await self.http.post(
            "/auth/login/facebook",
            json={
                "id": device_id,
                "name": name,
                "token": facebook_token,
            }
        )
        
        if not response or response.get("type") != "logged":
            raise ValidationError("Login failed: Invalid response from server")
            
        # Update token
        self.http.token = response.get("token")
        
        # Create user object
        user_data = response.get("user", {})
        self.user = User(user_data, self)
        
        logger.info(f"Logged in as {self.user.name} (@{self.user.nick})")
        return self.user
        
    async def logout(self) -> None:
        """Logout from the current session"""
        await self.http.post("/auth/logout")
        self.http.token = None
        self.user = None
        logger.info("Logged out")
        
    async def fetch_current_user(self) -> User:
        """
        Fetch the current authenticated user's information
        
        Returns:
            User object
        """
        if not self.http.token:
            raise ValidationError("Not authenticated. Please login first.")
            
        # Decode JWT to get user info
        import json
        import base64
        
        try:
            # JWT format: header.payload.signature
            payload = self.http.token.split('.')[1]
            # Add padding if needed
            payload += '=' * (4 - len(payload) % 4)
            decoded = json.loads(base64.b64decode(payload))
            
            nick = decoded.get("nick")
            if nick:
                profile = await self.get_profile(nick)
                self.user = profile.user
                return self.user
        except Exception as e:
            logger.error(f"Failed to decode token: {e}")
            
        raise ValidationError("Could not fetch current user")
        
    # ==================== User Methods ====================
    
    async def get_profile(self, nick: str) -> Profile:
        """
        Get a user's profile by nickname
        
        Args:
            nick: User's nickname/username
            
        Returns:
            Profile object
        """
        response = await self.http.get(f"/user/{nick}/profile")
        return Profile(response, self)
        
    async def get_user_config(self) -> dict:
        """
        Get the current user's configuration/settings
        
        Returns:
            Configuration dictionary
        """
        return await self.http.get("/user/config")
        
    async def update_profile(
        self,
        *,
        name: Optional[str] = None,
        nick: Optional[str] = None,
        description: Optional[str] = None,
        photo: Optional[str] = None,
        header: Optional[str] = None,
        show_age: Optional[bool] = None,
        interests: Optional[List[str]] = None,
        networks: Optional[List[dict]] = None,
    ) -> None:
        """
        Update the current user's profile
        
        Args:
            name: Display name
            nick: Username/nickname
            description: Bio/description (max 250 chars)
            photo: Photo UUID (from upload_photo)
            header: Header photo UUID
            show_age: Whether to show age
            interests: List of interests
            networks: List of social networks
        """
        # Enforce 250 character limit for description
        if description and len(description) > 250:
            logger.warning(f"Description too long ({len(description)} chars), truncating to 250")
            description = description[:250]

        data = {
            "push": None,
            "name": name,
            "nick": nick,
            "description": description,
            "photo": photo,
            "header": header,
            "showAge": show_age,
            "interests": interests,
            "networks": networks,
        }
        
        # Remove None values
        data = {k: v for k, v in data.items() if v is not None}
        
        await self.http.put("/user", json=data)
        logger.info("Profile updated")
        
    async def follow_user(self, user_uuid: str) -> None:
        """
        Follow a user
        
        Args:
            user_uuid: UUID of the user to follow
        """
        await self.http.post(f"/follow/{user_uuid}")
        
    async def unfollow_user(self, user_uuid: str) -> None:
        """
        Unfollow a user
        
        Args:
            user_uuid: UUID of the user to unfollow
        """
        await self.http.delete(f"/follow/{user_uuid}")
        
    async def is_user_online(self, nick: str) -> bool:
        """
        Check if a user is online
        
        Args:
            nick: User's nickname
            
        Returns:
            True if online, False otherwise
        """
        response = await self.http.get(f"/user/{nick}/isonline")
        return response.get("isOnline", False) if response else False
        
    # ==================== Post Methods ====================
    
    async def create_post(
        self,
        text: str,
        visibility: str = PostVisibility.PUBLIC.value,
        post_type: str = "text",
    ) -> Post:
        """
        Create a new post
        
        Args:
            text: Post text content
            visibility: Post visibility (public/private/followers)
            post_type: Post type (text/photo/video)
            
        Returns:
            Post object
        """
        response = await self.http.post(
            "/post",
            json={
                "text": text,
                "type": post_type,
                "visibility": visibility,
            }
        )
        
        post_uuid = response.get("uuid")
        
        # Fetch the full post data
        return await self.get_post(post_uuid)
        
    async def get_post(self, post_uuid: str) -> Post:
        """
        Get a post by UUID
        
        Args:
            post_uuid: Post's UUID
            
        Returns:
            Post object
        """
        response = await self.http.get(f"/post/{post_uuid}")
        return Post(response, self)
        
    async def get_feed(self, limit: Optional[int] = None) -> AsyncIterator[Post]:
        """
        Get the general feed with automatic pagination
        
        Args:
            limit: Maximum number of posts to fetch (None for unlimited)
            
        Yields:
            Post objects
        """
        async for post in self._get_feed_paginated("/post/feed/general", limit):
            yield post

    async def get_friends_feed(self, limit: Optional[int] = None) -> AsyncIterator[Post]:
        """
        Get the friends feed (mutual followers)
        
        Args:
            limit: Maximum number of posts to fetch
            
        Yields:
            Post objects
        """
        async for post in self._get_feed_paginated("/post/feed/friends", limit):
            yield post

    async def get_following_feed(self, limit: Optional[int] = None) -> AsyncIterator[Post]:
        """
        Get the following feed (people you follow)
        
        Args:
            limit: Maximum number of posts to fetch
            
        Yields:
            Post objects
        """
        async for post in self._get_feed_paginated("/post/feed/following", limit):
            yield post

    async def _get_feed_paginated(self, endpoint: str, limit: Optional[int] = None) -> AsyncIterator[Post]:
        """Internal helper for paginated feed fetching."""
        next_cursor = None
        count = 0

        while True:
            params = {}
            if next_cursor:
                params["next"] = next_cursor

            response = await self.http.get(endpoint, params=params)

            if not response:
                break

            posts = response.get("data", [])
            has_next = response.get("hasNext", False)

            for post_data in posts:
                post = Post(post_data, self)
                yield post

                count += 1
                if limit and count >= limit:
                    return

            if not has_next or not posts:
                break

            last_post = posts[-1]
            next_cursor = last_post.get("createdAt")
            
    async def delete_post(self, post_uuid: str) -> None:
        """
        Delete a post
        
        Args:
            post_uuid: UUID of the post to delete
        """
        await self.http.delete(f"/post/{post_uuid}")
        
    async def search_posts(self, query: str, limit: int = 20) -> List[Post]:
        """
        Search for posts by content
        
        Args:
            query: Search query
            limit: Maximum number of results
            
        Returns:
            List of Post objects
        """
        response = await self.http.get(
            "/post/search",
            params={"q": query, "limit": limit}
        )
        
        if not response:
            return []
            
        posts = []
        post_list = response if isinstance(response, list) else response.get("data", [])
        
        for post_data in post_list:
            posts.append(Post(post_data, self))
            
        return posts
        
    async def create_poll_post(
        self,
        text: str,
        options: List[str],
        visibility: str = PostVisibility.PUBLIC.value,
        is_anonymous: bool = False,
        allows_multiple: bool = True,
    ) -> Post:
        """
        Create a poll post
        
        Args:
            text: Poll question
            options: List of poll options (2-4 options)
            visibility: Post visibility (public/private/followers)
            is_anonymous: Whether votes are anonymous
            allows_multiple: Whether users can vote for multiple options
            
        Returns:
            Post object
        """
        if len(options) < 2 or len(options) > 4:
            raise ValidationError("Poll must have 2-4 options")
            
        response = await self.http.post(
            "/post",
            json={
                "text": text,
                "type": "poll",
                "visibility": visibility,
                "poll": {
                    "options": options,
                    "isAnonymous": is_anonymous,
                    "allowsMultiple": allows_multiple,
                }
            }
        )
        
        post_uuid = response.get("uuid")
        return await self.get_post(post_uuid)
        
    async def get_poll_details(self, post_uuid: str) -> dict:
        """
        Get poll details including votes
        
        Args:
            post_uuid: UUID of the poll post
            
        Returns:
            Poll details with options, votes, and voters
        """
        return await self.http.get(f"/post/{post_uuid}/poll")
        
    async def vote_poll(self, post_uuid: str, option_uuids: List[str]) -> dict:
        """
        Vote on a poll
        
        Args:
            post_uuid: UUID of the poll post
            option_uuids: List of option UUIDs to vote for
            
        Returns:
            Updated poll details
        """
        return await self.http.post(
            f"/post/{post_uuid}/poll/vote",
            json={"votes": option_uuids}
        )
        
    # ==================== Notification Methods ====================
    
    async def get_notification_resume(self) -> NotificationResume:
        """
        Get a summary of unread notifications
        
        Returns:
            NotificationResume object
        """
        response = await self.http.get("/notification/resume")
        return NotificationResume(response)
        
    async def get_notifications(self, limit: Optional[int] = None) -> AsyncIterator[Notification]:
        """
        Get notifications with automatic pagination
        
        Args:
            limit: Maximum number of notifications to fetch
            
        Yields:
            Notification objects
        """
        # Note: Pagination for notifications might work differently
        # Adjust if needed based on API behavior
        response = await self.http.get("/notification")
        
        if not response:
            return
            
        notifications = response.get("data", [])
        count = 0
        
        for notif_data in notifications:
            notif = Notification(notif_data, self)
            yield notif
            
            count += 1
            if limit and count >= limit:
                return
                
    # ==================== Chat Methods ====================
    
    async def get_chats(self) -> List[Chat]:
        """
        Get all chat conversations
        
        Returns:
            List of Chat objects
        """
        response = await self.http.get("/chat")
        
        if not response:
            return []
            
        chats = []
        chat_list = response if isinstance(response, list) else response.get("data", [])
        
        for chat_data in chat_list:
            chats.append(Chat(chat_data, self))
            
        return chats
        
    async def get_chat_by_user(self, user_uuid: str) -> Chat:
        """
        Get or create a chat with a user
        
        Args:
            user_uuid: UUID of the user to chat with
            
        Returns:
            Chat object
        """
        response = await self.http.get(f"/chat/user/{user_uuid}")
        chat_uuid = response.get("token")
        return Chat({"uuid": chat_uuid}, self)
        
    async def get_chat(self, chat_uuid: str) -> Chat:
        """
        Get a specific chat by UUID
        
        Args:
            chat_uuid: Chat's UUID
            
        Returns:
            Chat object
        """
        # Create chat object (might need to fetch info)
        chat = Chat({"uuid": chat_uuid}, self)
        return chat
        
    # ==================== Media Methods ====================
    
    async def upload_photo(
        self,
        file_path: str,
        media_type: str = MediaType.CHAT.value,
        auto_prepare: bool = True,
        background_color: str = "black",
    ) -> str:
        """
        Upload a photo
        
        Args:
            file_path: Path to the image file
            media_type: Type of media (chat/profile/header/story)
            auto_prepare: Auto-prepare image for story format (only applies to stories)
                         When True, images are automatically adjusted to 1037x1843
                         with letterboxing to fit the entire image
            background_color: Letterboxing color for stories (default: "black")
                             Can be color name or RGB tuple
            
        Returns:
            Media UUID
            
        Note:
            For stories (media_type="story"), images are automatically prepared
            to the correct aspect ratio (9:16) unless auto_prepare=False.
            This ensures proper display without cropping.
        """
        import aiohttp
        import os
        from .utils import prepare_image_for_story
        
        # Auto-prepare image for story format if needed
        prepared_file = None
        upload_path = file_path
        
        if media_type == MediaType.STORY.value and auto_prepare:
            logger.info("Auto-preparing image for story format (1037x1843)...")
            try:
                prepared_file = prepare_image_for_story(
                    file_path,
                    background_color=background_color
                )
                upload_path = prepared_file
                logger.debug(f"Using prepared image: {upload_path}")
            except Exception as e:
                logger.warning(f"Failed to auto-prepare image: {e}. Using original.")
                upload_path = file_path
        
        try:
            # Create multipart form data
            data = aiohttp.FormData()
            data.add_field("type", media_type)
            
            # Open file and add to form data
            with open(upload_path, "rb") as f:
                data.add_field(
                    "file",
                    f,
                    filename="file.jpg",
                    content_type="image/jpeg"
                )
                
                # Send request (aiohttp will set content-type automatically)
                response = await self.http.post(
                    "/media/photo",
                    data=data
                )
            
            media_uuid = response.get("uuid")
            logger.info(f"Uploaded photo: {media_uuid}")
            return media_uuid
            
        finally:
            # Clean up temporary prepared file if it was created
            if prepared_file and os.path.exists(prepared_file):
                try:
                    os.remove(prepared_file)
                    logger.debug(f"Cleaned up temporary file: {prepared_file}")
                except Exception as e:
                    logger.warning(f"Failed to clean up temporary file: {e}")
        
    async def wait_for_media(self, media_uuid: str, timeout: int = 30) -> None:
        """
        Wait for media to finish processing
        
        Args:
            media_uuid: Media UUID
            timeout: Maximum time to wait in seconds
        """
        start_time = asyncio.get_event_loop().time()
        
        while True:
            response = await self.http.get(f"/media/{media_uuid}/status")
            status = response.get("status")
            
            if status == "ready":
                logger.info(f"Media {media_uuid} is ready")
                return
            elif status == "error":
                error = response.get("error", "Unknown error")
                raise MediaProcessingError(f"Media processing failed: {error}")
                
            # Check timeout
            if asyncio.get_event_loop().time() - start_time > timeout:
                raise MediaProcessingError(f"Media processing timeout after {timeout}s")
                
            # Wait before checking again
            await asyncio.sleep(1)
            
    # ==================== Story Methods ====================
    
    async def create_story(
        self,
        media_uuid: str,
        items: Optional[List[dict]] = None,
        question_uuid: Optional[str] = None,
        question_dx: float = 0.0,
        question_dy: float = -200.0,
        question_scale: float = 1.0,
        question_color: int = 0,
    ) -> Story:
        """
        Create a new story

        Args:
            media_uuid: Media UUID (from upload_photo)
            items: Optional list of items (stickers, text) with positioning.
                   Example: [{"type": "sticker", "id": "sticker_id",
                             "dx": 0, "dy": 0, "rotate": 0, "scale": 1}]
            question_uuid: UUID of the question being answered. When provided,
                           automatically adds a "question" item so the question
                           bubble appears visually linked to the story.
            question_dx: Horizontal offset of the question sticker (default: 0.0)
            question_dy: Vertical offset of the question sticker (default: -200.0,
                         positioning it in the upper portion of the story)
            question_scale: Scale of the question sticker (default: 1.0)
            question_color: Color variant of the question sticker (default: 0)

        Returns:
            Story object
        """
        # Start with provided items (or empty list)
        story_items = list(items or [])

        # Automatically add the question sticker if a question_uuid is given
        if question_uuid:
            story_items.append({
                "type": "question",
                "id": question_uuid,
                "dx": question_dx,
                "dy": question_dy,
                "rotate": 0.0,
                "scale": question_scale,
                "color": question_color,
            })

        data = {
            "mediaId": media_uuid,
            "items": story_items,
        }

        response = await self.http.post("/story", json=data)
        story_uuid = response.get("uuid")

        # Create Story object from response data
        # Note: The API doesn't return full story details immediately after creation
        story_data = {
            "uuid": story_uuid,
            "media": media_uuid,
            "type": "photo",
            "user": self.user.__dict__ if self.user else {},
        }

        logger.info(f"Created story: {story_uuid}")
        return Story(story_data, self)
        
    async def get_my_story_info(self) -> List[dict]:
        """
        Get info about your own stories (views, likes, highlighted status)
        
        Returns:
            List of story info dicts with uuid, likes, views, highlighted
        """
        response = await self.http.get("/story/user/me/info")
        return response if response else []
    
    async def get_story_feed(self) -> List[Story]:
        """
        Get story feed with proper user context
        
        Returns:
            List of Story objects with user information
        """
        response = await self.http.get("/story/feed")
        
        if not response:
            return []
            
        stories = []
        data = response.get("data", [])
        
        # Feed response has structure: [{user: {...}, stories: [...]}, ...]
        for user_entry in data:
            user_data = user_entry.get("user", {})
            story_list = user_entry.get("stories", [])
            
            for story_data in story_list:
                # Pass user_data to Story constructor
                story = Story(story_data, self, user_data=user_data)
                stories.append(story)
                
        return stories
        
    async def get_user_stories(self, user_uuid: str) -> List[Story]:
        """
        Get stories from a specific user
        
        Args:
            user_uuid: User's UUID
            
        Returns:
            List of Story objects
        """
        response = await self.http.get(f"/story/user/{user_uuid}")
        
        if not response:
            return []
            
        stories = []
        story_list = response if isinstance(response, list) else response.get("data", [])
        
        for story_data in story_list:
            stories.append(Story(story_data, self))
            
        return stories
        
    async def get_story(self, story_uuid: str) -> Story:
        """
        Get a story by UUID
        
        Args:
            story_uuid: Story's UUID
            
        Returns:
            Story object
        """
        response = await self.http.get(f"/story/{story_uuid}")
        return Story(response, self)
        
    async def delete_story(self, story_uuid: str) -> None:
        """
        Delete a story
        
        Args:
            story_uuid: UUID of the story to delete
        """
        await self.http.delete(f"/story/{story_uuid}")
        
    # ==================== Sticker Methods ====================
    
    async def get_trending_stickers(self) -> List[dict]:
        """
        Get trending stickers from Giphy
        
        Returns:
            List of sticker dicts with id, live (URL), preview (URL), ratio
        """
        response = await self.http.get("/sticker/trending")
        
        if not response:
            return []
            
        return response.get("data", [])
        
    # ==================== Question Methods ====================
    
    async def get_question_categories(self) -> List[dict]:
        """
        Get available question categories
        
        Returns:
            List of categories with uuid and color
        """
        response = await self.http.get("/category")
        return response if response else []
        
    async def get_users_accepting_questions(self, page: int = 0) -> dict:
        """
        Get list of users who accept questions (from your following)
        
        Args:
            page: Page number for pagination
            
        Returns:
            Dict with 'data' (list of users) and 'hasNext' (bool)
        """
        response = await self.http.get(f"/follow/share", params={"page": page})
        return response if response else {"data": [], "hasNext": False}
    
    async def send_question(
        self,
        text: str,
        category: str = "personal",
        anonymous: bool = True,
        user_uuids: Optional[List[str]] = None,
    ) -> None:
        """
        Send a question to users
        
        Args:
            text: Question text (max 150 characters)
            category: Category UUID (personal, friendship, relationship, etc)
            anonymous: Whether to send anonymously
            user_uuids: List of user UUIDs to send to (None = send to all followers)
            
        Raises:
            ValidationError: If text exceeds 150 characters
            
        Note:
            - If user_uuids is None or empty, sends to all followers (type="all")
            - If user_uuids is provided, sends only to those users (type="some")
        """
        # Validate character limit
        if len(text) > 150:
            raise ValidationError(f"Question text too long: {len(text)} chars (max 150)")
        
        if user_uuids:
            question_type = "some"
            ids = user_uuids
        else:
            question_type = "all"
            ids = []
            
        await self.http.post(
            "/ask",
            json={
                "text": text,
                "category": category,
                "anonymous": anonymous,
                "type": question_type,
                "ids": ids,
            }
        )
        
    async def get_questions_received(self, limit: Optional[int] = None) -> AsyncIterator[Question]:
        """
        Get questions you received (from /ask endpoint)
        
        Args:
            limit: Maximum number of questions to fetch
            
        Yields:
            Question objects with additional metadata (type, viewed, directed)
        """
        response = await self.http.get("/ask")
        
        if not response:
            return
            
        questions_data = response.get("data", [])
        count = 0
        
        for item in questions_data:
            # Extract data from nested structure
            question_data = item.get("question", {})
            
            # Add extra metadata
            question_data["type"] = item.get("type")
            question_data["viewed"] = item.get("viewed")
            question_data["directed"] = item.get("directed")
            
            # Map 'creator' to 'user' for compatibility with Question model
            if "creator" in question_data:
                question_data["user"] = question_data.pop("creator")
            
            question = Question(question_data, self)
            yield question
            
            count += 1
            if limit and count >= limit:
                return
                
    async def get_questions_sent(self, limit: Optional[int] = None) -> AsyncIterator[Question]:
        """
        Get questions you sent
        
        Args:
            limit: Maximum number of questions to fetch
            
        Yields:
            Question objects
        """
        response = await self.http.get("/question/sent")
        
        if not response:
            return
            
        questions = response.get("data", [])
        count = 0
        
        for question_data in questions:
            question = Question(question_data, self)
            yield question
            
            count += 1
            if limit and count >= limit:
                return
                
    async def delete_question(self, question_uuid: str) -> None:
        """
        Delete a question
        
        Args:
            question_uuid: UUID of the question to delete
        """
        await self.http.delete(f"/question/{question_uuid}")
        
    async def get_ask_questions(self) -> List[dict]:
        """
        Get questions available to answer (optimized for story responses)
        
        Returns:
            List of question objects with format:
            {
                "question": {
                    "uuid": str,
                    "creator": dict or None (None if anonymous),
                    "category": {"uuid": str, "color": str},
                    "text": str,
                    "createdAt": str
                },
                "type": str (e.g., "diary", "user"),
                "viewed": bool,
                "directed": bool
            }
        """
        response = await self.http.get("/ask")
        
        if not response:
            return []
            
        return response.get("data", [])
        
    # ==================== User Search Methods ====================
    
    async def search_users(self, query: str, limit: int = 20) -> List[User]:
        """
        Search for users by name or nickname
        
        Args:
            query: Search query
            limit: Maximum number of results
            
        Returns:
            List of User objects
        """
        response = await self.http.get(
            "/user/search",
            params={"q": query, "limit": limit}
        )
        
        if not response:
            return []
            
        users = []
        user_list = response if isinstance(response, list) else response.get("data", [])
        
        for user_data in user_list:
            users.append(User(user_data, self))
            
        return users
        
    async def get_followers(self, user_uuid: str, page: int = 0) -> dict:
        """
        Get a user's followers
        
        Args:
            user_uuid: User's UUID
            page: Page number for pagination
            
        Returns:
            Dict with 'data' (list of follower objects) and 'hasNext' (bool)
        """
        response = await self.http.get(
            f"/follow/{user_uuid}/followers",
            params={"page": page}
        )
        
        if not response:
            return {"data": [], "hasNext": False}
            
        return response
        
    async def get_following(self, user_uuid: str, page: int = 0) -> dict:
        """
        Get users that a user is following
        
        Args:
            user_uuid: User's UUID
            page: Page number for pagination
            
        Returns:
            Dict with 'data' (list of following objects) and 'hasNext' (bool)
        """
        response = await self.http.get(
            f"/follow/{user_uuid}/following",
            params={"page": page}
        )
        
        if not response:
            return {"data": [], "hasNext": False}
            
        return response
        
    # ==================== Block/Mute Methods ====================
    
    async def block_user(self, user_uuid: str) -> None:
        """
        Block a user
        
        Args:
            user_uuid: UUID of the user to block
        """
        await self.http.post("/block", json={"type": "profile", "id": user_uuid})
        
    async def unblock_user(self, block_id: str) -> None:
        """
        Unblock a user
        
        Args:
            block_id: ID of the block record (not the user UUID)
        """
        await self.http.delete(f"/block/{block_id}")
        
    async def get_blocked_users(self) -> List[User]:
        """
        Get list of blocked users
        
        Returns:
            List of User objects (with _block_id attribute attached)
        """
        response = await self.http.get("/block")
        
        if not response:
            return []

        users = []
        # API returns a list directly: [{"id": "...", "user": {...}, "type": "profile", ...}]
        block_list = response if isinstance(response, list) else response.get("data", [])

        for block_data in block_list:
            user_data = block_data.get("user", {})
            block_id = block_data.get("id")
            if user_data:
                user_obj = User(user_data, self)
                user_obj._block_id = block_id
                users.append(user_obj)

        return users
        
    async def mute_user(self, user_uuid: str) -> None:
        """
        Mute a user
        
        Args:
            user_uuid: UUID of the user to mute
        """
        await self.http.post(f"/user/{user_uuid}/mute")
        
    async def unmute_user(self, user_uuid: str) -> None:
        """
        Unmute a user
        
        Args:
            user_uuid: UUID of the user to unmute
        """
        await self.http.delete(f"/user/{user_uuid}/mute")
        
    # ==================== User Posts Methods ====================
    
    async def get_user_posts(self, user_uuid: str, limit: Optional[int] = None) -> AsyncIterator[Post]:
        """
        Get posts from a specific user
        
        Args:
            user_uuid: User's UUID
            limit: Maximum number of posts to fetch
            
        Yields:
            Post objects
        """
        response = await self.http.get(f"/user/{user_uuid}/posts")
        
        if not response:
            return
            
        posts = response.get("data", [])
        count = 0
        
        for post_data in posts:
            post = Post(post_data, self)
            yield post
            
            count += 1
            if limit and count >= limit:
                return
                
    # ==================== Report Methods ====================
    
    async def report_post(self, post_uuid: str, reason: str) -> None:
        """
        Report a post
        
        Args:
            post_uuid: UUID of the post to report
            reason: Reason for reporting
        """
        await self.http.post(
            f"/post/{post_uuid}/report",
            json={"reason": reason}
        )
        
    async def report_user(self, user_uuid: str, reason: str) -> None:
        """
        Report a user
        
        Args:
            user_uuid: UUID of the user to report
            reason: Reason for reporting
        """
        await self.http.post(
            f"/user/{user_uuid}/report",
            json={"reason": reason}
        )
        
    async def report_comment(self, post_uuid: str, comment_uuid: str, reason: str) -> None:
        """
        Report a comment
        
        Args:
            post_uuid: UUID of the post
            comment_uuid: UUID of the comment to report
            reason: Reason for reporting
        """
        await self.http.post(
            f"/post/{post_uuid}/comments/{comment_uuid}/report",
            json={"reason": reason}
        )
        
    # ==================== Event System ====================
    
    def event(self, func: Callable) -> Callable:
        """
        Decorator to register an event handler
        
        Example:
            ```python
            @client.event
            async def on_ready():
                print("Bot is ready!")
            ```
        """
        event_name = func.__name__
        if event_name not in self._events:
            self._events[event_name] = []
        self._events[event_name].append(func)
        logger.debug(f"Registered event handler: {event_name}")
        return func
        
    async def _dispatch(self, event_name: str, *args, **kwargs):
        """Dispatch an event to all registered handlers"""
        handlers = self._events.get(event_name, [])
        for handler in handlers:
            try:
                await handler(*args, **kwargs)
            except Exception as e:
                logger.error(f"Error in event handler {event_name}: {e}", exc_info=True)
                
    async def _poll_notifications(self, interval: float):
        """Poll for new notifications"""
        logger.info(f"Starting notification polling (interval: {interval}s)")
        
        while self._running:
            try:
                # Get notification resume
                resume = await self.get_notification_resume()
                
                # If there are new notifications, fetch them
                if resume.has_unread:
                    async for notification in self.get_notifications(limit=20):
                        # Only dispatch if not read
                        if not notification.is_read:
                            await self._dispatch("on_notification", notification)
                            
                            # Dispatch specific events based on type
                            if notification.type == "follow":
                                await self._dispatch("on_follow", notification.user)
                            elif notification.type == "comment":
                                await self._dispatch("on_comment", notification)
                            elif notification.type == "mention":
                                await self._dispatch("on_mention", notification)
                                
            except Exception as e:
                logger.error(f"Error polling notifications: {e}", exc_info=True)
                
            await asyncio.sleep(interval)
            
    async def start(self, poll_interval: float = 15.0):
        """
        Start the client and begin polling for events
        
        Args:
            poll_interval: How often to check for new notifications (in seconds)
        """
        await self.http.start()
        
        # Fetch current user if we have a token
        if self.http.token and not self.user:
            try:
                await self.fetch_current_user()
            except Exception as e:
                logger.warning(f"Could not fetch current user: {e}")
                
        # Dispatch ready event
        await self._dispatch("on_ready")
        
        # Start polling
        self._running = True
        self._poll_task = asyncio.create_task(self._poll_notifications(poll_interval))
        
        try:
            await self._poll_task
        except asyncio.CancelledError:
            pass
