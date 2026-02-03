"""
X (Twitter) Tool

Read-only access to X (Twitter) data using the official API v2.

Requires:
    pip install strands-pack[x]  (just needs requests)

Authentication:
    Set X_BEARER_TOKEN environment variable with your Bearer Token.

Supported actions
-----------------
- get_user
    Parameters: username (required)
- get_user_by_id
    Parameters: user_id (required)
- get_user_tweets
    Parameters: user_id (required), max_results (optional, default 10), exclude (optional)
- get_tweet
    Parameters: tweet_id (required), expansions (optional)
- search_recent
    Parameters: query (required), max_results (optional, default 10),
                start_time (optional), end_time (optional)
- get_user_mentions
    Parameters: user_id (required), max_results (optional, default 10)
- get_user_followers
    Parameters: user_id (required), max_results (optional, default 100)
- get_user_following
    Parameters: user_id (required), max_results (optional, default 100)
- get_liking_users
    Parameters: tweet_id (required), max_results (optional, default 100)
- get_retweeters
    Parameters: tweet_id (required), max_results (optional, default 100)

Notes:
  - This is a READ-ONLY tool. Posting requires a paid API plan ($100/month).
  - Times should be in ISO 8601 format (e.g., "2023-01-01T00:00:00Z")
  - The free tier has rate limits: ~1,500 tweet reads/month
"""

from __future__ import annotations

import os
from typing import Any, Dict, List, Optional

from strands import tool

# Lazy import for requests
_requests = None


def _get_requests():
    global _requests
    if _requests is None:
        try:
            import requests
            _requests = requests
        except ImportError:
            raise ImportError("requests not installed. Run: pip install strands-pack[x]") from None
    return _requests


def _get_token():
    token = os.environ.get("X_BEARER_TOKEN")
    if not token:
        raise ValueError("X_BEARER_TOKEN environment variable is not set")
    return token


def _get_headers():
    return {
        "Authorization": f"Bearer {_get_token()}",
        "Content-Type": "application/json",
    }


BASE_URL = "https://api.twitter.com/2"

# Standard fields to request
USER_FIELDS = "created_at,description,location,profile_image_url,public_metrics,url,verified"
TWEET_FIELDS = "author_id,created_at,conversation_id,public_metrics,possibly_sensitive,lang,source,reply_settings"


def _ok(**data: Any) -> Dict[str, Any]:
    out: Dict[str, Any] = {"success": True}
    out.update(data)
    return out


def _err(message: str, *, error_type: Optional[str] = None, **data: Any) -> Dict[str, Any]:
    out: Dict[str, Any] = {"success": False, "error": message}
    if error_type:
        out["error_type"] = error_type
    out.update(data)
    return out


def _handle_response(response) -> Dict[str, Any]:
    """Handle API response and extract data or error."""
    if response.status_code == 401:
        return None, "Invalid or expired bearer token"
    if response.status_code == 403:
        return None, "Access forbidden - check API permissions"
    if response.status_code == 429:
        return None, "Rate limit exceeded"

    try:
        data = response.json()
    except Exception:
        return None, f"Failed to parse response: {response.text[:200]}"

    if "errors" in data:
        errors = data["errors"]
        if errors:
            return None, errors[0].get("detail", errors[0].get("message", str(errors[0])))

    return data, None


def _extract_user(user_data: Dict) -> Dict[str, Any]:
    """Extract user info from API response."""
    return {
        "id": user_data.get("id"),
        "username": user_data.get("username"),
        "name": user_data.get("name"),
        "description": user_data.get("description"),
        "location": user_data.get("location"),
        "url": user_data.get("url"),
        "profile_image_url": user_data.get("profile_image_url"),
        "verified": user_data.get("verified"),
        "created_at": user_data.get("created_at"),
        "public_metrics": user_data.get("public_metrics"),
    }


def _extract_tweet(tweet_data: Dict) -> Dict[str, Any]:
    """Extract tweet info from API response."""
    return {
        "id": tweet_data.get("id"),
        "text": tweet_data.get("text"),
        "author_id": tweet_data.get("author_id"),
        "created_at": tweet_data.get("created_at"),
        "conversation_id": tweet_data.get("conversation_id"),
        "public_metrics": tweet_data.get("public_metrics"),
        "possibly_sensitive": tweet_data.get("possibly_sensitive"),
        "lang": tweet_data.get("lang"),
        "source": tweet_data.get("source"),
        "reply_settings": tweet_data.get("reply_settings"),
    }


