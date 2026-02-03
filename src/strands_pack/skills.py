"""
Skills Tool

Load and manage reusable Skills following the Anthropic/agentskills.io specification.

Skills are directories containing a Skill.md file with YAML frontmatter and optional
reference files, scripts, and resources.

Directory Structure:
    .agent-skills/
    ├── my-skill/
    │   ├── Skill.md          # Required - main skill file
    │   ├── REFERENCE.md      # Optional - supplemental info
    │   ├── scripts/          # Optional - executable scripts
    │   │   └── run.py
    │   └── resources/        # Optional - images, data, etc.

Skill.md Format:
    ---
    name: My Skill Name
    description: What this skill does and when to use it
    dependencies: python>=3.8, requests>=2.28.0
    ---

    ## Overview
    Instructions for Claude...

Usage Examples:
    from strands import Agent
    from strands_pack import skills

    agent = Agent(tools=[skills])

    # List available skills (returns metadata only - token efficient)
    agent.tool.skills(action="list")

    # Load a skill's full content
    agent.tool.skills(action="load", name="my-skill")

    # Load a skill with reference files
    agent.tool.skills(action="load", name="my-skill", include_references=True)

    # List scripts in a skill
    agent.tool.skills(action="list_scripts", name="my-skill")

    # Read a specific script
    agent.tool.skills(action="read_script", name="my-skill", script="run.py")

Environment Variables:
    SKILLS_DIR: Default skills directory (default: ~/.agent-skills)
"""

import os
import re
from pathlib import Path
from typing import Any, Dict, List, Optional

from strands import tool

try:
    import yaml
    HAS_YAML = True
except ImportError:
    yaml = None
    HAS_YAML = False


DEFAULT_SKILLS_DIR = "~/.agent-skills"


def _ok(**data: Any) -> Dict[str, Any]:
    out: Dict[str, Any] = {"success": True}
    out.update(data)
    return out


def _err(message: str, **data: Any) -> Dict[str, Any]:
    out: Dict[str, Any] = {"success": False, "error": message}
    out.update(data)
    return out


def _get_skills_dir(skills_dir: Optional[str] = None) -> Path:
    """Get the skills directory path."""
    if skills_dir:
        return Path(skills_dir).expanduser()
    return Path(os.environ.get("SKILLS_DIR", DEFAULT_SKILLS_DIR)).expanduser()


def _parse_frontmatter(content: str) -> tuple[Dict[str, Any], str]:
    """
    Parse YAML frontmatter from markdown content.
    Returns (frontmatter_dict, body_content)
    """
    pattern = r'^---\s*\n(.*?)\n---\s*\n(.*)$'
    match = re.match(pattern, content, re.DOTALL)

    if not match:
        return {}, content

    frontmatter_str = match.group(1)
    body = match.group(2)

    if HAS_YAML:
        try:
            frontmatter = yaml.safe_load(frontmatter_str) or {}
        except Exception:
            frontmatter = {}
    else:
        # Simple fallback parsing
        frontmatter = {}
        for line in frontmatter_str.split('\n'):
            if ':' in line and not line.strip().startswith('-'):
                key, value = line.split(':', 1)
                frontmatter[key.strip()] = value.strip()

    return frontmatter, body


def _scan_skills(skills_dir: Path) -> Dict[str, Dict[str, Any]]:
    """
    Scan skills directory and build index from Skill.md frontmatter.
    Supports both directory-based skills (skill-name/Skill.md) and
    flat files (skill-name.md) for backwards compatibility.
    """
    index = {}

    if not skills_dir.exists():
        return index

    # Scan for directory-based skills (Anthropic format)
    for path in skills_dir.iterdir():
        if path.is_dir():
            skill_md = path / "Skill.md"
            if skill_md.exists():
                name = path.name
                try:
                    content = skill_md.read_text(encoding="utf-8")
                    frontmatter, _ = _parse_frontmatter(content)

                    # Check for reference files
                    has_references = any(
                        f.suffix == '.md' and f.name != 'Skill.md'
                        for f in path.iterdir() if f.is_file()
                    )

                    # Check for scripts
                    scripts_dir = path / "scripts"
                    has_scripts = scripts_dir.exists() and any(scripts_dir.iterdir())

                    # Check for resources
                    resources_dir = path / "resources"
                    has_resources = resources_dir.exists() and any(resources_dir.iterdir())

                    index[name] = {
                        "name": frontmatter.get("name", name),
                        "description": frontmatter.get("description", ""),
                        "dependencies": frontmatter.get("dependencies", ""),
                        "path": str(path),
                        "format": "directory",
                        "has_references": has_references,
                        "has_scripts": has_scripts,
                        "has_resources": has_resources,
                    }
                except Exception:
                    continue

    # Also scan for flat .md files (backwards compatibility)
    for path in skills_dir.glob("*.md"):
        name = path.stem
        if name not in index:  # Don't override directory-based skills
            try:
                content = path.read_text(encoding="utf-8")
                frontmatter, _ = _parse_frontmatter(content)

                # Support both old 'triggers' and new 'description' format
                description = frontmatter.get("description", "")

                index[name] = {
                    "name": frontmatter.get("name", name),
                    "description": description,
                    "dependencies": frontmatter.get("dependencies", ""),
                    "path": str(path),
                    "format": "file",
                    "has_references": False,
                    "has_scripts": False,
                    "has_resources": False,
                }
            except Exception:
                continue

    return index


