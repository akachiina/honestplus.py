"""
Chat methods mixin for Honest+ API client.
"""

import logging
from typing import TYPE_CHECKING

from ..models.chat import Chat

if TYPE_CHECKING:
    from ..http import HTTPClient

logger = logging.getLogger(__name__)


class ChatMixin:
    """Chat methods"""

    if TYPE_CHECKING:
        http: "HTTPClient"

    async def get_chats(self):
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
        chat = Chat({"uuid": chat_uuid}, self)
        return chat
