"""
GitHub Tool

GitHub repository, issue, and PR management using REST API.

Usage Examples:
    from strands import Agent
    from strands_pack import github

    agent = Agent(tools=[github])

    # Create an issue
    agent.tool.github(action="create_issue", repo="owner/repo", title="Bug report", body="Description here")

    # Create issue with labels and assignees
    agent.tool.github(action="create_issue", repo="owner/repo", title="Feature request", labels=["enhancement"], assignees=["username"])

    # List issues
    agent.tool.github(action="list_issues", repo="owner/repo", state="open")

    # Get a specific issue
    agent.tool.github(action="get_issue", repo="owner/repo", issue_number=42)

    # Create a pull request
    agent.tool.github(action="create_pr", repo="owner/repo", title="Add feature", head="feature-branch", base="main")

    # List pull requests
    agent.tool.github(action="list_prs", repo="owner/repo", state="open")

    # Get repository info
    agent.tool.github(action="get_repo", repo="owner/repo")

    # List repositories
    agent.tool.github(action="list_repos", owner="username")

    # Create a comment on an issue or PR
    agent.tool.github(action="create_comment", repo="owner/repo", issue_number=42, body="Great work!")

    # Search code
    agent.tool.github(action="search_code", query="language:python requests")

    # Get user info
    agent.tool.github(action="get_user", username="octocat")

    # Get authenticated user info
    agent.tool.github(action="get_user")

Available Actions:
    - create_issue: Create a new issue
        Parameters: repo (str), title (str), body (str), labels (list), assignees (list)
    - list_issues: List repository issues
        Parameters: repo (str), state (str), labels (str), per_page (int)
    - get_issue: Get a specific issue
        Parameters: repo (str), issue_number (int)
    - create_pr: Create a pull request
        Parameters: repo (str), title (str), head (str), base (str), body (str), draft (bool)
    - list_prs: List pull requests
        Parameters: repo (str), state (str), per_page (int)
    - get_pr: Get PR details (optionally includes files and/or diff)
        Parameters: repo (str), pr_number (int), include_files (bool), include_diff (bool), per_page (int), max_files (int)
    - list_pr_files: List files changed in a PR
        Parameters: repo (str), pr_number (int), per_page (int)
    - get_pr_diff: Get unified diff for a PR
        Parameters: repo (str), pr_number (int), diff_format ("diff"|"patch")
    - get_file_contents: Read a file from a repo via API
        Parameters: repo (str), path (str), ref (str)
    - create_or_update_file: Create or update a file via the Contents API
        Parameters: repo (str), path (str), content (str), message (str), branch (str), sha (str), overwrite (bool)
    - delete_file: Delete a file via the Contents API (guarded)
        Parameters: repo (str), path (str), message (str), branch (str), sha (str), confirm_text (str)
    - close_issue: Close an issue (or PR) (guarded)
        Parameters: repo (str), issue_number (int), confirm_text (str)
    - update_pr: Update PR title/body/state/base/draft (closing is guarded)
        Parameters: repo (str), pr_number (int), title (str), body (str), state (str), base (str), draft (bool), confirm_text (str)
    - merge_pr: Merge a PR (guarded)
        Parameters: repo (str), pr_number (int), merge_method (str), commit_title (str), commit_message (str), confirm_text (str)
    - set_labels: Replace all labels on an issue/PR
        Parameters: repo (str), issue_number (int), labels (list[str])
    - add_labels: Add labels to an issue/PR
        Parameters: repo (str), issue_number (int), labels (list[str])
    - remove_label: Remove a single label from an issue/PR
        Parameters: repo (str), issue_number (int), label (str)
    - get_repo: Get repository info
        Parameters: repo (str)
    - list_repos: List repositories
        Parameters: owner (str), type (str), per_page (int)
    - create_comment: Create a comment on issue/PR
        Parameters: repo (str), issue_number (int), body (str)
    - search_code: Search code on GitHub
        Parameters: query (str), per_page (int), page (int)
    - get_user: Get user info
        Parameters: username (str, optional - defaults to authenticated user)

Environment Variables:
    GITHUB_TOKEN: GitHub personal access token (required)

Requirements:
    pip install strands-pack[github]
"""

import os
import base64
from typing import Any, Dict, Optional, List

from strands import tool

try:
    import requests
    HAS_REQUESTS = True
except ImportError:
    HAS_REQUESTS = False


GITHUB_API_BASE = "https://api.github.com"


def _check_requests() -> Optional[Dict[str, Any]]:
    """Check if requests is installed."""
    if not HAS_REQUESTS:
        return {
            "success": False,
            "error": "requests not installed. Run: pip install strands-pack[github]"
        }
    return None


def _get_token() -> Optional[str]:
    """Get GitHub token from environment."""
    return os.environ.get("GITHUB_TOKEN")