def _get_user(username: str, **kwargs) -> Dict[str, Any]:
    """Get user by username."""
    if not username:
        return _err("username is required")

    # Remove @ if present
    username = username.lstrip("@")

    requests = _get_requests()

    response = requests.get(
        f"{BASE_URL}/users/by/username/{username}",
        headers=_get_headers(),
        params={"user.fields": USER_FIELDS},
        timeout=30,
    )

    data, error = _handle_response(response)
    if error:
        return _err(error, error_type="APIError")

    if not data or "data" not in data:
        return _err(f"User not found: @{username}", error_type="NotFound")

    return _ok(
        action="get_user",
        user=_extract_user(data["data"]),
    )


def _get_user_by_id(user_id: str, **kwargs) -> Dict[str, Any]:
    """Get user by ID."""
    if not user_id:
        return _err("user_id is required")

    requests = _get_requests()

    response = requests.get(
        f"{BASE_URL}/users/{user_id}",
        headers=_get_headers(),
        params={"user.fields": USER_FIELDS},
        timeout=30,
    )

    data, error = _handle_response(response)
    if error:
        return _err(error, error_type="APIError")

    if not data or "data" not in data:
        return _err(f"User not found: {user_id}", error_type="NotFound")

    return _ok(
        action="get_user_by_id",
        user=_extract_user(data["data"]),
    )


def _get_user_tweets(user_id: str, max_results: int = 10, exclude: Optional[List[str]] = None,
                     **kwargs) -> Dict[str, Any]:
    """Get tweets by a user."""
    if not user_id:
        return _err("user_id is required")

    requests = _get_requests()

    max_results = min(max(int(max_results), 5), 100)  # API limits: 5-100

    params = {
        "max_results": max_results,
        "tweet.fields": TWEET_FIELDS,
    }
    if exclude:
        params["exclude"] = ",".join(exclude) if isinstance(exclude, list) else exclude

    response = requests.get(
        f"{BASE_URL}/users/{user_id}/tweets",
        headers=_get_headers(),
        params=params,
        timeout=30,
    )

    data, error = _handle_response(response)
    if error:
        return _err(error, error_type="APIError")

    tweets = []
    if data and "data" in data:
        tweets = [_extract_tweet(t) for t in data["data"]]

    return _ok(
        action="get_user_tweets",
        user_id=user_id,
        tweets=tweets,
        count=len(tweets),
    )


def _get_tweet(tweet_id: str, expansions: Optional[List[str]] = None, **kwargs) -> Dict[str, Any]:
    """Get a single tweet by ID."""
    if not tweet_id:
        return _err("tweet_id is required")

    requests = _get_requests()

    params = {"tweet.fields": TWEET_FIELDS}
    if expansions:
        params["expansions"] = ",".join(expansions) if isinstance(expansions, list) else expansions

    response = requests.get(
        f"{BASE_URL}/tweets/{tweet_id}",
        headers=_get_headers(),
        params=params,
        timeout=30,
    )

    data, error = _handle_response(response)
    if error:
        return _err(error, error_type="APIError")

    if not data or "data" not in data:
        return _err(f"Tweet not found: {tweet_id}", error_type="NotFound")

    return _ok(
        action="get_tweet",
        tweet=_extract_tweet(data["data"]),
    )


def _search_recent(query: str, max_results: int = 10, start_time: Optional[str] = None,
                   end_time: Optional[str] = None, **kwargs) -> Dict[str, Any]:
    """Search recent tweets (last 7 days)."""
    if not query:
        return _err("query is required")

    requests = _get_requests()

    max_results = min(max(int(max_results), 10), 100)  # API limits: 10-100

    params = {
        "query": query,
        "max_results": max_results,
        "tweet.fields": TWEET_FIELDS,
    }
    if start_time:
        params["start_time"] = start_time
    if end_time:
        params["end_time"] = end_time

    response = requests.get(
        f"{BASE_URL}/tweets/search/recent",
        headers=_get_headers(),
        params=params,
        timeout=30,
    )

    data, error = _handle_response(response)
    if error:
        return _err(error, error_type="APIError")

    tweets = []
    if data and "data" in data:
        tweets = [_extract_tweet(t) for t in data["data"]]

    return _ok(
        action="search_recent",
        query=query,
        tweets=tweets,
        count=len(tweets),
    )


