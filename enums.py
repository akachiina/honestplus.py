"""
Enumerations for honestplus.py
"""

from enum import Enum


class ReactionType(str, Enum):
    """Post/comment reaction types"""
    LIKE = "like"
    DISLIKE = "dislike"
    NEUTRAL = "neutral"


class NotificationType(str, Enum):
    """Notification types"""
    FOLLOW = "follow"
    COMMENT = "comment"
    REPLY = "reply"
    MENTION = "mention"
    POST_REACTION = "postReaction"
    POST_COMMENT_REACTION = "postCommentReaction"
    QUESTION = "question"
    ANSWER = "answer"
    CHAT_MESSAGE = "chatMessage"


class PostVisibility(str, Enum):
    """Post visibility settings"""
    PUBLIC = "public"
    PRIVATE = "private"
    FOLLOWERS = "followers"


class MediaType(str, Enum):
    """Media upload types"""
    PROFILE = "profile"
    HEADER = "header"
    CHAT = "chat"
    STORY = "story"
    POST = "post"


class PostType(str, Enum):
    """Post content types"""
    TEXT = "text"
    PHOTO = "photo"
    VIDEO = "video"


class MessageType(str, Enum):
    """Chat message types"""
    TEXT = "text"
    PHOTO = "photo"
    VIDEO = "video"


class Gender(str, Enum):
    """User gender options"""
    MAN = "man"
    WOMAN = "woman"
    OTHER = "other"