def _get_headers() -> Dict[str, str]:
    """Get headers for GitHub API requests."""
    headers = {
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
        "User-Agent": "Strands-Pack-GitHub/1.0"
    }
    token = _get_token()
    if token:
        headers["Authorization"] = f"Bearer {token}"
    return headers


def _make_request(
    method: str,
    endpoint: str,
    *,
    headers_override: Optional[Dict[str, str]] = None,
    expect_json: bool = True,
    **kwargs,
) -> Dict[str, Any]:
    """Make a request to GitHub API."""
    url = f"{GITHUB_API_BASE}{endpoint}"
    headers = _get_headers()
    if headers_override:
        headers.update(headers_override)

    response = requests.request(method, url, headers=headers, timeout=30, **kwargs)

    if response.status_code >= 400:
        error_data: Dict[str, Any] = {}
        if response.text:
            try:
                error_data = response.json()
            except Exception:
                error_data = {"message": response.text[:500]}
        return {
            "success": False,
            "error": error_data.get("message", f"HTTP {response.status_code}"),
            "status_code": response.status_code,
            "documentation_url": error_data.get("documentation_url")
        }

    if response.status_code == 204:
        return {"success": True, "data": None}

    if not expect_json:
        return {"success": True, "data": response.text}

    return {"success": True, "data": response.json()}


def _require_repo(repo: Optional[str]) -> Optional[Dict[str, Any]]:
    if not repo:
        return {"success": False, "error": "repo is required (format: owner/repo)"}
    return None


def _require_number(name: str, number: Any) -> Optional[Dict[str, Any]]:
    if number is None:
        return {"success": False, "error": f"{name} is required"}
    return None


def _confirm_or_err(confirm_text: Optional[str], required: str, *, action: str) -> Optional[Dict[str, Any]]:
    if confirm_text != required:
        return {
            "success": False,
            "action": action,
            "error": "Confirmation required for this action",
            "confirm_required": required,
        }
    return None


def _action_create_issue(**kwargs) -> Dict[str, Any]:
    """Create a new issue."""
    repo = kwargs.get("repo")
    title = kwargs.get("title")
    body = kwargs.get("body", "")
    labels = kwargs.get("labels", [])
    assignees = kwargs.get("assignees", [])

    if not repo:
        return {"success": False, "error": "repo is required (format: owner/repo)"}
    if not title:
        return {"success": False, "error": "title is required"}

    payload = {"title": title}
    if body:
        payload["body"] = body
    if labels:
        payload["labels"] = labels
    if assignees:
        payload["assignees"] = assignees

    result = _make_request("POST", f"/repos/{repo}/issues", json=payload)

    if result["success"]:
        issue = result["data"]
        return {
            "success": True,
            "action": "create_issue",
            "issue_number": issue["number"],
            "url": issue["html_url"],
            "title": issue["title"],
            "state": issue["state"],
            "created_at": issue["created_at"]
        }
    return result


def _action_list_issues(**kwargs) -> Dict[str, Any]:
    """List repository issues."""
    repo = kwargs.get("repo")
    state = kwargs.get("state", "open")
    labels = kwargs.get("labels", "")
    per_page = kwargs.get("per_page", 30)

    if not repo:
        return {"success": False, "error": "repo is required (format: owner/repo)"}

    params = {"state": state, "per_page": per_page}
    if labels:
        params["labels"] = labels

    result = _make_request("GET", f"/repos/{repo}/issues", params=params)

    if result["success"]:
        issues = result["data"]
        return {
            "success": True,
            "action": "list_issues",
            "repo": repo,
            "state": state,
            "count": len(issues),
            "issues": [
                {
                    "number": i["number"],
                    "title": i["title"],
                    "state": i["state"],
                    "url": i["html_url"],
                    "created_at": i["created_at"],
                    "user": i["user"]["login"],
                    "labels": [l["name"] for l in i.get("labels", [])],
                    "comments": i["comments"]
                }
                for i in issues
            ]
        }
    return result


def _action_get_issue(**kwargs) -> Dict[str, Any]:
    """Get a specific issue."""
    repo = kwargs.get("repo")
    issue_number = kwargs.get("issue_number")

    if not repo:
        return {"success": False, "error": "repo is required (format: owner/repo)"}
    if issue_number is None:
        return {"success": False, "error": "issue_number is required"}

    result = _make_request("GET", f"/repos/{repo}/issues/{issue_number}")

    if result["success"]:
        issue = result["data"]
        return {
            "success": True,
            "action": "get_issue",
            "number": issue["number"],
            "title": issue["title"],
            "body": issue.get("body", ""),
            "state": issue["state"],
            "url": issue["html_url"],
            "user": issue["user"]["login"],
            "labels": [l["name"] for l in issue.get("labels", [])],
            "assignees": [a["login"] for a in issue.get("assignees", [])],
            "comments": issue["comments"],
            "created_at": issue["created_at"],
            "updated_at": issue["updated_at"],
            "closed_at": issue.get("closed_at")
        }
    return result


