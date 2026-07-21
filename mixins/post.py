"""
Post methods mixin for Honest+ API client.
"""

import logging
from typing import Optional, List, AsyncIterator, TYPE_CHECKING

from ..errors import ValidationError
from ..enums import PostVisibility
from ..models.post import Post, Comment

if TYPE_CHECKING:
    from ..http import HTTPClient

logger = logging.getLogger(__name__)


class PostMixin:
    """Post creation, feed, polls, and report methods"""

    if TYPE_CHECKING:
        http: "HTTPClient"

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

    async def follow_post(self, post_uuid: str) -> None:
        """
        Follow a post to receive notifications for new comments

        Args:
            post_uuid: UUID of the post to follow
        """
        await self.http.put(f"/post/{post_uuid}/follow")

    async def unfollow_post(self, post_uuid: str) -> None:
        """
        Unfollow a post to stop receiving notifications

        Args:
            post_uuid: UUID of the post to unfollow
        """
        await self.http.delete(f"/post/{post_uuid}/follow")
