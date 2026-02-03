"""
LinkedIn Tool

Access LinkedIn profile and posting (official API with restrictions).

Requires:
    pip install strands-pack[linkedin]

Authentication:
    Set LINKEDIN_ACCESS_TOKEN environment variable with your OAuth 2.0 access token.

Supported actions
-----------------
- get_profile
    Parameters: none - Gets the authenticated user's profile
- get_connections
    Parameters: count (optional, default 10), start (optional, default 0)
    Note: Requires r_1st_connections_size permission (limited access)
- create_post
    Parameters: text (required), visibility (optional: "PUBLIC" or "CONNECTIONS"), media_url (optional)
- get_posts
    Parameters: count (optional, default 10), start (optional, default 0)
- get_company
    Parameters: company_id (required)
- share_url
    Parameters: url (required), comment (optional), visibility (optional)
- get_analytics
    Parameters: time_range (optional)
    Note: Requires additional permissions
- delete_post
    Parameters: post_id (required)

Notes:
  - LinkedIn's official API has significant restrictions
  - Most features require an approved LinkedIn Developer App
  - Some features (like connections list) require special partnership
  - Rate limits are strict: typically 100 requests/day for basic apps
"""

from __future__ import annotations

import os
from typing import Any, Dict, Optional

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
            raise ImportError("requests not installed. Run: pip install strands-pack[linkedin]") from None
    return _requests


def _get_token():
    token = os.environ.get("LINKEDIN_ACCESS_TOKEN")
    if not token:
        raise ValueError("LINKEDIN_ACCESS_TOKEN environment variable is not set")
    return token


def _get_headers():
    return {
        "Authorization": f"Bearer {_get_token()}",
        "Content-Type": "application/json",
        "X-Restli-Protocol-Version": "2.0.0",
        "LinkedIn-Version": "202401",
    }


BASE_URL = "https://api.linkedin.com/v2"
REST_URL = "https://api.linkedin.com/rest"


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


def _get_profile(**kwargs) -> Dict[str, Any]:
    """Get the authenticated user's profile."""
    requests = _get_requests()

    # Use userinfo endpoint for basic profile
    response = requests.get(f"{BASE_URL}/userinfo", headers=_get_headers(), timeout=30)

    if response.status_code == 401:
        return _err("Invalid or expired access token", error_type="AuthenticationError")

    response.raise_for_status()
    data = response.json()

    # Also try to get the full profile
    profile_data = {}
    try:
        profile_response = requests.get(f"{BASE_URL}/me", headers=_get_headers(), timeout=30)
        if profile_response.status_code == 200:
            profile_data = profile_response.json()
    except Exception:
        pass

    return _ok(
        action="get_profile",
        profile={
            "id": data.get("sub"),
            "name": data.get("name"),
            "given_name": data.get("given_name"),
            "family_name": data.get("family_name"),
            "email": data.get("email"),
            "email_verified": data.get("email_verified"),
            "picture": data.get("picture"),
            "locale": data.get("locale"),
            # From /me endpoint if available
            "vanity_name": profile_data.get("vanityName"),
            "headline": profile_data.get("localizedHeadline"),
        },
    )


def _get_connections(count: int = 10, start: int = 0, **kwargs) -> Dict[str, Any]:
    """Get user's connections count (limited API access)."""
    requests = _get_requests()

    # Note: Full connections list requires special partnership
    # This endpoint returns connection count only
    try:
        response = requests.get(
            f"{BASE_URL}/connections",
            headers=_get_headers(),
            params={"start": start, "count": min(count, 50)},
            timeout=30,
        )

        if response.status_code == 403:
            return _err(
                "Access denied: Connections API requires special LinkedIn partnership",
                error_type="PermissionError",
                note="Most LinkedIn apps don't have access to the connections API",
            )

        response.raise_for_status()
        data = response.json()

        return _ok(
            action="get_connections",
            connections=data.get("elements", []),
            total=data.get("paging", {}).get("total"),
        )
    except Exception as e:
        return _err(
            f"Connections API access restricted: {str(e)}",
            error_type="APIError",
            note="LinkedIn restricts connections API to approved partners",
        )