def _load_skill(name: str, skills_dir: Path, include_references: bool = False) -> Dict[str, Any]:
    """Load full skill content."""

    # Check for directory-based skill first
    skill_path = skills_dir / name
    if skill_path.is_dir():
        skill_md = skill_path / "Skill.md"
        if not skill_md.exists():
            return _err(f"Skill directory exists but missing Skill.md: {name}")

        try:
            content = skill_md.read_text(encoding="utf-8")
            frontmatter, body = _parse_frontmatter(content)

            result = _ok(
                action="load",
                skill=name,
                name=frontmatter.get("name", name),
                description=frontmatter.get("description", ""),
                dependencies=frontmatter.get("dependencies", ""),
                content=body.strip(),
                format="directory",
                path=str(skill_path),
            )

            # Include reference files if requested
            if include_references:
                references = {}
                for f in skill_path.iterdir():
                    if f.is_file() and f.suffix == '.md' and f.name != 'Skill.md':
                        try:
                            references[f.name] = f.read_text(encoding="utf-8")
                        except Exception:
                            pass
                if references:
                    result["references"] = references

            # List available scripts
            scripts_dir = skill_path / "scripts"
            if scripts_dir.exists():
                scripts = [f.name for f in scripts_dir.iterdir() if f.is_file()]
                if scripts:
                    result["scripts"] = scripts

            # List available resources
            resources_dir = skill_path / "resources"
            if resources_dir.exists():
                resources = [f.name for f in resources_dir.iterdir() if f.is_file()]
                if resources:
                    result["resources"] = resources

            return result

        except Exception as e:
            return _err(f"Failed to load skill: {e}", skill=name)

    # Fall back to flat file
    flat_path = skills_dir / f"{name}.md"
    if flat_path.exists():
        try:
            content = flat_path.read_text(encoding="utf-8")
            frontmatter, body = _parse_frontmatter(content)

            return _ok(
                action="load",
                skill=name,
                name=frontmatter.get("name", name),
                description=frontmatter.get("description", ""),
                dependencies=frontmatter.get("dependencies", ""),
                content=body.strip(),
                format="file",
                path=str(flat_path),
            )
        except Exception as e:
            return _err(f"Failed to load skill: {e}", skill=name)

    return _err(f"Skill not found: {name}", skill=name)


def _list_scripts(name: str, skills_dir: Path) -> Dict[str, Any]:
    """List scripts in a skill."""
    skill_path = skills_dir / name

    if not skill_path.is_dir():
        return _err(f"Skill not found or not a directory: {name}")

    scripts_dir = skill_path / "scripts"
    if not scripts_dir.exists():
        return _ok(action="list_scripts", skill=name, scripts=[])

    scripts = []
    for f in scripts_dir.iterdir():
        if f.is_file():
            scripts.append({
                "name": f.name,
                "path": str(f),
                "size": f.stat().st_size,
            })

    return _ok(action="list_scripts", skill=name, scripts=scripts)


def _read_script(name: str, script: str, skills_dir: Path) -> Dict[str, Any]:
    """Read a script file from a skill."""
    skill_path = skills_dir / name

    if not skill_path.is_dir():
        return _err(f"Skill not found or not a directory: {name}")

    script_path = skill_path / "scripts" / script
    if not script_path.exists():
        return _err(f"Script not found: {script}", skill=name)

    try:
        content = script_path.read_text(encoding="utf-8")
        return _ok(
            action="read_script",
            skill=name,
            script=script,
            content=content,
            path=str(script_path),
        )
    except Exception as e:
        return _err(f"Failed to read script: {e}", skill=name, script=script)