def _get_user_mentions(user_id: str, max_results: int = 10, **kwargs) -> Dict[str, Any]:
    """Get tweets mentioning a user."""
    if not user_id:
        return _err("user_id is required")

    requests = _get_requests()

    max_results = min(max(int(max_results), 5), 100)  # API limits: 5-100

    response = requests.get(
        f"{BASE_URL}/users/{user_id}/mentions",
        headers=_get_headers(),
        params={
            "max_results": max_results,
            "tweet.fields": TWEET_FIELDS,
        },
        timeout=30,
    )

    data, error = _handle_response(response)
    if error:
        return _err(error, error_type="APIError")

    tweets = []
    if data and "data" in data:
        tweets = [_extract_tweet(t) for t in data["data"]]

    return _ok(
        action="get_user_mentions",
        user_id=user_id,
        tweets=tweets,
        count=len(tweets),
    )


def _get_user_followers(user_id: str, max_results: int = 100, **kwargs) -> Dict[str, Any]:
    """Get followers of a user."""
    if not user_id:
        return _err("user_id is required")

    requests = _get_requests()

    max_results = min(max(int(max_results), 1), 1000)

    response = requests.get(
        f"{BASE_URL}/users/{user_id}/followers",
        headers=_get_headers(),
        params={
            "max_results": max_results,
            "user.fields": USER_FIELDS,
        },
        timeout=30,
    )

    data, error = _handle_response(response)
    if error:
        return _err(error, error_type="APIError")

    users = []
    if data and "data" in data:
        users = [_extract_user(u) for u in data["data"]]

    return _ok(
        action="get_user_followers",
        user_id=user_id,
        followers=users,
        count=len(users),
    )


def _get_user_following(user_id: str, max_results: int = 100, **kwargs) -> Dict[str, Any]:
    """Get users that a user is following."""
    if not user_id:
        return _err("user_id is required")

    requests = _get_requests()

    max_results = min(max(int(max_results), 1), 1000)

    response = requests.get(
        f"{BASE_URL}/users/{user_id}/following",
        headers=_get_headers(),
        params={
            "max_results": max_results,
            "user.fields": USER_FIELDS,
        },
        timeout=30,
    )

    data, error = _handle_response(response)
    if error:
        return _err(error, error_type="APIError")

    users = []
    if data and "data" in data:
        users = [_extract_user(u) for u in data["data"]]

    return _ok(
        action="get_user_following",
        user_id=user_id,
        following=users,
        count=len(users),
    )


def _get_liking_users(tweet_id: str, max_results: int = 100, **kwargs) -> Dict[str, Any]:
    """Get users who liked a tweet."""
    if not tweet_id:
        return _err("tweet_id is required")

    requests = _get_requests()

    max_results = min(max(int(max_results), 1), 100)

    response = requests.get(
        f"{BASE_URL}/tweets/{tweet_id}/liking_users",
        headers=_get_headers(),
        params={
            "max_results": max_results,
            "user.fields": USER_FIELDS,
        },
        timeout=30,
    )

    data, error = _handle_response(response)
    if error:
        return _err(error, error_type="APIError")

    users = []
    if data and "data" in data:
        users = [_extract_user(u) for u in data["data"]]

    return _ok(
        action="get_liking_users",
        tweet_id=tweet_id,
        users=users,
        count=len(users),
    )


def _get_retweeters(tweet_id: str, max_results: int = 100, **kwargs) -> Dict[str, Any]:
    """Get users who retweeted a tweet."""
    if not tweet_id:
        return _err("tweet_id is required")

    requests = _get_requests()

    max_results = min(max(int(max_results), 1), 100)

    response = requests.get(
        f"{BASE_URL}/tweets/{tweet_id}/retweeted_by",
        headers=_get_headers(),
        params={
            "max_results": max_results,
            "user.fields": USER_FIELDS,
        },
        timeout=30,
    )

    data, error = _handle_response(response)
    if error:
        return _err(error, error_type="APIError")

    users = []
    if data and "data" in data:
        users = [_extract_user(u) for u in data["data"]]

    return _ok(
        action="get_retweeters",
        tweet_id=tweet_id,
        users=users,
        count=len(users),
    )


