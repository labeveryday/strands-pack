"""Tests for skills tool."""
import pytest
from pathlib import Path


@pytest.fixture
def skills_dir(tmp_path):
    """Create a temporary skills directory with test skills (Anthropic format)."""
    skills_path = tmp_path / ".agent-skills"
    skills_path.mkdir()

    # Create task-with-reminder skill (directory-based)
    task_skill = skills_path / "task-with-reminder"
    task_skill.mkdir()
    (task_skill / "Skill.md").write_text("""---
name: Task with Reminder
description: Create a task with Google Tasks and Calendar reminders
dependencies: google_tasks, google_calendar
---

## Overview

Create tasks with reminders using Google Tasks and Calendar.

## Instructions

1. Parse the task title and due date
2. Create task in Google Tasks
3. Create calendar event with reminders
""")
    # Create a script
    scripts_dir = task_skill / "scripts"
    scripts_dir.mkdir()
    (scripts_dir / "create_task.py").write_text("""#!/usr/bin/env python3
def create_task(title, due):
    print(f"Creating task: {title}")
""")

    # Create github-to-social skill (directory-based)
    github_skill = skills_path / "github-to-social"
    github_skill.mkdir()
    (github_skill / "Skill.md").write_text("""---
name: GitHub to Social
description: Announce GitHub releases across social platforms
dependencies: github, discord, linkedin
---

## Overview

Announce releases on Discord and LinkedIn.

## Instructions

1. Get release info from GitHub
2. Post to Discord
3. Post to LinkedIn
""")
    # Create a reference file
    (github_skill / "REFERENCE.md").write_text("""# Reference

Additional documentation for the skill.
""")

    # Create simple skill (directory-based, minimal)
    simple_skill = skills_path / "simple-skill"
    simple_skill.mkdir()
    (simple_skill / "Skill.md").write_text("""---
name: Simple Skill
description: A simple test skill
---

# Simple Skill

Just do the thing.
""")

    # Create flat file skill (backwards compatibility)
    flat_skill = skills_path / "legacy-skill.md"
    flat_skill.write_text("""---
name: Legacy Skill
description: Old-style flat file skill
---

# Legacy

This is a flat file skill for backwards compatibility.
""")

    return skills_path


def test_skills_list(skills_dir):
    """Test listing skills returns index only."""
    from strands_pack.skills import skills

    result = skills(action="list", skills_dir=str(skills_dir))

    assert result["success"] is True
    assert result["action"] == "list"
    assert result["count"] == 4
    assert "task-with-reminder" in result["skills"]
    assert "github-to-social" in result["skills"]
    assert "simple-skill" in result["skills"]
    assert "legacy-skill" in result["skills"]

    # Check index structure
    task = result["skills"]["task-with-reminder"]
    assert task["name"] == "Task with Reminder"
    assert task["description"] == "Create a task with Google Tasks and Calendar reminders"
    assert task["format"] == "directory"
    assert task.get("has_scripts") is True

    github = result["skills"]["github-to-social"]
    assert github["format"] == "directory"
    assert github.get("has_references") is True

    legacy = result["skills"]["legacy-skill"]
    assert legacy["format"] == "file"


def test_skills_list_empty_dir(tmp_path):
    """Test listing skills from empty directory."""
    from strands_pack.skills import skills

    empty_dir = tmp_path / "empty-skills"
    empty_dir.mkdir()

    result = skills(action="list", skills_dir=str(empty_dir))

    assert result["success"] is True
    assert result["count"] == 0
    assert result["skills"] == {}


def test_skills_list_nonexistent_dir(tmp_path):
    """Test listing skills from nonexistent directory."""
    from strands_pack.skills import skills

    result = skills(action="list", skills_dir=str(tmp_path / "does-not-exist"))

    assert result["success"] is True
    assert result["skills"] == {}
    assert "does not exist" in result.get("note", "")


