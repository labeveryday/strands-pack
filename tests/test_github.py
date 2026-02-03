"""Tests for GitHub tool."""

import os
from unittest.mock import patch

import pytest


@pytest.fixture
def mock_env_token():
    """Mock the GITHUB_TOKEN environment variable."""
    with patch.dict(os.environ, {"GITHUB_TOKEN": "test_token_123"}):
        yield


def test_github_missing_token():
    """Test error when GITHUB_TOKEN is not set."""
    with patch.dict(os.environ, {}, clear=True):
        # Remove GITHUB_TOKEN if it exists
        os.environ.pop("GITHUB_TOKEN", None)

        from strands_pack import github

        result = github(action="get_user")

        assert result["success"] is False
        assert "GITHUB_TOKEN" in result["error"]


def test_github_unknown_action(mock_env_token):
    """Test error for unknown action."""
    from strands_pack import github

    result = github(action="unknown_action")

    assert result["success"] is False
    assert "Unknown action" in result["error"]
    assert "available_actions" in result


def test_github_create_issue_missing_repo(mock_env_token):
    """Test error when repo is missing for create_issue."""
    from strands_pack import github

    result = github(action="create_issue", title="Test Issue")

    assert result["success"] is False
    assert "repo" in result["error"]


def test_github_create_issue_missing_title(mock_env_token):
    """Test error when title is missing for create_issue."""
    from strands_pack import github

    result = github(action="create_issue", repo="owner/repo")

    assert result["success"] is False
    assert "title" in result["error"]


def test_github_list_issues_missing_repo(mock_env_token):
    """Test error when repo is missing for list_issues."""
    from strands_pack import github

    result = github(action="list_issues")

    assert result["success"] is False
    assert "repo" in result["error"]


def test_github_get_issue_missing_params(mock_env_token):
    """Test error when required params are missing for get_issue."""
    from strands_pack import github

    result = github(action="get_issue", repo="owner/repo")

    assert result["success"] is False
    assert "issue_number" in result["error"]


def test_github_create_pr_missing_params(mock_env_token):
    """Test error when required params are missing for create_pr."""
    from strands_pack import github

    result = github(action="create_pr", repo="owner/repo", title="PR Title")

    assert result["success"] is False
    assert "head" in result["error"] or "base" in result["error"]


def test_github_search_code_missing_query(mock_env_token):
    """Test error when query is missing for search_code."""
    from strands_pack import github

    result = github(action="search_code")

    assert result["success"] is False
    assert "query" in result["error"]


def test_github_create_comment_missing_params(mock_env_token):
    """Test error when required params are missing for create_comment."""
    from strands_pack import github

    result = github(action="create_comment", repo="owner/repo", issue_number=1)

    assert result["success"] is False
    assert "body" in result["error"]


@pytest.mark.skip(reason="Requires network access and valid GitHub token")
def test_github_get_repo_integration():
    """Integration test for getting repo info."""
    from strands_pack import github

    result = github(action="get_repo", repo="strands-agents/sdk-python")

    assert result["success"] is True
    assert "name" in result
    assert "full_name" in result


@pytest.mark.skip(reason="Requires network access and valid GitHub token")
def test_github_list_issues_integration():
    """Integration test for listing issues."""
    from strands_pack import github

    result = github(action="list_issues", repo="strands-agents/sdk-python", per_page=5)

    assert result["success"] is True
    assert "issues" in result
    assert "count" in result


@pytest.mark.skip(reason="Requires network access and valid GitHub token")
def test_github_get_user_integration():
    """Integration test for getting user info."""
    from strands_pack import github

    result = github(action="get_user", username="octocat")

    assert result["success"] is True
    assert result["login"] == "octocat"


@patch("strands_pack.github._make_request")
def test_github_create_issue_success(mock_request, mock_env_token):
    """Test successful issue creation with mocked API."""
    mock_request.return_value = {
        "success": True,
        "data": {
            "number": 42,
            "html_url": "https://github.com/owner/repo/issues/42",
            "title": "Test Issue",
            "state": "open",
            "created_at": "2024-01-01T00:00:00Z"
        }
    }

    from strands_pack import github

    result = github(
        action="create_issue",
        repo="owner/repo",
        title="Test Issue",
        body="Issue body",
        labels=["bug"]
    )

    assert result["success"] is True
    assert result["issue_number"] == 42
    assert result["title"] == "Test Issue"
    mock_request.assert_called_once()


