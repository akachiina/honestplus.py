"""
Question methods mixin for Honest+ API client.
"""

import logging
from typing import Optional, List, AsyncIterator, TYPE_CHECKING

from ..errors import ValidationError
from ..models.story import Question

if TYPE_CHECKING:
    from ..http import HTTPClient

logger = logging.getLogger(__name__)


class QuestionMixin:
    """Question (ask) methods"""

    if TYPE_CHECKING:
        http: "HTTPClient"

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
        await self.http.delete(f"/ask/{question_uuid}")

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
