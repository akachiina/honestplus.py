"""
User methods mixin for Honest+ API client.
"""

import logging
from typing import Optional, List, AsyncIterator, TYPE_CHECKING

from ..models.user import User, Profile
from ..models.post import Post

if TYPE_CHECKING:
    from ..http import HTTPClient

logger = logging.getLogger(__name__)


class UserMixin:
    """User profile, search, follow, block/mute, and report methods"""

    if TYPE_CHECKING:
        http: "HTTPClient"
        user: Optional[User]

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
            Configuration dictionary with all current settings
        """
        return await self.http.get("/user/config")

    async def update_user_config(self, **kwargs) -> None:
        """
        Update user configuration/settings

        Only send the fields you want to change.

        Args:
            showAgeRange: Age range options to display (list of ints, e.g. [2, 3, 4, 5, 6])
            allowAnonymousQuestions: Allow anonymous questions (bool)
            allowStoryDiscover: Show stories in discover tab (bool)
            allowQuestionDiscover: Show questions in discover tab (bool)
            allowShowIsOnline: Show online status to others (bool)
            denyAccountPublicAccess: Deny public access to account (bool)
            allowNotifNewQuestion: Notification: new question (bool)
            allowNotifNewAnswer: Notification: new answer (bool)
            allowNotifNewReaction: Notification: new reaction (bool)
            allowNotifNewFollow: Notification: new follow (bool)
            allowNotifNewChatMessage: Notification: new chat message (bool)
            allowNotifNewGroupMessage: Notification: new group message (bool)
            allowNotifNewPostMessage: Notification: new post in feed (bool)
            allowNotifNewPostMention: Notification: post mention (bool)
            allowNotifNewPostReply: Notification: post reply (bool)
            allowOpenChat: Allow opening chat with you (bool)
            allowChatShowView: Show "viewed" status in chat (bool)
            allowChatSendPhoto: Allow sending photos in chat (bool)
        """
        await self.http.put("/user/config", json=kwargs)

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

        # API requires interests to always be a list (not null).
        # Fetch current interests if not provided.
        if interests is None:
            profile = await self.get_profile(self.user.nick)
            interests = profile.interests

        # API requires ALL fields, including nulls for unchanged ones
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

    async def get_user_posts(self, user_uuid: str, limit: Optional[int] = None) -> AsyncIterator[Post]:
        """
        Get posts from a specific user

        Args:
            user_uuid: User's UUID
            limit: Maximum number of posts to fetch

        Yields:
            Post objects
        """
        response = await self.http.get(f"/post/feed/profile/{user_uuid}")

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

    async def delete_profile_data(
        self,
        posts: bool = False,
        comments: bool = False,
        stories: bool = False,
    ) -> None:
        """
        Delete user profile data (posts, comments, stories)

        Args:
            posts: Delete all posts (default: False)
            comments: Delete all comments (default: False)
            stories: Delete all stories (default: False)
        """
        params = {
            "posts": str(posts).lower(),
            "comments": str(comments).lower(),
            "stories": str(stories).lower(),
        }
        await self.http.delete("/user/me/profile/data", params=params)

    async def delete_account(self) -> None:
        """Delete the current user's account permanently"""
        await self.http.delete("/user/me/profile")

    async def add_to_gallery(self, media_uuid: str) -> None:
        """
        Add an uploaded photo to the profile gallery

        Args:
            media_uuid: Media UUID from upload_photo (with media_type="foto")
        """
        await self.http.post(
            "/user/me/photo",
            json={"mediaId": media_uuid}
        )
