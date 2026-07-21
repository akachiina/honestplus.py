"""
Discover tab methods mixin for Honest+ API client.
"""

import logging
from typing import List, TYPE_CHECKING

from ..models.user import User
from ..models.story import Story

if TYPE_CHECKING:
    from ..http import HTTPClient

logger = logging.getLogger(__name__)


class DiscoverMixin:
    """Discover tab methods (users, questions, stories)"""

    if TYPE_CHECKING:
        http: "HTTPClient"

    async def discover_users(self) -> List[User]:
        """
        Get user suggestions from the Discover tab

        Returns:
            List of User objects
        """
        response = await self.http.get("/discover/users")

        if not response:
            return []

        return [User(u, self) for u in response]

    async def discover_questions(self) -> List[dict]:
        """
        Get hot/trending questions from the Discover tab

        Returns:
            List of question dicts with keys: uuid, creator (dict or None),
            category (dict with uuid/color), text, createdAt
        """
        response = await self.http.get("/discover/questions")
        return response if response else []

    async def discover_stories(self) -> List[Story]:
        """
        Get popular stories from the Discover tab

        Returns:
            List of Story objects with user context
        """
        response = await self.http.get("/discover/stories")

        if not response:
            return []

        stories = []
        for entry in response:
            user_data = entry.get("user", {})
            for story_data in entry.get("stories", []):
                stories.append(Story(story_data, self, user_data=user_data))

        return stories