def _read_resource(name: str, resource: str, skills_dir: Path) -> Dict[str, Any]:
    """Read a resource file from a skill (returns path for binary files)."""
    skill_path = skills_dir / name

    if not skill_path.is_dir():
        return _err(f"Skill not found or not a directory: {name}")

    resource_path = skill_path / "resources" / resource
    if not resource_path.exists():
        return _err(f"Resource not found: {resource}", skill=name)

    # For text files, return content; for binary, return path
    text_extensions = {'.txt', '.md', '.json', '.yaml', '.yml', '.csv', '.xml', '.html'}

    if resource_path.suffix.lower() in text_extensions:
        try:
            content = resource_path.read_text(encoding="utf-8")
            return _ok(
                action="read_resource",
                skill=name,
                resource=resource,
                content=content,
                path=str(resource_path),
            )
        except Exception:
            pass

    # Return path for binary files
    return _ok(
        action="read_resource",
        skill=name,
        resource=resource,
        path=str(resource_path),
        note="Binary file - use path to access",
    )


@tool
def skills(
    action: str,
    name: Optional[str] = None,
    script: Optional[str] = None,
    resource: Optional[str] = None,
    include_references: bool = False,
    skills_dir: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Load and manage reusable Skills following the Anthropic/agentskills.io specification.

    Skills are directories containing a Skill.md file with YAML frontmatter,
    optional reference files, executable scripts, and resources.

    Args:
        action: The action to perform. One of:
            - "list": List available skills (returns metadata only)
            - "load": Load a skill's full content
            - "list_scripts": List scripts in a skill
            - "read_script": Read a script file
            - "read_resource": Read a resource file
        name: Skill name (required for load, list_scripts, read_script, read_resource)
        script: Script filename (required for read_script)
        resource: Resource filename (required for read_resource)
        include_references: Include reference .md files when loading (default False)
        skills_dir: Directory containing skills.
            Defaults to SKILLS_DIR env var or ~/.agent-skills

    Returns:
        dict with success status and action-specific data:
            - list: skills dict with metadata
            - load: skill content, scripts list, resources list
            - list_scripts: list of script files
            - read_script: script content
            - read_resource: resource content or path

    Examples:
        >>> skills(action="list")
        >>> skills(action="load", name="deploy-lambda")
        >>> skills(action="load", name="deploy-lambda", include_references=True)
        >>> skills(action="list_scripts", name="deploy-lambda")
        >>> skills(action="read_script", name="deploy-lambda", script="deploy.py")
    """
    action = (action or "").strip().lower()
    valid_actions = ["list", "load", "list_scripts", "read_script", "read_resource"]

    if action not in valid_actions:
        return _err(f"Unknown action: {action}", available_actions=valid_actions)

    dir_path = _get_skills_dir(skills_dir)

    if action == "list":
        if not dir_path.exists():
            return _ok(
                action="list",
                skills={},
                skills_dir=str(dir_path),
                note=f"Skills directory does not exist: {dir_path}",
            )

        index = _scan_skills(dir_path)

        # Return compact index
        compact = {}
        for skill_name, info in index.items():
            compact[skill_name] = {
                "name": info["name"],
                "description": info["description"],
                "format": info["format"],
            }
            if info.get("has_scripts"):
                compact[skill_name]["has_scripts"] = True
            if info.get("has_references"):
                compact[skill_name]["has_references"] = True

        return _ok(
            action="list",
            skills=compact,
            skills_dir=str(dir_path),
            count=len(compact),
        )

    if action == "load":
        if not name:
            return _err("name is required for load action")
        return _load_skill(name, dir_path, include_references)

    if action == "list_scripts":
        if not name:
            return _err("name is required for list_scripts action")
        return _list_scripts(name, dir_path)

    if action == "read_script":
        if not name:
            return _err("name is required for read_script action")
        if not script:
            return _err("script is required for read_script action")
        return _read_script(name, script, dir_path)

    if action == "read_resource":
        if not name:
            return _err("name is required for read_resource action")
        if not resource:
            return _err("resource is required for read_resource action")
        return _read_resource(name, resource, dir_path)

    return _err(f"Unhandled action: {action}")