@patch("strands_pack.github._make_request")
def test_github_list_issues_success(mock_request, mock_env_token):
    """Test successful issue listing with mocked API."""
    mock_request.return_value = {
        "success": True,
        "data": [
            {
                "number": 1,
                "title": "Issue 1",
                "state": "open",
                "html_url": "https://github.com/owner/repo/issues/1",
                "created_at": "2024-01-01T00:00:00Z",
                "user": {"login": "user1"},
                "labels": [{"name": "bug"}],
                "comments": 5
            },
            {
                "number": 2,
                "title": "Issue 2",
                "state": "open",
                "html_url": "https://github.com/owner/repo/issues/2",
                "created_at": "2024-01-02T00:00:00Z",
                "user": {"login": "user2"},
                "labels": [],
                "comments": 0
            }
        ]
    }

    from strands_pack import github

    result = github(action="list_issues", repo="owner/repo", state="open")

    assert result["success"] is True
    assert result["count"] == 2
    assert len(result["issues"]) == 2
    assert result["issues"][0]["number"] == 1


@patch("strands_pack.github._make_request")
def test_github_get_repo_success(mock_request, mock_env_token):
    """Test successful repo info retrieval with mocked API."""
    mock_request.return_value = {
        "success": True,
        "data": {
            "name": "test-repo",
            "full_name": "owner/test-repo",
            "description": "A test repository",
            "html_url": "https://github.com/owner/test-repo",
            "clone_url": "https://github.com/owner/test-repo.git",
            "default_branch": "main",
            "language": "Python",
            "private": False,
            "fork": False,
            "stargazers_count": 100,
            "watchers_count": 50,
            "forks_count": 25,
            "open_issues_count": 10,
            "created_at": "2023-01-01T00:00:00Z",
            "updated_at": "2024-01-01T00:00:00Z",
            "pushed_at": "2024-01-01T00:00:00Z"
        }
    }

    from strands_pack import github

    result = github(action="get_repo", repo="owner/test-repo")

    assert result["success"] is True
    assert result["name"] == "test-repo"
    assert result["language"] == "Python"
    assert result["stargazers_count"] == 100


@patch("strands_pack.github._make_request")
def test_github_api_error(mock_request, mock_env_token):
    """Test handling of API errors."""
    mock_request.return_value = {
        "success": False,
        "error": "Not Found",
        "status_code": 404
    }

    from strands_pack import github

    result = github(action="get_repo", repo="nonexistent/repo")

    assert result["success"] is False
    assert "Not Found" in result["error"]


@patch("strands_pack.github._make_request")
def test_github_create_pr_success(mock_request, mock_env_token):
    """Test successful PR creation with mocked API."""
    mock_request.return_value = {
        "success": True,
        "data": {
            "number": 10,
            "html_url": "https://github.com/owner/repo/pull/10",
            "title": "Add feature",
            "state": "open",
            "draft": False,
            "head": {"ref": "feature-branch"},
            "base": {"ref": "main"},
            "created_at": "2024-01-01T00:00:00Z"
        }
    }

    from strands_pack import github

    result = github(
        action="create_pr",
        repo="owner/repo",
        title="Add feature",
        head="feature-branch",
        base="main",
        body="PR description"
    )

    assert result["success"] is True
    assert result["number"] == 10
    assert result["head"] == "feature-branch"
    assert result["base"] == "main"


@patch("strands_pack.github._make_request")
def test_github_get_pr_with_files_and_diff(mock_request, mock_env_token):
    """Test get_pr with include_files/include_diff."""
    pr_payload = {
        "number": 12,
        "html_url": "https://github.com/owner/repo/pull/12",
        "title": "Fix bug",
        "state": "open",
        "draft": False,
        "body": "desc",
        "user": {"login": "alice"},
        "head": {"ref": "feat", "sha": "h"},
        "base": {"ref": "main", "sha": "b"},
        "changed_files": 1,
        "additions": 2,
        "deletions": 1,
        "commits": 1,
        "created_at": "2024-01-01T00:00:00Z",
        "updated_at": "2024-01-02T00:00:00Z",
    }
    files_payload = [
        {"filename": "a.py", "status": "modified", "additions": 2, "deletions": 1, "changes": 3, "patch": "@@ ...", "sha": "s"},
    ]
    diff_text = "diff --git a/a.py b/a.py\n"

    mock_request.side_effect = [
        {"success": True, "data": pr_payload},
        {"success": True, "data": files_payload},
        {"success": True, "data": diff_text},
    ]

    from strands_pack import github

    res = github(action="get_pr", repo="owner/repo", pr_number=12, include_files=True, include_diff=True)
    assert res["success"] is True
    assert res["action"] == "get_pr"
    assert res["number"] == 12
    assert len(res["files"]) == 1
    assert res["diff"].startswith("diff --git")


@patch("strands_pack.github._make_request")
def test_github_get_file_contents_decodes_base64(mock_request, mock_env_token):
    """Test get_file_contents decodes base64 content."""
    mock_request.return_value = {
        "success": True,
        "data": {
            "sha": "abc",
            "encoding": "base64",
            "content": "aGVsbG8K",  # hello\n
            "size": 6,
            "download_url": "https://example.com",
            "html_url": "https://github.com/owner/repo/blob/main/x.txt",
        },
    }
    from strands_pack import github

    res = github(action="get_file_contents", repo="owner/repo", path="x.txt", ref="main")
    assert res["success"] is True
    assert res["text"].startswith("hello")


