"""
Media methods mixin for Honest+ API client.
"""

import asyncio
import logging
import os
from typing import TYPE_CHECKING

import aiohttp

from ..errors import MediaProcessingError
from ..enums import MediaType
from ..utils import prepare_image_for_story

if TYPE_CHECKING:
    from ..http import HTTPClient

logger = logging.getLogger(__name__)


class MediaMixin:
    """Media upload and processing methods"""

    if TYPE_CHECKING:
        http: "HTTPClient"

    async def upload_photo(
        self,
        file_path: str,
        media_type: str = MediaType.CHAT.value,
        auto_prepare: bool = True,
        background_color: str = "black",
    ) -> str:
        """
        Upload a photo

        Args:
            file_path: Path to the image file
            media_type: Type of media (chat/profile/header/story)
            auto_prepare: Auto-prepare image for story format (only applies to stories)
                         When True, images are automatically adjusted to 1037x1843
                         with letterboxing to fit the entire image
            background_color: Letterboxing color for stories (default: "black")
                             Can be color name or RGB tuple

        Returns:
            Media UUID

        Note:
            For stories (media_type="story"), images are automatically prepared
            to the correct aspect ratio (9:16) unless auto_prepare=False.
            This ensures proper display without cropping.
        """
        # Auto-prepare image for story format if needed
        prepared_file = None
        upload_path = file_path

        if media_type == MediaType.STORY.value and auto_prepare:
            logger.info("Auto-preparing image for story format (1037x1843)...")
            try:
                prepared_file = prepare_image_for_story(
                    file_path,
                    background_color=background_color
                )
                upload_path = prepared_file
                logger.debug(f"Using prepared image: {upload_path}")
            except Exception as e:
                logger.warning(f"Failed to auto-prepare image: {e}. Using original.")
                upload_path = file_path

        try:
            # Create multipart form data
            data = aiohttp.FormData()
            data.add_field("type", media_type)

            # Open file and add to form data
            with open(upload_path, "rb") as f:
                data.add_field(
                    "file",
                    f,
                    filename="file.jpg",
                    content_type="image/jpeg"
                )

                # Send request (aiohttp will set content-type automatically)
                response = await self.http.post(
                    "/media/photo",
                    data=data
                )

            media_uuid = response.get("uuid")
            logger.info(f"Uploaded photo: {media_uuid}")
            return media_uuid

        finally:
            # Clean up temporary prepared file if it was created
            if prepared_file and os.path.exists(prepared_file):
                try:
                    os.remove(prepared_file)
                    logger.debug(f"Cleaned up temporary file: {prepared_file}")
                except Exception as e:
                    logger.warning(f"Failed to clean up temporary file: {e}")

    async def wait_for_media(self, media_uuid: str, timeout: int = 30) -> None:
        """
        Wait for media to finish processing

        Args:
            media_uuid: Media UUID
            timeout: Maximum time to wait in seconds
        """
        start_time = asyncio.get_event_loop().time()

        while True:
            response = await self.http.get(f"/media/{media_uuid}/status")
            status = response.get("status")

            if status == "ready":
                logger.info(f"Media {media_uuid} is ready")
                return
            elif status == "error":
                error = response.get("error", "Unknown error")
                raise MediaProcessingError(f"Media processing failed: {error}")

            # Check timeout
            if asyncio.get_event_loop().time() - start_time > timeout:
                raise MediaProcessingError(f"Media processing timeout after {timeout}s")

            # Wait before checking again
            await asyncio.sleep(1)
