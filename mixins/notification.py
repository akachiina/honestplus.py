"""
Notification methods mixin for Honest+ API client.
"""

import logging
from typing import Optional, AsyncIterator, TYPE_CHECKING

from ..models.notification import Notification, NotificationResume

if TYPE_CHECKING:
    from ..http import HTTPClient

logger = logging.getLogger(__name__)


class NotificationMixin:
    """Notification methods"""

    if TYPE_CHECKING:
        http: "HTTPClient"

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
