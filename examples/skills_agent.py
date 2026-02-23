#!/usr/bin/env python3
"""
Skills Agent Example

Demonstrates the skills tool for loading reusable multi-tool workflow instructions.

Skills follow the Anthropic/agentskills.io specification:
- Directory-based: skill-name/Skill.md
- YAML frontmatter with name, description, dependencies
- Optional scripts/ and resources/ directories

Usage:
    python examples/skills_agent.py

    # Use custom skills directory
    SKILLS_DIR=./my-skills python examples/skills_agent.py

Note:
    When run from the strands-pack project, uses .agent-skills/ in the project root.
    Otherwise uses ~/.agent-skills by default.
    Set SKILLS_DIR environment variable to override.

Example Skills Directory:
    .agent-skills/
    ├── task-with-reminder/
    │   ├── Skill.md           # Main skill file with frontmatter
    │   └── scripts/
    │       └── create_task.py
    ├── github-to-social/
    │   ├── Skill.md
    │   └── REFERENCE.md       # Additional reference docs
    └── video-content-pipeline/
        └── Skill.md
"""

import os
import sys

from pathlib import Path

# Get repo root (parent of examples/)
_repo_root = Path(__file__).resolve().parent.parent

# Change to repo root so secrets/ is found
os.chdir(_repo_root)

# Add src to path for local development
sys.path.insert(0, str(_repo_root / "src"))

# Auto-detect project .agent-skills directory if not set
if "SKILLS_DIR" not in os.environ:
    # Check for .agent-skills in project root (parent of examples/)
    project_skills = Path(__file__).parent.parent / ".agent-skills"
    if project_skills.exists():
        os.environ["SKILLS_DIR"] = str(project_skills)

from strands import Agent
from strands_tools import current_time
from strands_pack import (
    skills,
    # Google tools (commonly used by skills)
    google_tasks,
    google_calendar,
    gmail,
    # Social tools
    discord,
    # GitHub
    github,
    # Media tools
    gemini_video,
    gemini_image,
    image,
    carbon,
    google_auth
)

# System prompt that tells the agent about skills
SYSTEM_PROMPT = """You are a helpful assistant with access to skills - reusable multi-tool workflows.

When the user asks to list skills, use: skills(action="list")
When the user wants to perform a task that matches a skill, first load the skill with: skills(action="load", name="skill-name")

Available skills provide workflows for:
- Task management with reminders
- Email to tasks conversion
- GitHub release announcements
- Deployment notifications
- Video content creation
- Weekly productivity reports

Always check available skills first when the user asks to perform a complex multi-step task.
"""


def main():
    """Run the skills agent."""
    skills_dir = os.environ.get("SKILLS_DIR", "~/.agent-skills")

    # Include the skills tool plus tools that skills commonly use
    agent = Agent(
        system_prompt=SYSTEM_PROMPT,
        tools=[
            skills,
            # Google Suite
            google_tasks,
            google_calendar,
            gmail,
            # Social
            discord,
            # GitHub
            github,
            # Media generation
            gemini_video,
            gemini_image,
            image,
            carbon,
            current_time,
            google_auth,
        ]
    )

    print("=" * 60)
    print("Skills Agent")
    print("=" * 60)
    print("\nThis agent loads and executes reusable multi-tool workflow skills.")
    print(f"\nSkills directory: {skills_dir}")
    print("\nAvailable actions:")
    print("  list           - List available skills (token efficient)")
    print("  load           - Load a skill's full instructions")
    print("  list_scripts   - List executable scripts in a skill")
    print("  read_script    - Read a script file")
    print("  read_resource  - Read a resource file")
    print("\nExample queries:")
    print("  - List my available skills")
    print("  - Load the task-with-reminder skill")
    print("  - Remind me to review PR tomorrow at 10am")
    print("  - Announce the v1.0 release on Discord")
    print("  - Create a video about Python async/await")
    print("\nType 'quit' or 'exit' to end.\n")

    while True:
        try:
            user_input = input("You: ").strip()
            if not user_input:
                continue
            if user_input.lower() in ("quit", "exit", "q"):
                print("Goodbye!")
                break

            response = agent(user_input)
            print(f"\nAgent: {response}\n")

        except KeyboardInterrupt:
            print("\nGoodbye!")
            break
        except Exception as e:
            print(f"\nError: {e}\n")


if __name__ == "__main__":
    main()