def _action_create_pr(**kwargs) -> Dict[str, Any]:
    """Create a pull request."""
    repo = kwargs.get("repo")
    title = kwargs.get("title")
    head = kwargs.get("head")
    base = kwargs.get("base")
    body = kwargs.get("body", "")
    draft = kwargs.get("draft", False)

    if not repo:
        return {"success": False, "error": "repo is required (format: owner/repo)"}
    if not title:
        return {"success": False, "error": "title is required"}
    if not head:
        return {"success": False, "error": "head is required (source branch)"}
    if not base:
        return {"success": False, "error": "base is required (target branch)"}

    payload = {
        "title": title,
        "head": head,
        "base": base,
        "draft": draft
    }
    if body:
        payload["body"] = body

    result = _make_request("POST", f"/repos/{repo}/pulls", json=payload)

    if result["success"]:
        pr = result["data"]
        return {
            "success": True,
            "action": "create_pr",
            "number": pr["number"],
            "url": pr["html_url"],
            "title": pr["title"],
            "state": pr["state"],
            "draft": pr["draft"],
            "head": pr["head"]["ref"],
            "base": pr["base"]["ref"],
            "created_at": pr["created_at"]
        }
    return result


def _action_list_prs(**kwargs) -> Dict[str, Any]:
    """List pull requests."""
    repo = kwargs.get("repo")
    state = kwargs.get("state", "open")
    per_page = kwargs.get("per_page", 30)

    if not repo:
        return {"success": False, "error": "repo is required (format: owner/repo)"}

    params = {"state": state, "per_page": per_page}

    result = _make_request("GET", f"/repos/{repo}/pulls", params=params)

    if result["success"]:
        prs = result["data"]
        return {
            "success": True,
            "action": "list_prs",
            "repo": repo,
            "state": state,
            "count": len(prs),
            "pull_requests": [
                {
                    "number": pr["number"],
                    "title": pr["title"],
                    "state": pr["state"],
                    "draft": pr["draft"],
                    "url": pr["html_url"],
                    "user": pr["user"]["login"],
                    "head": pr["head"]["ref"],
                    "base": pr["base"]["ref"],
                    "created_at": pr["created_at"],
                    "updated_at": pr["updated_at"]
                }
                for pr in prs
            ]
        }
    return result


def _action_get_repo(**kwargs) -> Dict[str, Any]:
    """Get repository info."""
    repo = kwargs.get("repo")

    if not repo:
        return {"success": False, "error": "repo is required (format: owner/repo)"}

    result = _make_request("GET", f"/repos/{repo}")

    if result["success"]:
        r = result["data"]
        return {
            "success": True,
            "action": "get_repo",
            "name": r["name"],
            "full_name": r["full_name"],
            "description": r.get("description", ""),
            "url": r["html_url"],
            "clone_url": r["clone_url"],
            "default_branch": r["default_branch"],
            "language": r.get("language"),
            "private": r["private"],
            "fork": r["fork"],
            "stargazers_count": r["stargazers_count"],
            "watchers_count": r["watchers_count"],
            "forks_count": r["forks_count"],
            "open_issues_count": r["open_issues_count"],
            "created_at": r["created_at"],
            "updated_at": r["updated_at"],
            "pushed_at": r["pushed_at"]
        }
    return result


def _action_list_repos(**kwargs) -> Dict[str, Any]:
    """List repositories."""
    owner = kwargs.get("owner")
    repo_type = kwargs.get("type", "all")
    per_page = kwargs.get("per_page", 30)

    params = {"type": repo_type, "per_page": per_page}

    if owner:
        endpoint = f"/users/{owner}/repos"
    else:
        endpoint = "/user/repos"

    result = _make_request("GET", endpoint, params=params)

    if result["success"]:
        repos = result["data"]
        return {
            "success": True,
            "action": "list_repos",
            "owner": owner or "authenticated user",
            "count": len(repos),
            "repositories": [
                {
                    "name": r["name"],
                    "full_name": r["full_name"],
                    "description": r.get("description", ""),
                    "url": r["html_url"],
                    "private": r["private"],
                    "language": r.get("language"),
                    "stargazers_count": r["stargazers_count"],
                    "updated_at": r["updated_at"]
                }
                for r in repos
            ]
        }
    return result


def _action_create_comment(**kwargs) -> Dict[str, Any]:
    """Create a comment on an issue or PR."""
    repo = kwargs.get("repo")
    issue_number = kwargs.get("issue_number")
    body = kwargs.get("body")

    if not repo:
        return {"success": False, "error": "repo is required (format: owner/repo)"}
    if issue_number is None:
        return {"success": False, "error": "issue_number is required"}
    if not body:
        return {"success": False, "error": "body is required"}

    payload = {"body": body}

    result = _make_request("POST", f"/repos/{repo}/issues/{issue_number}/comments", json=payload)

    if result["success"]:
        comment = result["data"]
        return {
            "success": True,
            "action": "create_comment",
            "comment_id": comment["id"],
            "url": comment["html_url"],
            "body": comment["body"][:100] + "..." if len(comment["body"]) > 100 else comment["body"],
            "created_at": comment["created_at"]
        }
    return result


