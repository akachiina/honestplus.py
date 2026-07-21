"""
Story and sticker methods mixin for Honest+ API client.
"""

import logging
from typing import Optional, List, TYPE_CHECKING

from ..models.story import Story

if TYPE_CHECKING:
    from ..http import HTTPClient

logger = logging.getLogger(__name__)


class StoryMixin:
    """Story and sticker methods"""

    if TYPE_CHECKING:
        http: "HTTPClient"
        user: Optional["User"]

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

        for user_entry in data:
            user_data = user_entry.get("user", {})
            story_list = user_entry.get("stories", [])

            for story_data in story_list:
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