@patch("strands_pack.github._make_request")
def test_github_create_or_update_file_encodes_content(mock_request, mock_env_token):
    """Test create_or_update_file base64 encodes content and uses contents API."""
    calls = []

    def _side_effect(method, endpoint, **kwargs):
        calls.append((method, endpoint, kwargs))
        if method == "GET":
            return {"success": True, "data": {"sha": "oldsha"}}
        return {"success": True, "data": {"commit": {"sha": "csha"}, "content": {"sha": "fsha", "html_url": "u"}}}

    mock_request.side_effect = _side_effect

    from strands_pack import github

    res = github(
        action="create_or_update_file",
        repo="owner/repo",
        path="a.txt",
        content="hi",
        message="msg",
        branch="main",
    )
    assert res["success"] is True
    assert res["commit_sha"] == "csha"
    # Ensure PUT payload contains base64 content
    put_call = [c for c in calls if c[0] == "PUT"][0]
    payload = put_call[2]["json"]
    assert payload["content"] == "aGk="


@patch("strands_pack.github._make_request")
def test_github_close_issue_requires_confirm(mock_request, mock_env_token):
    from strands_pack import github

    res = github(action="close_issue", repo="owner/repo", issue_number=5)
    assert res["success"] is False
    assert "confirm_required" in res

    mock_request.return_value = {"success": True, "data": {"number": 5, "state": "closed", "html_url": "u"}}
    res = github(action="close_issue", repo="owner/repo", issue_number=5, confirm_text="CLOSE_ISSUE owner/repo#5")
    assert res["success"] is True
    assert res["state"] == "closed"


@patch("strands_pack.github._make_request")
def test_github_merge_pr_requires_confirm(mock_request, mock_env_token):
    from strands_pack import github

    res = github(action="merge_pr", repo="owner/repo", pr_number=7)
    assert res["success"] is False
    assert "confirm_required" in res

    mock_request.return_value = {"success": True, "data": {"merged": True, "message": "Merged", "sha": "x"}}
    res = github(action="merge_pr", repo="owner/repo", pr_number=7, confirm_text="MERGE_PR owner/repo#7")
    assert res["success"] is True
    assert res["merged"] is True


@patch("strands_pack.github._make_request")
def test_github_labels_actions(mock_request, mock_env_token):
    from strands_pack import github

    mock_request.return_value = {"success": True, "data": [{"name": "bug"}, {"name": "enhancement"}]}
    res = github(action="set_labels", repo="owner/repo", issue_number=1, labels=["bug", "enhancement"])
    assert res["success"] is True
    assert "bug" in res["labels"]

    mock_request.return_value = {"success": True, "data": [{"name": "bug"}]}
    res = github(action="add_labels", repo="owner/repo", issue_number=1, labels=["bug"])
    assert res["success"] is True

    mock_request.return_value = {"success": True, "data": None}
    res = github(action="remove_label", repo="owner/repo", issue_number=1, label="bug")
    assert res["success"] is True
    assert res["removed"] == "bug"


@patch("strands_pack.github._make_request")
def test_github_delete_file_requires_confirm(mock_request, mock_env_token):
    from strands_pack import github

    res = github(action="delete_file", repo="owner/repo", path="posts/x.md", branch="main", message="rm")
    assert res["success"] is False
    assert "confirm_required" in res


@patch("strands_pack.github._make_request")
def test_github_delete_file_auto_sha_and_delete(mock_request, mock_env_token):
    """delete_file should resolve sha if not provided, then DELETE with the sha."""
    calls = []

    def _side_effect(method, endpoint, **kwargs):
        calls.append((method, endpoint, kwargs))
        if method == "GET":
            return {"success": True, "data": {"sha": "filesha"}}
        if method == "DELETE":
            return {"success": True, "data": {"commit": {"sha": "commitsha"}}}
        return {"success": True, "data": {}}

    mock_request.side_effect = _side_effect

    from strands_pack import github

    res = github(
        action="delete_file",
        repo="owner/repo",
        path="posts/x.md",
        branch="main",
        message="Delete post",
        confirm_text="DELETE_FILE owner/repo:posts/x.md@main",
    )
    assert res["success"] is True
    assert res["commit_sha"] == "commitsha"

    # Verify DELETE payload includes sha + branch + message
    delete_call = [c for c in calls if c[0] == "DELETE"][0]
    payload = delete_call[2]["json"]
    assert payload["sha"] == "filesha"
    assert payload["branch"] == "main"
    assert payload["message"] == "Delete post"