def _create_post(text: str, visibility: str = "PUBLIC", media_url: Optional[str] = None,
                 **kwargs) -> Dict[str, Any]:
    """Create a post on LinkedIn."""
    if not text:
        return _err("text is required")

    requests = _get_requests()

    # First get user ID
    profile_response = _get_profile()
    if not profile_response.get("success"):
        return profile_response

    user_id = profile_response["profile"]["id"]

    visibility_code = "PUBLIC" if visibility.upper() == "PUBLIC" else "CONNECTIONS"

    # Build post body
    post_body = {
        "author": f"urn:li:person:{user_id}",
        "lifecycleState": "PUBLISHED",
        "visibility": {
            "com.linkedin.ugc.MemberNetworkVisibility": visibility_code,
        },
        "specificContent": {
            "com.linkedin.ugc.ShareContent": {
                "shareCommentary": {
                    "text": text,
                },
                "shareMediaCategory": "NONE" if not media_url else "ARTICLE",
            },
        },
    }

    if media_url:
        post_body["specificContent"]["com.linkedin.ugc.ShareContent"]["media"] = [{
            "status": "READY",
            "originalUrl": media_url,
        }]
        post_body["specificContent"]["com.linkedin.ugc.ShareContent"]["shareMediaCategory"] = "ARTICLE"

    response = requests.post(
        f"{BASE_URL}/ugcPosts",
        headers=_get_headers(),
        json=post_body,
        timeout=30,
    )

    if response.status_code == 403:
        return _err(
            "Access denied: Posting requires w_member_social permission",
            error_type="PermissionError",
        )

    response.raise_for_status()

    # Get post ID from header
    post_id = response.headers.get("X-RestLi-Id", response.headers.get("x-restli-id"))

    return _ok(
        action="create_post",
        post_id=post_id,
        visibility=visibility_code,
        text_length=len(text),
    )


def _get_posts(count: int = 10, start: int = 0, **kwargs) -> Dict[str, Any]:
    """Get user's posts."""
    requests = _get_requests()

    # Get user ID
    profile_response = _get_profile()
    if not profile_response.get("success"):
        return profile_response

    user_id = profile_response["profile"]["id"]

    response = requests.get(
        f"{BASE_URL}/ugcPosts",
        headers=_get_headers(),
        params={
            "q": "authors",
            "authors": f"List(urn:li:person:{user_id})",
            "start": start,
            "count": min(count, 50),
        },
        timeout=30,
    )

    if response.status_code == 403:
        return _err(
            "Access denied: Reading posts requires r_member_social permission",
            error_type="PermissionError",
        )

    response.raise_for_status()
    data = response.json()

    posts = []
    for post in data.get("elements", []):
        posts.append({
            "id": post.get("id"),
            "created_time": post.get("created", {}).get("time"),
            "visibility": post.get("visibility"),
            "text": post.get("specificContent", {}).get("com.linkedin.ugc.ShareContent", {}).get(
                "shareCommentary", {}
            ).get("text"),
        })

    return _ok(
        action="get_posts",
        posts=posts,
        count=len(posts),
    )


def _get_company(company_id: str, **kwargs) -> Dict[str, Any]:
    """Get company information."""
    if not company_id:
        return _err("company_id is required")

    requests = _get_requests()

    response = requests.get(
        f"{BASE_URL}/organizations/{company_id}",
        headers=_get_headers(),
        timeout=30,
    )

    if response.status_code == 403:
        return _err(
            "Access denied: Company API requires rw_organization_admin permission",
            error_type="PermissionError",
        )

    if response.status_code == 404:
        return _err(f"Company not found: {company_id}", error_type="NotFound")

    response.raise_for_status()
    data = response.json()

    return _ok(
        action="get_company",
        company={
            "id": data.get("id"),
            "name": data.get("localizedName"),
            "vanity_name": data.get("vanityName"),
            "description": data.get("localizedDescription"),
            "website": data.get("localizedWebsite"),
            "logo_url": data.get("logoV2", {}).get("original"),
            "industry": data.get("localizedIndustry"),
            "company_type": data.get("companyType"),
            "staff_count_range": data.get("staffCountRange"),
        },
    )


def _share_url(url: str, comment: Optional[str] = None, visibility: str = "PUBLIC",
               **kwargs) -> Dict[str, Any]:
    """Share a URL on LinkedIn."""
    if not url:
        return _err("url is required")

    requests = _get_requests()

    # Get user ID
    profile_response = _get_profile()
    if not profile_response.get("success"):
        return profile_response

    user_id = profile_response["profile"]["id"]

    visibility_code = "PUBLIC" if visibility.upper() == "PUBLIC" else "CONNECTIONS"

    post_body = {
        "author": f"urn:li:person:{user_id}",
        "lifecycleState": "PUBLISHED",
        "visibility": {
            "com.linkedin.ugc.MemberNetworkVisibility": visibility_code,
        },
        "specificContent": {
            "com.linkedin.ugc.ShareContent": {
                "shareCommentary": {
                    "text": comment or "",
                },
                "shareMediaCategory": "ARTICLE",
                "media": [{
                    "status": "READY",
                    "originalUrl": url,
                }],
            },
        },
    }

    response = requests.post(
        f"{BASE_URL}/ugcPosts",
        headers=_get_headers(),
        json=post_body,
        timeout=30,
    )

    if response.status_code == 403:
        return _err(
            "Access denied: Sharing requires w_member_social permission",
            error_type="PermissionError",
        )

    response.raise_for_status()

    post_id = response.headers.get("X-RestLi-Id", response.headers.get("x-restli-id"))

    return _ok(
        action="share_url",
        post_id=post_id,
        url=url,
        visibility=visibility_code,
    )


