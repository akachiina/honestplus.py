"""
HTTP client for Honest+ API with rate limiting and error handling
"""

import asyncio
import logging
from typing import Optional, Dict, Any, Union
from urllib.parse import urljoin

import aiohttp

from .errors import (
    AuthenticationError,
    NotFoundError,
    RateLimitError,
    APIError,
)

logger = logging.getLogger(__name__)


class HTTPClient:
    """
    Async HTTP client for Honest+ API
    
    Handles:
    - Authentication headers
    - Rate limiting
    - Automatic retries
    - Error handling
    """
    
    BASE_URL = "https://api.honest.plus/v1/"
    
    def __init__(
        self,
        token: Optional[str] = None,
        language: str = "en",
        platform: str = "android",
        version: str = "90",
    ):
        self.token = token
        self.language = language
        self.platform = platform
        self.version = version
        self.session: Optional[aiohttp.ClientSession] = None
        self._rate_limit_remaining = None
        self._rate_limit_reset = None
        
    async def __aenter__(self):
        await self.start()
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()
        
    async def start(self):
        """Initialize the HTTP session"""
        if self.session is None or self.session.closed:
            self.session = aiohttp.ClientSession()
            logger.debug("HTTP session started")
            
    async def close(self):
        """Close the HTTP session"""
        if self.session and not self.session.closed:
            await self.session.close()
            logger.debug("HTTP session closed")
            
    def _get_headers(self, additional_headers: Optional[Dict[str, str]] = None) -> Dict[str, str]:
        """Build request headers"""
        headers = {
            "user-agent": "Dart/3.9 (dart:io)",
            "accept-encoding": "gzip",
            "x-lang": self.language,
            "x-platform": self.platform,
            "x-version": self.version,
        }
        
        if self.token:
            headers["authorization"] = f"Bearer {self.token}"
            
        if additional_headers:
            headers.update(additional_headers)
            
        return headers
        
    async def _handle_response(self, response: aiohttp.ClientResponse) -> Union[Dict, list, None]:
        """Handle API response and errors"""
        status = response.status
        
        # Log response
        logger.debug(f"Response {status} from {response.url}")
        
        # Handle rate limiting
        if status == 429:
            retry_after = response.headers.get("Retry-After")
            if retry_after:
                retry_after = float(retry_after)
            else:
                retry_after = 60.0  # Default to 60 seconds
                
            logger.warning(f"Rate limited. Retry after {retry_after}s")
            raise RateLimitError(
                f"Rate limit exceeded. Retry after {retry_after} seconds",
                retry_after=retry_after
            )
            
        # Handle authentication errors
        if status == 401:
            logger.error("Authentication failed")
            raise AuthenticationError("Invalid or expired token")
            
        # Handle not found
        if status == 404:
            logger.error(f"Resource not found: {response.url}")
            raise NotFoundError(f"Resource not found: {response.url}")
            
        # Handle other client errors
        if 400 <= status < 500:
            try:
                error_data = await response.json()
                error_message = error_data.get("error", error_data.get("message", "Unknown error"))
            except:
                error_message = await response.text()
                
            logger.error(f"Client error {status}: {error_message}")
            raise APIError(error_message, status_code=status, response=error_data if 'error_data' in locals() else None)
            
        # Handle server errors
        if status >= 500:
            logger.error(f"Server error {status}")
            raise APIError(f"Server error: {status}", status_code=status)
            
        # Success responses
        if status == 204:  # No content
            return None
            
        if status in (200, 201):
            content_type = response.headers.get("Content-Type", "")
            if "application/json" in content_type:
                return await response.json()
            else:
                return await response.text()
                
        # Handle 304 Not Modified
        if status == 304:
            return None
            
        # Unexpected status code
        logger.warning(f"Unexpected status code: {status}")
        return None
        
    async def request(
        self,
        method: str,
        endpoint: str,
        *,
        json: Optional[Dict[str, Any]] = None,
        data: Optional[Any] = None,
        params: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
        retry: int = 3,
    ) -> Union[Dict, list, None]:
        """
        Make an HTTP request to the API
        
        Args:
            method: HTTP method (GET, POST, PUT, DELETE)
            endpoint: API endpoint (e.g., "/post/feed/general")
            json: JSON body for request
            data: Raw data for request (for multipart)
            params: Query parameters
            headers: Additional headers
            retry: Number of retries for network errors
            
        Returns:
            Response data (dict, list, or None)
        """
        if self.session is None:
            await self.start()
            
        url = urljoin(self.BASE_URL, endpoint.lstrip("/"))
        request_headers = self._get_headers(headers)
        
        logger.debug(f"{method} {url}")
        if json:
            logger.debug(f"Request body: {json}")
            
        for attempt in range(retry):
            try:
                async with self.session.request(
                    method,
                    url,
                    json=json,
                    data=data,
                    params=params,
                    headers=request_headers,
                ) as response:
                    return await self._handle_response(response)
                    
            except RateLimitError:
                # Don't retry rate limit errors, let caller handle it
                raise
                
            except AuthenticationError:
                # Don't retry auth errors
                raise
                
            except aiohttp.ClientError as e:
                if attempt == retry - 1:
                    logger.error(f"Request failed after {retry} attempts: {e}")
                    raise APIError(f"Network error: {e}")
                    
                wait_time = 2 ** attempt  # Exponential backoff
                logger.warning(f"Request failed (attempt {attempt + 1}/{retry}), retrying in {wait_time}s: {e}")
                await asyncio.sleep(wait_time)
                
    async def get(self, endpoint: str, **kwargs) -> Union[Dict, list, None]:
        """Make a GET request"""
        return await self.request("GET", endpoint, **kwargs)
        
    async def post(self, endpoint: str, **kwargs) -> Union[Dict, list, None]:
        """Make a POST request"""
        return await self.request("POST", endpoint, **kwargs)
        
    async def put(self, endpoint: str, **kwargs) -> Union[Dict, list, None]:
        """Make a PUT request"""
        return await self.request("PUT", endpoint, **kwargs)
        
    async def delete(self, endpoint: str, **kwargs) -> Union[Dict, list, None]:
        """Make a DELETE request"""
        return await self.request("DELETE", endpoint, **kwargs)