def _action_search_code(**kwargs) -> Dict[str, Any]:
    """Search code on GitHub."""
    query = kwargs.get("query")
    per_page = kwargs.get("per_page", 30)
    page = kwargs.get("page", 1)

    if not query:
        return {"success": False, "error": "query is required"}

    params = {"q": query, "per_page": per_page, "page": page}

    result = _make_request("GET", "/search/code", params=params)

    if result["success"]:
        data = result["data"]
        return {
            "success": True,
            "action": "search_code",
            "query": query,
            "total_count": data["total_count"],
            "incomplete_results": data["incomplete_results"],
            "items": [
                {
                    "name": item["name"],
                    "path": item["path"],
                    "repository": item["repository"]["full_name"],
                    "url": item["html_url"],
                    "sha": item["sha"]
                }
                for item in data["items"]
            ]
        }
    return result


def _action_get_user(**kwargs) -> Dict[str, Any]:
    """Get user info."""
    username = kwargs.get("username")

    if username:
        endpoint = f"/users/{username}"
    else:
        endpoint = "/user"

    result = _make_request("GET", endpoint)

    if result["success"]:
        user = result["data"]
        return {
            "success": True,
            "action": "get_user",
            "login": user["login"],
            "name": user.get("name"),
            "email": user.get("email"),
            "bio": user.get("bio"),
            "url": user["html_url"],
            "avatar_url": user["avatar_url"],
            "public_repos": user["public_repos"],
            "followers": user["followers"],
            "following": user["following"],
            "created_at": user["created_at"]
        }
    return result


def _action_get_pr(**kwargs) -> Dict[str, Any]:
    """Get PR details. Optionally includes changed files and/or diff."""
    repo = kwargs.get("repo")
    pr_number = kwargs.get("pr_number")
    include_files = bool(kwargs.get("include_files", False))
    include_diff = bool(kwargs.get("include_diff", False))
    per_page = kwargs.get("per_page", 30)
    max_files = kwargs.get("max_files", 200)
    diff_format = (kwargs.get("diff_format") or "diff").strip().lower()

    if err := _require_repo(repo):
        return err
    if err := _require_number("pr_number", pr_number):
        return err

    pr_res = _make_request("GET", f"/repos/{repo}/pulls/{pr_number}")
    if not pr_res["success"]:
        return pr_res

    pr = pr_res["data"]
    out: Dict[str, Any] = {
        "success": True,
        "action": "get_pr",
        "repo": repo,
        "number": pr["number"],
        "url": pr["html_url"],
        "state": pr["state"],
        "draft": pr.get("draft", False),
        "title": pr["title"],
        "body": pr.get("body") or "",
        "user": pr["user"]["login"],
        "head": pr["head"]["ref"],
        "base": pr["base"]["ref"],
        "head_sha": pr["head"]["sha"],
        "base_sha": pr["base"]["sha"],
        "merged": pr.get("merged", False),
        "mergeable": pr.get("mergeable"),
        "rebaseable": pr.get("rebaseable"),
        "changed_files": pr.get("changed_files"),
        "additions": pr.get("additions"),
        "deletions": pr.get("deletions"),
        "commits": pr.get("commits"),
        "created_at": pr.get("created_at"),
        "updated_at": pr.get("updated_at"),
    }

    if include_files:
        files_res = _action_list_pr_files(repo=repo, pr_number=pr_number, per_page=per_page)
        if not files_res["success"]:
            return files_res
        files = files_res["files"]
        # safety cap
        if isinstance(files, list) and len(files) > int(max_files):
            files = files[: int(max_files)]
            out["files_truncated"] = True
        out["files"] = files

    if include_diff:
        diff_res = _action_get_pr_diff(repo=repo, pr_number=pr_number, diff_format=diff_format)
        if not diff_res["success"]:
            return diff_res
        out["diff_format"] = diff_format
        out["diff"] = diff_res["diff"]

    return out


def _action_list_pr_files(**kwargs) -> Dict[str, Any]:
    """List files changed in a PR."""
    repo = kwargs.get("repo")
    pr_number = kwargs.get("pr_number")
    per_page = kwargs.get("per_page", 30)
    if err := _require_repo(repo):
        return err
    if err := _require_number("pr_number", pr_number):
        return err

    params = {"per_page": min(int(per_page or 30), 100)}
    res = _make_request("GET", f"/repos/{repo}/pulls/{pr_number}/files", params=params)
    if not res["success"]:
        return res
    files = res["data"]
    return {
        "success": True,
        "action": "list_pr_files",
        "repo": repo,
        "pr_number": pr_number,
        "count": len(files),
        "files": [
            {
                "filename": f.get("filename"),
                "status": f.get("status"),
                "additions": f.get("additions"),
                "deletions": f.get("deletions"),
                "changes": f.get("changes"),
                "patch": f.get("patch"),
                "sha": f.get("sha"),
            }
            for f in files
        ],
    }


