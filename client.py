"""
Main client for honestplus.py
"""

import asyncio
import logging
from datetime import datetime
from typing import Optional, List, Callable, Dict

from .http import HTTPClient
from .models.user import User

# Mixins
from .mixins.auth import AuthMixin, LoginResult  # noqa: F401 — backward compat
from .mixins.user import UserMixin
from .mixins.post import PostMixin
from .mixins.story import StoryMixin
from .mixins.chat import ChatMixin
from .mixins.notification import NotificationMixin
from .mixins.media import MediaMixin
from .mixins.question import QuestionMixin
from .mixins.discover import DiscoverMixin

logger = logging.getLogger(__name__)


class Client(
    AuthMixin,
    UserMixin,
    PostMixin,
    StoryMixin,
    ChatMixin,
    NotificationMixin,
    MediaMixin,
    QuestionMixin,
    DiscoverMixin,
):
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
            language: Language / server selector (default: "en").
                     Determines which content server the user sees:
                     "en" = English server, "pt" = Brazilian server,
                     "es" = Spanish-language server, etc.
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