def test_skills_load_directory_skill(skills_dir):
    """Test loading a directory-based skill's full content."""
    from strands_pack.skills import skills

    result = skills(action="load", name="task-with-reminder", skills_dir=str(skills_dir))

    assert result["success"] is True
    assert result["action"] == "load"
    assert result["skill"] == "task-with-reminder"
    assert result["name"] == "Task with Reminder"
    assert result["description"] == "Create a task with Google Tasks and Calendar reminders"
    assert result["dependencies"] == "google_tasks, google_calendar"
    assert result["format"] == "directory"
    assert "## Overview" in result["content"]
    assert "Google Tasks" in result["content"]
    assert "scripts" in result
    assert "create_task.py" in result["scripts"]


def test_skills_load_with_references(skills_dir):
    """Test loading a skill with reference files."""
    from strands_pack.skills import skills

    result = skills(
        action="load",
        name="github-to-social",
        include_references=True,
        skills_dir=str(skills_dir)
    )

    assert result["success"] is True
    assert "references" in result
    assert "REFERENCE.md" in result["references"]
    assert "Additional documentation" in result["references"]["REFERENCE.md"]


def test_skills_load_flat_file_skill(skills_dir):
    """Test loading a flat file skill (backwards compatibility)."""
    from strands_pack.skills import skills

    result = skills(action="load", name="legacy-skill", skills_dir=str(skills_dir))

    assert result["success"] is True
    assert result["skill"] == "legacy-skill"
    assert result["name"] == "Legacy Skill"
    assert result["format"] == "file"
    assert "flat file skill" in result["content"]


def test_skills_load_minimal_frontmatter(skills_dir):
    """Test loading a skill with minimal frontmatter."""
    from strands_pack.skills import skills

    result = skills(action="load", name="simple-skill", skills_dir=str(skills_dir))

    assert result["success"] is True
    assert result["name"] == "Simple Skill"
    assert result["description"] == "A simple test skill"
    assert result["dependencies"] == ""


def test_skills_load_not_found(skills_dir):
    """Test loading a nonexistent skill."""
    from strands_pack.skills import skills

    result = skills(action="load", name="nonexistent", skills_dir=str(skills_dir))

    assert result["success"] is False
    assert "not found" in result["error"].lower()


def test_skills_load_missing_name(skills_dir):
    """Test load action without name parameter."""
    from strands_pack.skills import skills

    result = skills(action="load", skills_dir=str(skills_dir))

    assert result["success"] is False
    assert "name is required" in result["error"]


def test_skills_list_scripts(skills_dir):
    """Test listing scripts in a skill."""
    from strands_pack.skills import skills

    result = skills(action="list_scripts", name="task-with-reminder", skills_dir=str(skills_dir))

    assert result["success"] is True
    assert result["action"] == "list_scripts"
    assert result["skill"] == "task-with-reminder"
    assert len(result["scripts"]) == 1
    assert result["scripts"][0]["name"] == "create_task.py"


def test_skills_list_scripts_no_scripts(skills_dir):
    """Test listing scripts for skill without scripts."""
    from strands_pack.skills import skills

    result = skills(action="list_scripts", name="github-to-social", skills_dir=str(skills_dir))

    assert result["success"] is True
    assert result["scripts"] == []


def test_skills_read_script(skills_dir):
    """Test reading a script file."""
    from strands_pack.skills import skills

    result = skills(
        action="read_script",
        name="task-with-reminder",
        script="create_task.py",
        skills_dir=str(skills_dir)
    )

    assert result["success"] is True
    assert result["action"] == "read_script"
    assert result["script"] == "create_task.py"
    assert "def create_task" in result["content"]


def test_skills_read_script_not_found(skills_dir):
    """Test reading nonexistent script."""
    from strands_pack.skills import skills

    result = skills(
        action="read_script",
        name="task-with-reminder",
        script="nonexistent.py",
        skills_dir=str(skills_dir)
    )

    assert result["success"] is False
    assert "not found" in result["error"].lower()


