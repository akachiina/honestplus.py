"""
honestplus.py - Async Python wrapper for Honest+ API

A discord.py-like library for interacting with Honest+ social network.
"""

__version__ = "0.1.0"
__author__ = "honestplus.py contributors"
__license__ = "MIT"

from .client import Client
from .errors import (
    HonestException,
    AuthenticationError,
    NotFoundError,
    RateLimitError,
    APIError,
    ValidationError,
    MediaProcessingError,
)
from .enums import (
    ReactionType,
    NotificationType,
    PostVisibility,
    MediaType,
)
from .models.user import User, Profile
from .models.post import Post, Comment
from .models.notification import Notification
from .models.chat import Chat, Message
from .models.story import Story, Question
from .utils import (
    prepare_image_for_story,
    create_text_story,
    add_text_to_image,
    get_default_font,
)

__all__ = [
    "Client",
    "HonestException",
    "AuthenticationError",
    "NotFoundError",
    "RateLimitError",
    "APIError",
    "ValidationError",
    "MediaProcessingError",
    "ReactionType",
    "NotificationType",
    "PostVisibility",
    "MediaType",
    "User",
    "Profile",
    "Post",
    "Comment",
    "Notification",
    "Chat",
    "Message",
    "Story",
    "Question",
    "prepare_image_for_story",
    "create_text_story",
    "add_text_to_image",
    "get_default_font",
]