def _action_get_pr_diff(**kwargs) -> Dict[str, Any]:
    """Get PR diff/patch as text."""
    repo = kwargs.get("repo")
    pr_number = kwargs.get("pr_number")
    diff_format = (kwargs.get("diff_format") or "diff").strip().lower()

    if err := _require_repo(repo):
        return err
    if err := _require_number("pr_number", pr_number):
        return err
    if diff_format not in ("diff", "patch"):
        return {"success": False, "error": "diff_format must be 'diff' or 'patch'"}

    accept = "application/vnd.github.v3.diff" if diff_format == "diff" else "application/vnd.github.v3.patch"
    res = _make_request(
        "GET",
        f"/repos/{repo}/pulls/{pr_number}",
        headers_override={"Accept": accept},
        expect_json=False,
    )
    if not res["success"]:
        return res
    return {
        "success": True,
        "action": "get_pr_diff",
        "repo": repo,
        "pr_number": pr_number,
        "diff_format": diff_format,
        "diff": res["data"],
    }


def _action_get_file_contents(**kwargs) -> Dict[str, Any]:
    """Get file contents via the GitHub Contents API."""
    repo = kwargs.get("repo")
    path = kwargs.get("path")
    ref = kwargs.get("ref")
    max_chars = int(kwargs.get("max_chars") or 200_000)

    if err := _require_repo(repo):
        return err
    if not path:
        return {"success": False, "error": "path is required"}

    params = {}
    if ref:
        params["ref"] = ref

    res = _make_request("GET", f"/repos/{repo}/contents/{path}", params=params)
    if not res["success"]:
        return res

    data = res["data"]
    # For directories, GitHub returns a list; we keep it metadata-only.
    if isinstance(data, list):
        return {
            "success": True,
            "action": "get_file_contents",
            "repo": repo,
            "path": path,
            "ref": ref,
            "is_directory": True,
            "items": [{"name": i.get("name"), "path": i.get("path"), "type": i.get("type"), "sha": i.get("sha")} for i in data],
        }

    encoding = data.get("encoding")
    content_b64 = data.get("content", "")
    text = None
    if encoding == "base64" and content_b64:
        try:
            raw = base64.b64decode(content_b64.encode("utf-8"), validate=False)
            # best-effort decode
            text = raw.decode("utf-8", errors="replace")
        except Exception:
            text = None

    truncated = False
    if isinstance(text, str) and len(text) > max_chars:
        text = text[:max_chars]
        truncated = True

    return {
        "success": True,
        "action": "get_file_contents",
        "repo": repo,
        "path": path,
        "ref": ref,
        "sha": data.get("sha"),
        "size": data.get("size"),
        "download_url": data.get("download_url"),
        "html_url": data.get("html_url"),
        "encoding": encoding,
        "text": text,
        "truncated": truncated,
    }


def _action_create_or_update_file(**kwargs) -> Dict[str, Any]:
    """Create or update a file via the GitHub Contents API (no git required)."""
    repo = kwargs.get("repo")
    path = kwargs.get("path")
    content = kwargs.get("content")
    message = kwargs.get("message")
    branch = kwargs.get("branch")
    sha = kwargs.get("sha")
    overwrite = bool(kwargs.get("overwrite", True))

    if err := _require_repo(repo):
        return err
    if not path:
        return {"success": False, "error": "path is required"}
    if content is None:
        return {"success": False, "error": "content is required"}
    if not message:
        return {"success": False, "error": "message is required"}
    if not branch:
        return {"success": False, "error": "branch is required"}

    # Determine sha if updating (and not provided)
    if sha is None:
        existing = _make_request("GET", f"/repos/{repo}/contents/{path}", params={"ref": branch})
        if existing["success"] and isinstance(existing["data"], dict) and existing["data"].get("sha"):
            if not overwrite:
                return {"success": False, "error": "File exists and overwrite is False", "sha": existing["data"]["sha"]}
            sha = existing["data"]["sha"]

    encoded = base64.b64encode(str(content).encode("utf-8")).decode("utf-8")
    payload: Dict[str, Any] = {"message": message, "content": encoded, "branch": branch}
    if sha:
        payload["sha"] = sha

    res = _make_request("PUT", f"/repos/{repo}/contents/{path}", json=payload)
    if not res["success"]:
        return res

    data = res["data"]
    return {
        "success": True,
        "action": "create_or_update_file",
        "repo": repo,
        "path": path,
        "branch": branch,
        "commit_sha": (data.get("commit") or {}).get("sha"),
        "content_sha": (data.get("content") or {}).get("sha"),
        "html_url": (data.get("content") or {}).get("html_url"),
    }