def test_skills_read_script_missing_params(skills_dir):
    """Test read_script without required params."""
    from strands_pack.skills import skills

    result = skills(action="read_script", skills_dir=str(skills_dir))
    assert result["success"] is False
    assert "name is required" in result["error"]

    result = skills(action="read_script", name="task-with-reminder", skills_dir=str(skills_dir))
    assert result["success"] is False
    assert "script is required" in result["error"]


def test_skills_read_resource(skills_dir):
    """Test reading a resource file."""
    from strands_pack.skills import skills

    # Create a resource
    resource_dir = skills_dir / "task-with-reminder" / "resources"
    resource_dir.mkdir()
    (resource_dir / "config.json").write_text('{"key": "value"}')

    result = skills(
        action="read_resource",
        name="task-with-reminder",
        resource="config.json",
        skills_dir=str(skills_dir)
    )

    assert result["success"] is True
    assert result["action"] == "read_resource"
    assert result["resource"] == "config.json"
    assert '"key"' in result["content"]


def test_skills_read_resource_binary(skills_dir):
    """Test reading a binary resource returns path."""
    from strands_pack.skills import skills

    # Create a binary resource
    resource_dir = skills_dir / "task-with-reminder" / "resources"
    resource_dir.mkdir(exist_ok=True)
    (resource_dir / "image.png").write_bytes(b'\x89PNG\r\n\x1a\n')

    result = skills(
        action="read_resource",
        name="task-with-reminder",
        resource="image.png",
        skills_dir=str(skills_dir)
    )

    assert result["success"] is True
    assert "path" in result
    assert "content" not in result
    assert "Binary file" in result.get("note", "")


def test_skills_invalid_action():
    """Test invalid action returns error."""
    from strands_pack.skills import skills

    result = skills(action="invalid")

    assert result["success"] is False
    assert "Unknown action" in result["error"]
    assert "available_actions" in result


def test_skills_default_dir(monkeypatch, tmp_path):
    """Test default skills directory from environment."""
    from strands_pack.skills import skills

    # Create skills in custom dir
    custom_dir = tmp_path / "custom-skills"
    custom_dir.mkdir()
    skill_dir = custom_dir / "env-test"
    skill_dir.mkdir()
    (skill_dir / "Skill.md").write_text("""---
name: Env Test
description: Test skill from env
---
# Test
""")

    monkeypatch.setenv("SKILLS_DIR", str(custom_dir))

    result = skills(action="list")

    assert result["success"] is True
    assert "env-test" in result["skills"]


def test_skills_frontmatter_parsing():
    """Test frontmatter parsing function directly."""
    from strands_pack.skills import _parse_frontmatter

    content = """---
name: Test Skill
description: Test description
dependencies: tool_a, tool_b
---

## Overview

Body text here.
"""
    frontmatter, body = _parse_frontmatter(content)

    assert frontmatter["name"] == "Test Skill"
    assert frontmatter["description"] == "Test description"
    assert frontmatter["dependencies"] == "tool_a, tool_b"
    assert "## Overview" in body


def test_skills_frontmatter_parsing_no_frontmatter():
    """Test parsing content without frontmatter."""
    from strands_pack.skills import _parse_frontmatter

    content = """# Just Content

No frontmatter here.
"""
    frontmatter, body = _parse_frontmatter(content)

    assert frontmatter == {}
    assert "# Just Content" in body


def test_skills_directory_priority_over_flat(skills_dir):
    """Test that directory-based skills take priority over flat files with same name."""
    from strands_pack.skills import skills

    # Create both directory and flat file with same name
    dir_skill = skills_dir / "duplicate"
    dir_skill.mkdir()
    (dir_skill / "Skill.md").write_text("""---
name: Directory Version
description: From directory
---
Directory content
""")
    (skills_dir / "duplicate.md").write_text("""---
name: Flat Version
description: From flat file
---
Flat content
""")

    result = skills(action="list", skills_dir=str(skills_dir))

    # Directory version should win
    assert result["skills"]["duplicate"]["name"] == "Directory Version"
    assert result["skills"]["duplicate"]["format"] == "directory"