def _get_analytics(time_range: Optional[str] = None, **kwargs) -> Dict[str, Any]:
    """Get analytics for user's content."""
    requests = _get_requests()

    # Get user ID
    profile_response = _get_profile()
    if not profile_response.get("success"):
        return profile_response

    user_id = profile_response["profile"]["id"]

    # Note: Analytics API requires additional permissions
    try:
        response = requests.get(
            f"{BASE_URL}/organizationalEntityShareStatistics",
            headers=_get_headers(),
            params={
                "q": "organizationalEntity",
                "organizationalEntity": f"urn:li:person:{user_id}",
            },
            timeout=30,
        )

        if response.status_code == 403:
            return _err(
                "Access denied: Analytics requires additional permissions",
                error_type="PermissionError",
                note="Personal analytics are limited. Organization analytics require admin access.",
            )

        response.raise_for_status()
        data = response.json()

        return _ok(
            action="get_analytics",
            analytics=data.get("elements", []),
        )
    except Exception as e:
        return _err(
            f"Analytics API access restricted: {str(e)}",
            error_type="APIError",
            note="Analytics are primarily available for organization pages",
        )


def _delete_post(post_id: str, **kwargs) -> Dict[str, Any]:
    """Delete a post."""
    if not post_id:
        return _err("post_id is required")

    requests = _get_requests()

    response = requests.delete(
        f"{BASE_URL}/ugcPosts/{post_id}",
        headers=_get_headers(),
        timeout=30,
    )

    if response.status_code == 403:
        return _err(
            "Access denied: Deleting requires w_member_social permission",
            error_type="PermissionError",
        )

    if response.status_code == 404:
        return _err(f"Post not found: {post_id}", error_type="NotFound")

    response.raise_for_status()

    return _ok(
        action="delete_post",
        post_id=post_id,
        deleted=True,
    )


_ACTIONS = {
    "get_profile": _get_profile,
    "get_connections": _get_connections,
    "create_post": _create_post,
    "get_posts": _get_posts,
    "get_company": _get_company,
    "share_url": _share_url,
    "get_analytics": _get_analytics,
    "delete_post": _delete_post,
}


@tool
def linkedin(
    action: str,
    text: Optional[str] = None,
    visibility: Optional[str] = None,
    media_url: Optional[str] = None,
    url: Optional[str] = None,
    comment: Optional[str] = None,
    company_id: Optional[str] = None,
    post_id: Optional[str] = None,
    time_range: Optional[str] = None,
    count: Optional[int] = None,
    start: Optional[int] = None,
) -> Dict[str, Any]:
    """
    Access LinkedIn profile and posting (official API with restrictions).

    Actions:
    - get_profile: Get the authenticated user's profile
    - get_connections: Get user's connections (requires special permission)
    - create_post: Create a post on LinkedIn
    - get_posts: Get user's posts
    - get_company: Get company information
    - share_url: Share a URL on LinkedIn
    - get_analytics: Get analytics (requires additional permissions)
    - delete_post: Delete a post

    Args:
        action: The action to perform
        text: Text content for create_post action (required for create_post)
        visibility: Visibility setting for posts - "PUBLIC" or "CONNECTIONS" (optional, default "PUBLIC")
        media_url: URL of media to attach to post (optional for create_post)
        url: URL to share (required for share_url action)
        comment: Comment to add when sharing a URL (optional for share_url)
        company_id: Company ID to look up (required for get_company action)
        post_id: Post ID to delete (required for delete_post action)
        time_range: Time range for analytics (optional for get_analytics)
        count: Number of items to retrieve (optional for get_connections, get_posts; default 10)
        start: Starting offset for pagination (optional for get_connections, get_posts; default 0)

    Returns:
        dict with success status and action-specific data

    Note:
        LinkedIn's official API has significant restrictions. Most features
        require an approved LinkedIn Developer App with specific permissions.

    Authentication:
        Set LINKEDIN_ACCESS_TOKEN environment variable with your OAuth 2.0 access token.
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
    if text is not None:
        kwargs["text"] = text
    if visibility is not None:
        kwargs["visibility"] = visibility
    if media_url is not None:
        kwargs["media_url"] = media_url
    if url is not None:
        kwargs["url"] = url
    if comment is not None:
        kwargs["comment"] = comment
    if company_id is not None:
        kwargs["company_id"] = company_id
    if post_id is not None:
        kwargs["post_id"] = post_id
    if time_range is not None:
        kwargs["time_range"] = time_range
    if count is not None:
        kwargs["count"] = count
    if start is not None:
        kwargs["start"] = start

    try:
        return _ACTIONS[action](**kwargs)
    except ImportError as e:
        return _err(str(e), error_type="ImportError")
    except ValueError as e:
        return _err(str(e), error_type="ValueError")
    except Exception as e:
        error_message = str(e)
        if hasattr(e, "response") and e.response is not None:
            try:
                error_data = e.response.json()
                error_message = error_data.get("message", str(e))
            except Exception:
                pass
        return _err(error_message, error_type=type(e).__name__, action=action)