def _action_delete_file(**kwargs) -> Dict[str, Any]:
    """Delete a file via the GitHub Contents API. Guarded by confirm_text."""
    repo = kwargs.get("repo")
    path = kwargs.get("path")
    message = kwargs.get("message")
    branch = kwargs.get("branch")
    sha = kwargs.get("sha")
    confirm_text = kwargs.get("confirm_text")

    if err := _require_repo(repo):
        return err
    if not path:
        return {"success": False, "error": "path is required"}
    if not message:
        return {"success": False, "error": "message is required"}
    if not branch:
        return {"success": False, "error": "branch is required"}

    required = f"DELETE_FILE {repo}:{path}@{branch}"
    if err := _confirm_or_err(confirm_text, required, action="delete_file"):
        return err

    # Resolve sha if not provided
    if sha is None:
        existing = _make_request("GET", f"/repos/{repo}/contents/{path}", params={"ref": branch})
        if not existing["success"]:
            return existing
        if isinstance(existing["data"], list):
            return {"success": False, "error": "path points to a directory; delete_file only supports files"}
        sha = (existing["data"] or {}).get("sha")
        if not sha:
            return {"success": False, "error": "Could not resolve file sha for deletion"}

    payload: Dict[str, Any] = {"message": message, "sha": sha, "branch": branch}
    res = _make_request("DELETE", f"/repos/{repo}/contents/{path}", json=payload)
    if not res["success"]:
        return res
    data = res["data"] or {}
    return {
        "success": True,
        "action": "delete_file",
        "repo": repo,
        "path": path,
        "branch": branch,
        "commit_sha": (data.get("commit") or {}).get("sha"),
    }


def _action_close_issue(**kwargs) -> Dict[str, Any]:
    """Close an issue (or PR) via Issues API. Guarded by confirm_text."""
    repo = kwargs.get("repo")
    issue_number = kwargs.get("issue_number")
    confirm_text = kwargs.get("confirm_text")

    if err := _require_repo(repo):
        return err
    if err := _require_number("issue_number", issue_number):
        return err

    required = f"CLOSE_ISSUE {repo}#{issue_number}"
    if err := _confirm_or_err(confirm_text, required, action="close_issue"):
        return err

    res = _make_request("PATCH", f"/repos/{repo}/issues/{issue_number}", json={"state": "closed"})
    if not res["success"]:
        return res
    issue = res["data"]
    return {
        "success": True,
        "action": "close_issue",
        "repo": repo,
        "number": issue.get("number"),
        "state": issue.get("state"),
        "url": issue.get("html_url"),
    }


def _action_update_pr(**kwargs) -> Dict[str, Any]:
    """Update PR properties. Closing is guarded by confirm_text."""
    repo = kwargs.get("repo")
    pr_number = kwargs.get("pr_number")
    title = kwargs.get("title")
    body = kwargs.get("body")
    state = kwargs.get("state")
    base = kwargs.get("base")
    draft = kwargs.get("draft")
    confirm_text = kwargs.get("confirm_text")

    if err := _require_repo(repo):
        return err
    if err := _require_number("pr_number", pr_number):
        return err

    payload: Dict[str, Any] = {}
    if title is not None:
        payload["title"] = title
    if body is not None:
        payload["body"] = body
    if base is not None:
        payload["base"] = base
    if draft is not None:
        payload["draft"] = bool(draft)
    if state is not None:
        if state not in ("open", "closed"):
            return {"success": False, "error": "state must be 'open' or 'closed'"}
        if state == "closed":
            required = f"CLOSE_PR {repo}#{pr_number}"
            if err := _confirm_or_err(confirm_text, required, action="update_pr"):
                return err
        payload["state"] = state

    if not payload:
        return {"success": False, "error": "Provide at least one field to update (title/body/state/base/draft)"}

    res = _make_request("PATCH", f"/repos/{repo}/pulls/{pr_number}", json=payload)
    if not res["success"]:
        return res
    pr = res["data"]
    return {
        "success": True,
        "action": "update_pr",
        "repo": repo,
        "number": pr.get("number"),
        "state": pr.get("state"),
        "title": pr.get("title"),
        "url": pr.get("html_url"),
        "draft": pr.get("draft"),
    }


def _action_merge_pr(**kwargs) -> Dict[str, Any]:
    """Merge a PR. Guarded by confirm_text."""
    repo = kwargs.get("repo")
    pr_number = kwargs.get("pr_number")
    merge_method = (kwargs.get("merge_method") or "squash").strip().lower()
    commit_title = kwargs.get("commit_title")
    commit_message = kwargs.get("commit_message")
    confirm_text = kwargs.get("confirm_text")

    if err := _require_repo(repo):
        return err
    if err := _require_number("pr_number", pr_number):
        return err

    required = f"MERGE_PR {repo}#{pr_number}"
    if err := _confirm_or_err(confirm_text, required, action="merge_pr"):
        return err

    if merge_method not in ("merge", "squash", "rebase"):
        return {"success": False, "error": "merge_method must be one of: merge, squash, rebase"}

    payload: Dict[str, Any] = {"merge_method": merge_method}
    if commit_title:
        payload["commit_title"] = commit_title
    if commit_message:
        payload["commit_message"] = commit_message

    res = _make_request("PUT", f"/repos/{repo}/pulls/{pr_number}/merge", json=payload)
    if not res["success"]:
        return res
    data = res["data"] or {}
    return {
        "success": True,
        "action": "merge_pr",
        "repo": repo,
        "pr_number": pr_number,
        "merged": data.get("merged", True),
        "message": data.get("message"),
        "sha": data.get("sha"),
    }