_ACTIONS = {
    "get_user": _get_user,
    "get_user_by_id": _get_user_by_id,
    "get_user_tweets": _get_user_tweets,
    "get_tweet": _get_tweet,
    "search_recent": _search_recent,
    "get_user_mentions": _get_user_mentions,
    "get_user_followers": _get_user_followers,
    "get_user_following": _get_user_following,
    "get_liking_users": _get_liking_users,
    "get_retweeters": _get_retweeters,
}


@tool
def x(
    action: str,
    username: Optional[str] = None,
    user_id: Optional[str] = None,
    tweet_id: Optional[str] = None,
    query: Optional[str] = None,
    max_results: Optional[int] = None,
    exclude: Optional[List[str]] = None,
    expansions: Optional[List[str]] = None,
    start_time: Optional[str] = None,
    end_time: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Read-only access to X (Twitter) data using the official API v2.

    Actions:
    - get_user: Get user by username
    - get_user_by_id: Get user by ID
    - get_user_tweets: Get tweets by a user
    - get_tweet: Get a single tweet by ID
    - search_recent: Search recent tweets (last 7 days)
    - get_user_mentions: Get tweets mentioning a user
    - get_user_followers: Get followers of a user
    - get_user_following: Get users that a user is following
    - get_liking_users: Get users who liked a tweet
    - get_retweeters: Get users who retweeted a tweet

    Args:
        action: The action to perform
        username: Twitter username (for get_user). The @ symbol is optional.
        user_id: Twitter user ID (for get_user_by_id, get_user_tweets, get_user_mentions,
                 get_user_followers, get_user_following)
        tweet_id: Tweet ID (for get_tweet, get_liking_users, get_retweeters)
        query: Search query string (for search_recent)
        max_results: Maximum number of results to return. Defaults vary by action:
                     - get_user_tweets: 10 (range: 5-100)
                     - search_recent: 10 (range: 10-100)
                     - get_user_mentions: 10 (range: 5-100)
                     - get_user_followers/following: 100 (range: 1-1000)
                     - get_liking_users/retweeters: 100 (range: 1-100)
        exclude: List of tweet types to exclude (for get_user_tweets).
                 Options: "retweets", "replies"
        expansions: List of expansions to include (for get_tweet).
                    Example: ["author_id", "referenced_tweets.id"]
        start_time: Start time for search in ISO 8601 format (for search_recent).
                    Example: "2023-01-01T00:00:00Z"
        end_time: End time for search in ISO 8601 format (for search_recent).
                  Example: "2023-01-15T00:00:00Z"

    Returns:
        dict with success status and action-specific data

    Note:
        This is a READ-ONLY tool. Posting requires a paid API plan ($100/month).

    Authentication:
        Set X_BEARER_TOKEN environment variable with your Bearer Token.
    """
    action = (action or "").strip().lower()

    if action not in _ACTIONS:
        return _err(
            f"Unknown action: {action}",
            error_type="InvalidAction",
            available_actions=list(_ACTIONS.keys()),
        )

    # Build kwargs dict from explicit parameters
    kwargs: Dict[str, Any] = {}
    if username is not None:
        kwargs["username"] = username
    if user_id is not None:
        kwargs["user_id"] = user_id
    if tweet_id is not None:
        kwargs["tweet_id"] = tweet_id
    if query is not None:
        kwargs["query"] = query
    if max_results is not None:
        kwargs["max_results"] = max_results
    if exclude is not None:
        kwargs["exclude"] = exclude
    if expansions is not None:
        kwargs["expansions"] = expansions
    if start_time is not None:
        kwargs["start_time"] = start_time
    if end_time is not None:
        kwargs["end_time"] = end_time

    try:
        return _ACTIONS[action](**kwargs)
    except ImportError as e:
        return _err(str(e), error_type="ImportError")
    except ValueError as e:
        return _err(str(e), error_type="ValueError")
    except Exception as e:
        return _err(str(e), error_type=type(e).__name__, action=action)
