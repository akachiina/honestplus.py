# honestplus.py

<div align="center">
  <b>🌐 Language</b>
  <table>
    <tr>
      <td align="center"><a href="README.md">🇺🇸 English</a></td>
      <td align="center"><a href="README.pt-BR.md">🇧🇷 Português</a></td>
    </tr>
  </table>
</div>

---

> [!CAUTION]
> This project is for **educational purposes only**. The author assumes no responsibility for any misuse, violations of Terms of Service, or damages arising from the use of this library. Use at your own risk.

## Contents

- [About](#about)
- [Installation](#installation)
- [Quick Start](#quick-start)
- [Getting the Token](#jwt-token-recommended)
- [Usage Examples](#usage-examples)
  - [Account Registration](#account-registration)
  - [Creating a Post](#creating-a-post)
  - [Polls](#polls)
  - [Reading the Feed](#reading-the-feed)
  - [Comments](#comments)
  - [Stories](#stories)
  - [Chats and Messages](#chats-and-messages)
  - [Profile](#profile)
  - [Follow / Unfollow](#follow--unfollow)
  - [Search](#search)
  - [Questions](#questions)
  - [Block / Mute](#block--mute)
  - [Reports](#reports)
- [Event System](#event-system)
- [API Reference](#api-reference)
- [Requirements](#requirements)
- [License](#license)
- [Disclaimer](#disclaimer)

## About

An unofficial async Python wrapper for the [Honest+](https://honest.plus) API, inspired by discord.py's design philosophy.

## Features

- **Async/await syntax** — Built on `aiohttp` for efficient async operations
- **Event-driven architecture** — React to real-time events (notifications, messages)
- **Comprehensive API coverage** — Posts, comments, stories, chats, polls, questions, and more
- **Image processing** — Built-in utilities for preparing story images (1037×1843)
- **Text rendering** — Create text stories and overlays with the included Fredoka font
- **Type hints** — Full typing support for better IDE integration

## Installation

```bash
pip install git+https://github.com/akachiina/honestplus.py.git
```

Dependencies (`aiohttp` and `Pillow`) are installed automatically.

## Quick Start

```python
import honestplus
import asyncio

# language selects the content server: "en" (default), "pt" (Brazil), "es" (Spanish), etc.
client = honestplus.Client(token="your_jwt_token", language="pt")

@client.event
async def on_ready():
    print(f"Logged in as {client.user.name} (@{client.user.nick})")

async def main():
    await client.start()

asyncio.run(main())
```

## Usage Examples

### Account Registration

```python
import honestplus
from honestplus import Client, Gender

async with Client() as client:
    # Step 1: Try to login with Google
    result = await client.login_google(
        google_token="google_oauth_jwt_token",
        device_id="device_identifier",
    )

    if result.not_found:
        # Account doesn't exist — API suggested a nick
        print(f"Suggested nick: {result.nick}")

        # Step 2: Check if the nick is available
        available = await client.check_nick("meunick")

        # Step 3: Register the new account
        user = await client.register_google(
            google_token="google_oauth_jwt_token",
            device_id="device_identifier",
            name="My Name",
            nick="meunick",
            gender=Gender.MAN.value,
            birthday="2000-01-15T00:00:00.000",
        )
    else:
        # Account exists — already logged in
        print(f"Welcome back, {result.user.name}!")

    # Step 4: Get available interests and configure profile
    interests = await client.get_interests()
    await client.update_profile(interests=["politics", "music"])

    # Step 5: Discover users with similar interests
    users = await client.discover_users()
    for u in users:
        print(f"{u.name} (@{u.nick})")
```

### Creating a Post

```python
post = await client.create_post(
    text="Hello from honestplus.py!",
    visibility=honestplus.PostVisibility.PUBLIC,
)
```

### Polls

```python
post = await client.create_poll_post(
    text="What's your favorite color?",
    options=["Red", "Blue", "Green"],
    is_anonymous=True,
    allows_multiple=False,
)

# Vote on a poll
await client.vote_poll(post.uuid, [option_uuid])
```

### Reading the Feed

```python
# General feed
async for post in client.get_feed(limit=20):
    print(f"{post.user.name}: {post.text}")
    print(f"  ↑{post.likes} ↓{post.dislikes} 💬{post.comments}")

# Friends-only feed
async for post in client.get_friends_feed(limit=10):
    print(post.text)

# Following feed
async for post in client.get_following_feed(limit=10):
    print(post.text)
```

### Comments

```python
# Add a comment
comment = await post.comment("Nice post!")

# Reply to a comment
reply = await post.comment("I agree!", reply_id=comment.uuid)

# Get all comments
comments = await post.get_comments()
for c in comments:
    print(f"{c.user.name}: {c.text}")

# React to a comment
await comment.like()
await comment.dislike()
await comment.remove_reaction()
```

### Stories

```python
# Upload an image and create a story (auto-prepared to 1037×1843)
media_uuid = await client.upload_photo("photo.jpg", media_type="story")
await client.wait_for_media(media_uuid)
story = await client.create_story(media_uuid)

# Create a text story
text_image = honestplus.create_text_story(
    "Hello world!",
    background_color="#1a1a2e",
    text_color="white",
    font_size=70,
)
media_uuid = await client.upload_photo(text_image, media_type="story")
await client.wait_for_media(media_uuid)
story = await client.create_story(media_uuid)

# Add text overlay to an image
overlay = honestplus.add_text_to_image(
    "photo.jpg",
    "Check this out!",
    text_color="white",
    font_size=80,
)

# View stories from your feed
stories = client.get_story_feed()
for story in stories:
    print(f"{story.user.name} posted a story")
    await story.view()
    await story.like()
```

### Chats and Messages

```python
# List all chats
chats = await client.get_chats()
for chat in chats:
    print(f"Chat with {chat.user.name}: {chat.last_message_text}")

# Open a chat with a user
chat = await client.get_chat_by_user("user_uuid")

# Send messages
await chat.send("Hello!")
await chat.send_photo("photo.jpg")

# Get chat history
messages = await chat.get_history(limit=50)
for msg in messages:
    print(f"{msg.user.name}: {msg.text}")

# Typing indicator
await chat.typing()
```

### Profile

```python
# Get a user's profile
profile = await client.get_profile("username")
print(f"{profile.user.name} — {profile.followers} followers")
print(f"Bio: {profile.description}")
print(f"Following: {profile.following}")

# Update your own profile
await client.update_profile(
    name="New Name",
    description="My new bio",
    photo="photo_uuid",
    header="header_uuid",
    interests=["coding", "music"],
)

# Upload a new profile photo
photo_uuid = await client.upload_photo("selfie.jpg", media_type="profile")
await client.wait_for_media(photo_uuid)
await client.update_profile(photo=photo_uuid)
```

### Follow / Unfollow

```python
await client.follow_user("user_uuid")
await client.unfollow_user("user_uuid")

# Check followers and following
followers = await client.get_followers("user_uuid", page=0)
following = await client.get_following("user_uuid", page=0)
```

### Search

```python
users = await client.search_users("query", limit=10)
for user in users:
    print(f"{user.name} (@{user.nick})")

posts = await client.search_posts("query", limit=10)
for post in posts:
    print(f"{post.user.name}: {post.text}")
```

### Questions

```python
# Send a question
await client.send_question(
    text="What's your favorite food?",
    category="personal",
    anonymous=True,
)

# Receive questions
async for question in client.get_questions_received(limit=10):
    print(f"Q: {question.text} (from {question.user.name})")

# Answer a question
await question.answer("Pizza!")
```

### Block / Mute

```python
await client.block_user("user_uuid")
await client.unblock_user("block_id")

await client.mute_user("user_uuid")
await client.unmute_user("user_uuid")

blocked = await client.get_blocked_users()
```

### Reports

```python
await client.report_post("post_uuid", "Spam")
await client.report_user("user_uuid", "Harassment")
await client.report_comment("post_uuid", "comment_uuid", "Inappropriate")
```

## Event System

```python
@client.event
async def on_ready():
    """Called when the client connects and is ready."""
    print("Bot is ready!")

@client.event
async def on_notification(notification):
    """Called when a new notification is received."""
    print(f"New notification: {notification.type}")

@client.event
async def on_follow(user):
    """Called when someone follows you."""
    print(f"New follower: {user.name}")

@client.event
async def on_comment(notification):
    """Called when someone comments on your post."""
    print(f"New comment from {notification.user.name}")
```

Start polling with `await client.start(poll_interval=15.0)`.

## Authentication

### JWT Token (recommended)

The only practical way to use this wrapper. Pass the token directly when creating the client:

```python
client = honestplus.Client(token="your_jwt_token")
```

To get the token:

1. Set up an Android emulator with root access on your PC
2. Install [HTTP Toolkit](https://httptoolkit.com/) to intercept HTTP traffic
3. Open the Honest+ app in the emulator
4. Capture the requests and copy the `Authorization: Bearer <token>` header value

> [!CAUTION]
> Treat your token as a secret. Do not share it publicly.

### Google / Facebook OAuth (for reference only)

The methods `login_google()`, `register_google()`, and `login_facebook()` exist in the wrapper because the API supports them, but **they cannot be used** from this library. The OAuth flow requires the Google/Facebook client ID configured in the Honest+ Android app, which is tied to the app's signing key and cannot be replicated externally. These methods are kept for API completeness only.

## API Reference

### Client

| Method | Returns | Description |
|---|---|---|
| `login_google(google_token, device_id, name)` | `LoginResult` | Login with Google OAuth (returns `logged` or `notFound`) |
| `register_google(google_token, device_id, name, nick, ...)` | `User` | Register a new account with Google OAuth |
| `login_facebook(facebook_token, device_id, name)` | `User` | Login with Facebook OAuth |
| `check_nick(nick)` | `bool` | Check if a nickname is available |
| `get_interests()` | `dict` | Get available and selected interests |
| `logout()` | `None` | Logout current session |
| `get_profile(nick)` | `Profile` | Get a user's profile |
| `get_user_config()` | `dict` | Get user settings (notifications, privacy, etc.) |
| `update_user_config(...)` | `None` | Update user settings |
| `update_profile(...)` | `None` | Update your profile |
| `create_post(text, visibility, post_type)` | `Post` | Create a new post |
| `get_post(post_uuid)` | `Post` | Get a post by UUID |
| `get_feed(limit)` | `AsyncIterator[Post]` | General feed |
| `get_friends_feed(limit)` | `AsyncIterator[Post]` | Friends-only feed |
| `get_following_feed(limit)` | `AsyncIterator[Post]` | Following feed |
| `search_posts(query, limit)` | `List[Post]` | Search posts |
| `follow_post(post_uuid)` | `None` | Follow a post (get comment notifications) |
| `unfollow_post(post_uuid)` | `None` | Unfollow a post |
| `upload_photo(file_path, media_type)` | `str` | Upload media, returns UUID |
| `add_to_gallery(media_uuid)` | `None` | Add photo to profile gallery |
| `create_story(media_uuid, items)` | `Story` | Create a story |
| `get_story_feed()` | `List[Story]` | Get story feed |
| `get_chats()` | `List[Chat]` | List all chats |
| `get_chat_by_user(user_uuid)` | `Chat` | Open chat with user |
| `get_notification_resume()` | `NotificationResume` | Unread counts |
| `get_notifications(limit)` | `AsyncIterator[Notification]` | All notifications |
| `search_users(query, limit)` | `List[User]` | Search users |
| `send_question(text, category, anonymous)` | `None` | Send a question |
| `delete_profile_data(posts, comments, stories)` | `None` | Delete posts/comments/stories in bulk |
| `delete_account()` | `None` | Permanently delete account |
| `discover_users()` | `List[User]` | User suggestions from Discover |
| `discover_questions()` | `List[dict]` | Hot questions from Discover |
| `discover_stories()` | `List[Story]` | Popular stories from Discover |

### Models

| Model | Key Attributes |
|---|---|
| `User` | `uuid`, `name`, `nick`, `profile_photo`, `profile_photo_url` |
| `Profile` | `user`, `description`, `followers`, `following`, `is_following`, `interests` |
| `Post` | `uuid`, `user`, `text`, `type`, `likes`, `dislikes`, `comments`, `media_url` |
| `Comment` | `uuid`, `user`, `text`, `likes`, `dislikes`, `reply_to_uuid` |
| `Story` | `uuid`, `user`, `items`, `liked`, `media_url` |
| `Chat` | `uuid`, `user`, `last_message`, `unread_count` |
| `Message` | `id`, `user`, `type`, `text`, `media`, `date` |
| `Notification` | `uuid`, `user`, `type`, `action`, `is_read` |
| `Question` | `uuid`, `user`, `text`, `answer`, `is_anonymous`, `is_answered` |

### Enums

| Enum | Values |
|---|---|
| `ReactionType` | `LIKE`, `DISLIKE`, `NEUTRAL` |
| `PostVisibility` | `PUBLIC`, `PRIVATE`, `FOLLOWERS` |
| `MediaType` | `PROFILE`, `HEADER`, `CHAT`, `STORY`, `FOTO` |
| `Gender` | `MAN`, `WOMAN`, `OTHER` |
| `NotificationType` | `FOLLOW`, `COMMENT`, `REPLY`, `MENTION`, `POST_REACTION`, `QUESTION`, `ANSWER`, `CHAT_MESSAGE` |

### Exceptions

| Exception | When |
|---|---|
| `HonestException` | Base exception |
| `AuthenticationError` | Invalid or expired token |
| `NotFoundError` | Resource not found (404) |
| `RateLimitError` | Rate limit exceeded |
| `APIError` | General API error |
| `ValidationError` | Input validation failed |
| `MediaProcessingError` | Media upload/processing failed |

## Requirements

- Python 3.8+
- `aiohttp`
- `Pillow`

## License

MIT License.

## Disclaimer

This library is not officially affiliated with or endorsed by Honest+. It is an independent project created for educational and development purposes.