def _action_set_labels(**kwargs) -> Dict[str, Any]:
    """Replace all labels on an issue/PR."""
    repo = kwargs.get("repo")
    issue_number = kwargs.get("issue_number")
    labels = kwargs.get("labels") or []
    if err := _require_repo(repo):
        return err
    if err := _require_number("issue_number", issue_number):
        return err
    if not isinstance(labels, list):
        return {"success": False, "error": "labels must be a list of strings"}

    res = _make_request("PUT", f"/repos/{repo}/issues/{issue_number}/labels", json=labels)
    if not res["success"]:
        return res
    return {"success": True, "action": "set_labels", "repo": repo, "issue_number": issue_number, "labels": [l.get('name') for l in (res['data'] or [])]}


def _action_add_labels(**kwargs) -> Dict[str, Any]:
    """Add labels to an issue/PR."""
    repo = kwargs.get("repo")
    issue_number = kwargs.get("issue_number")
    labels = kwargs.get("labels") or []
    if err := _require_repo(repo):
        return err
    if err := _require_number("issue_number", issue_number):
        return err
    if not isinstance(labels, list):
        return {"success": False, "error": "labels must be a list of strings"}

    res = _make_request("POST", f"/repos/{repo}/issues/{issue_number}/labels", json=labels)
    if not res["success"]:
        return res
    return {"success": True, "action": "add_labels", "repo": repo, "issue_number": issue_number, "labels": [l.get('name') for l in (res['data'] or [])]}


def _action_remove_label(**kwargs) -> Dict[str, Any]:
    """Remove a label from an issue/PR."""
    repo = kwargs.get("repo")
    issue_number = kwargs.get("issue_number")
    label = kwargs.get("label")
    if err := _require_repo(repo):
        return err
    if err := _require_number("issue_number", issue_number):
        return err
    if not label:
        return {"success": False, "error": "label is required"}

    res = _make_request("DELETE", f"/repos/{repo}/issues/{issue_number}/labels/{label}")
    if not res["success"]:
        return res
    return {"success": True, "action": "remove_label", "repo": repo, "issue_number": issue_number, "removed": label}


# Action dispatcher
_ACTIONS = {
    "create_issue": _action_create_issue,
    "list_issues": _action_list_issues,
    "get_issue": _action_get_issue,
    "create_pr": _action_create_pr,
    "list_prs": _action_list_prs,
    "get_pr": _action_get_pr,
    "list_pr_files": _action_list_pr_files,
    "get_pr_diff": _action_get_pr_diff,
    "get_file_contents": _action_get_file_contents,
    "create_or_update_file": _action_create_or_update_file,
    "delete_file": _action_delete_file,
    "close_issue": _action_close_issue,
    "update_pr": _action_update_pr,
    "merge_pr": _action_merge_pr,
    "set_labels": _action_set_labels,
    "add_labels": _action_add_labels,
    "remove_label": _action_remove_label,
    "get_repo": _action_get_repo,
    "list_repos": _action_list_repos,
    "create_comment": _action_create_comment,
    "search_code": _action_search_code,
    "get_user": _action_get_user,
}


