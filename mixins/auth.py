"""
Authentication mixin for Honest+ API client.
"""

import json
import base64
import logging
from typing import Optional, TYPE_CHECKING

from ..errors import ValidationError
from ..enums import Gender
from ..models.user import User

if TYPE_CHECKING:
    from ..http import HTTPClient

logger = logging.getLogger(__name__)


class LoginResult:
    """
    Result from a login attempt via Google OAuth.

    Attributes:
        type: "logged" if the account exists and login succeeded,
              "notFound" if the account doesn't exist yet (needs registration)
        name: Display name from Google (only present when type="notFound")
        nick: Suggested nickname (only present when type="notFound")
        token: JWT token (only present when type="logged")
        user: User object (only present when type="logged")
    """

    def __init__(
        self,
        type: str,
        name: Optional[str] = None,
        nick: Optional[str] = None,
        token: Optional[str] = None,
        user: Optional["User"] = None,
    ):
        self.type = type
        self.name = name
        self.nick = nick
        self.token = token
        self.user = user

    @property
    def logged(self) -> bool:
        """True if login was successful (account exists)"""
        return self.type == "logged"

    @property
    def not_found(self) -> bool:
        """True if account doesn't exist yet (needs registration)"""
        return self.type == "notFound"

    def __repr__(self):
        if self.logged:
            return f"<LoginResult logged user={self.user}>"
        return f"<LoginResult notFound name={self.name} nick={self.nick}>"


class AuthMixin:
    """Authentication methods for Honest+ API"""

    if TYPE_CHECKING:
        http: "HTTPClient"
        user: Optional[User]

    async def login_google(self, google_token: str, device_id: str, name: Optional[str] = None) -> LoginResult:
        """
        Login with Google OAuth token

        Args:
            google_token: Google OAuth JWT token
            device_id: Device identifier (e.g., "TQ3A.230901.001")
            name: Optional display name

        Returns:
            LoginResult with type="logged" (account exists) or
            type="notFound" (account doesn't exist, use register_google)
        """
        response = await self.http.post(
            "/auth/login/google",
            json={
                "id": device_id,
                "name": name,
                "token": google_token,
            }
        )

        if not response:
            raise ValidationError("Login failed: Empty response from server")

        login_type = response.get("type")

        if login_type == "logged":
            # Account exists — extract token and user
            self.http.token = response.get("token")
            user_data = response.get("user", {})
            self.user = User(user_data, self)
            logger.info(f"Logged in as {self.user.name} (@{self.user.nick})")
            return LoginResult(
                type="logged",
                token=self.http.token,
                user=self.user,
            )

        if login_type == "notFound":
            # Account doesn't exist — return suggested name/nick for registration
            logger.info(f"Account not found. Suggested nick: {response.get('nick')}")
            return LoginResult(
                type="notFound",
                name=response.get("name"),
                nick=response.get("nick"),
            )

        raise ValidationError(f"Login failed: Unexpected response type '{login_type}'")

    async def register_google(
        self,
        google_token: str,
        device_id: str,
        name: str,
        nick: str,
        push: Optional[str] = None,
        show_age: bool = True,
        model: Optional[str] = None,
        device: bool = True,
        gender: str = Gender.OTHER.value,
        birthday: Optional[str] = None,
    ) -> User:
        """
        Register a new account with Google OAuth

        Args:
            google_token: Google OAuth JWT token
            device_id: Device identifier
            name: Display name for the new account
            nick: Username/nickname for the new account
            push: Push notification UUID (from OneSignal)
            show_age: Whether to show age on profile (default: True)
            model: Device model string (e.g., "Pixel 7")
            device: Whether this is a device (default: True)
            gender: User gender — "man", "woman", or "other" (default: "other")
            birthday: ISO 8601 birthday string (e.g., "2000-01-15T00:00:00.000")

        Returns:
            User object for the newly created account
        """
        response = await self.http.post(
            "/auth/register/google",
            json={
                "id": device_id,
                "token": google_token,
                "push": push,
                "name": name,
                "nick": nick,
                "showAge": show_age,
                "model": model,
                "device": device,
                "gender": gender,
                "birthday": birthday,
            }
        )

        if not response:
            raise ValidationError("Registration failed: Empty response from server")

        # The register endpoint returns the same structure as login
        login_type = response.get("type")

        if login_type == "logged":
            self.http.token = response.get("token")
            user_data = response.get("user", {})
            self.user = User(user_data, self)
            logger.info(f"Registered and logged in as {self.user.name} (@{self.user.nick})")
            return self.user

        # Some implementations return user data directly
        if "uuid" in response:
            self.user = User(response, self)
            logger.info(f"Registered: {self.user.name} (@{self.user.nick})")
            return self.user

        raise ValidationError(f"Registration failed: Unexpected response: {response}")

    async def login_facebook(self, facebook_token: str, device_id: str, name: Optional[str] = None) -> User:
        """
        Login with Facebook OAuth token

        Args:
            facebook_token: Facebook OAuth token
            device_id: Device identifier
            name: Optional display name

        Returns:
            User object for the authenticated user
        """
        response = await self.http.post(
            "/auth/login/facebook",
            json={
                "id": device_id,
                "name": name,
                "token": facebook_token,
            }
        )

        if not response or response.get("type") != "logged":
            raise ValidationError("Login failed: Invalid response from server")

        # Update token
        self.http.token = response.get("token")

        # Create user object
        user_data = response.get("user", {})
        self.user = User(user_data, self)

        logger.info(f"Logged in as {self.user.name} (@{self.user.nick})")
        return self.user

    async def logout(self) -> None:
        """Logout from the current session"""
        await self.http.post("/auth/logout")
        self.http.token = None
        self.user = None
        logger.info("Logged out")

    async def fetch_current_user(self) -> User:
        """
        Fetch the current authenticated user's information

        Returns:
            User object
        """
        if not self.http.token:
            raise ValidationError("Not authenticated. Please login first.")

        try:
            # JWT format: header.payload.signature
            payload = self.http.token.split('.')[1]
            # Add padding if needed
            payload += '=' * (4 - len(payload) % 4)
            decoded = json.loads(base64.b64decode(payload))

            nick = decoded.get("nick")
            if nick:
                profile = await self.get_profile(nick)
                self.user = profile.user
                return self.user
        except Exception as e:
            logger.error(f"Failed to decode token: {e}")

        raise ValidationError("Could not fetch current user")

    async def check_nick(self, nick: str) -> bool:
        """
        Check if a nickname is available for registration

        Args:
            nick: Nickname to check

        Returns:
            True if the nick is available, False if taken
        """
        response = await self.http.get(f"/auth/nick/{nick}/check")
        return response.get("isAvailable", False) if response else False

    async def get_interests(self) -> dict:
        """
        Get available interests and currently selected interests

        Returns:
            Dict with "all" (list of available interest strings) and
            "selected" (list of the user's currently selected interests)
        """
        return await self.http.get("/interests")

    async def discover_users(self):
        """
        Discover users with similar interests

        Returns:
            List of User objects
        """
        response = await self.http.get("/discover/users")

        if not response:
            return []

        return [User(u, self) for u in response]