@tool
def github(
    action: str,
    repo: Optional[str] = None,
    title: Optional[str] = None,
    body: Optional[str] = None,
    labels: Optional[list] = None,
    assignees: Optional[list] = None,
    state: Optional[str] = None,
    per_page: Optional[int] = None,
    issue_number: Optional[int] = None,
    pr_number: Optional[int] = None,
    head: Optional[str] = None,
    base: Optional[str] = None,
    draft: Optional[bool] = None,
    owner: Optional[str] = None,
    repo_type: Optional[str] = None,
    query: Optional[str] = None,
    page: Optional[int] = None,
    username: Optional[str] = None,
    # repo content ops
    path: Optional[str] = None,
    ref: Optional[str] = None,
    content: Optional[str] = None,
    message: Optional[str] = None,
    branch: Optional[str] = None,
    sha: Optional[str] = None,
    overwrite: Optional[bool] = None,
    # PR diff/files helpers
    include_files: Optional[bool] = None,
    include_diff: Optional[bool] = None,
    diff_format: Optional[str] = None,
    max_files: Optional[int] = None,
    # merge / guarded actions
    merge_method: Optional[str] = None,
    commit_title: Optional[str] = None,
    commit_message: Optional[str] = None,
    confirm_text: Optional[str] = None,
    # labels helpers
    label: Optional[str] = None,
    max_chars: Optional[int] = None,
) -> dict:
    """
    Manage GitHub repositories, issues, and pull requests.

    Args:
        action: The action to perform. One of:
            - create_issue: Create issue
            - list_issues: List issues
            - get_issue: Get issue
            - create_pr: Create PR
            - list_prs: List PRs
            - get_repo: Get repo info
            - list_repos: List repos
            - create_comment: Create comment
            - search_code: Search code
            - get_user: Get user info
        repo: Repository in format "owner/repo". Required for: create_issue, list_issues,
            get_issue, create_pr, list_prs, get_repo, create_comment.
        title: Title for issue or PR. Required for: create_issue, create_pr.
        body: Body text for issue, PR, or comment. Optional for: create_issue, create_pr.
            Required for: create_comment.
        labels: List of label names. Optional for: create_issue, list_issues.
        assignees: List of usernames to assign. Optional for: create_issue.
        state: Filter by state ("open", "closed", "all"). Optional for: list_issues, list_prs.
            Defaults to "open".
        per_page: Number of results per page (max 100). Optional for: list_issues, list_prs,
            list_repos, search_code. Defaults to 30.
        issue_number: Issue or PR number. Required for: get_issue, create_comment.
        head: Source branch name. Required for: create_pr.
        base: Target branch name. Required for: create_pr.
        draft: Create PR as draft. Optional for: create_pr. Defaults to False.
        owner: Username for listing repos. Optional for: list_repos. If not provided,
            lists authenticated user's repos.
        repo_type: Type of repos to list ("all", "owner", "member"). Optional for: list_repos.
            Defaults to "all".
        query: Search query string. Required for: search_code.
        page: Page number for paginated results. Optional for: search_code. Defaults to 1.
        username: GitHub username. Optional for: get_user. If not provided, returns
            authenticated user info.

    Returns:
        dict: Result with "success" key and action-specific data

    Examples:
        >>> github(action="create_issue", repo="owner/repo", title="Bug report")
        >>> github(action="list_issues", repo="owner/repo", state="open")
        >>> github(action="get_repo", repo="owner/repo")
    """
    if err := _check_requests():
        return err

    if not _get_token():
        return {
            "success": False,
            "error": "GITHUB_TOKEN environment variable not set",
            "hint": "Set GITHUB_TOKEN with a personal access token"
        }

    if action not in _ACTIONS:
        return {
            "success": False,
            "error": f"Unknown action: {action}",
            "available_actions": list(_ACTIONS.keys())
        }

    # Build kwargs dict from explicit parameters
    kwargs: Dict[str, Any] = {}
    if repo is not None:
        kwargs["repo"] = repo
    if title is not None:
        kwargs["title"] = title
    if body is not None:
        kwargs["body"] = body
    if labels is not None:
        kwargs["labels"] = labels
    if assignees is not None:
        kwargs["assignees"] = assignees
    if state is not None:
        kwargs["state"] = state
    if per_page is not None:
        kwargs["per_page"] = per_page
    if issue_number is not None:
        kwargs["issue_number"] = issue_number
    if head is not None:
        kwargs["head"] = head
    if base is not None:
        kwargs["base"] = base
    if draft is not None:
        kwargs["draft"] = draft
    if owner is not None:
        kwargs["owner"] = owner
    if repo_type is not None:
        kwargs["type"] = repo_type
    if query is not None:
        kwargs["query"] = query
    if page is not None:
        kwargs["page"] = page
    if username is not None:
        kwargs["username"] = username
    if pr_number is not None:
        kwargs["pr_number"] = pr_number
    if path is not None:
        kwargs["path"] = path
    if ref is not None:
        kwargs["ref"] = ref
    if content is not None:
        kwargs["content"] = content
    if message is not None:
        kwargs["message"] = message
    if branch is not None:
        kwargs["branch"] = branch
    if sha is not None:
        kwargs["sha"] = sha
    if overwrite is not None:
        kwargs["overwrite"] = overwrite
    if include_files is not None:
        kwargs["include_files"] = include_files
    if include_diff is not None:
        kwargs["include_diff"] = include_diff
    if diff_format is not None:
        kwargs["diff_format"] = diff_format
    if max_files is not None:
        kwargs["max_files"] = max_files
    if merge_method is not None:
        kwargs["merge_method"] = merge_method
    if commit_title is not None:
        kwargs["commit_title"] = commit_title
    if commit_message is not None:
        kwargs["commit_message"] = commit_message
    if confirm_text is not None:
        kwargs["confirm_text"] = confirm_text
    if label is not None:
        kwargs["label"] = label
    if max_chars is not None:
        kwargs["max_chars"] = max_chars

    try:
        return _ACTIONS[action](**kwargs)
    except Exception as e:
        error_type = type(e).__name__
        return {
            "success": False,
            "action": action,
            "error": str(e),
            "error_type": error_type
        }
