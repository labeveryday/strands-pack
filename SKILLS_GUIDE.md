# Skills Guide

Skills are reusable multi-tool workflows that follow the [Anthropic agentskills.io specification](https://agentskills.io). They provide step-by-step instructions for agents to execute complex tasks using strands-pack tools.

## Directory Structure

Skills are stored in `~/.agent-skills` by default (override with `SKILLS_DIR` env var):

```
.agent-skills/
├── task-with-reminder/
│   ├── Skill.md              # Required - main skill file
│   ├── REFERENCE.md          # Optional - supplemental docs
│   ├── scripts/              # Optional - executable scripts
│   │   └── create_task.py
│   └── resources/            # Optional - images, data, etc.
├── github-to-social/
│   └── Skill.md
└── video-content-pipeline/
    └── Skill.md
```

## Skill.md Format

Each skill has a `Skill.md` file with YAML frontmatter:

```markdown
---
name: Task with Reminder
description: Create a task in Google Tasks with calendar reminders
dependencies: google_tasks, google_calendar
---

## Overview

Brief description of what this skill does.

## When to Use

- User says "remind me to..."
- User says "add task..."

## Workflow

### Step 1: Parse the Request
Extract task title, due date, notes from user input.

### Step 2: Create Google Task
```python
google_tasks(
    action="create_task",
    tasklist_id="primary",
    title="<task title>",
    due="<RFC3339 datetime>"
)
```

### Step 3: Create Calendar Event with Reminders
```python
google_calendar(
    action="create_event",
    calendar_id="primary",
    event={
        "summary": "⏰ <task title>",
        "reminders": {
            "overrides": [
                {"method": "popup", "minutes": 0},
                {"method": "email", "minutes": 30}
            ]
        }
    }
)
```

## Output Format

```
✅ Task Created

📋 **Task:** <title>
📅 **Due:** <date>
🔔 **Reminders:** Email + Popup
```
```

### Frontmatter Fields

| Field | Required | Description |
|-------|----------|-------------|
| `name` | Yes | Human-readable skill name |
| `description` | Yes | What the skill does (shown in list) |
| `dependencies` | No | Comma-separated strands-pack tools used |

## Using the Skills Tool

### List Available Skills (Token Efficient)

```python
from strands_pack import skills

# Returns metadata only - doesn't load full content
result = skills(action="list")
# Returns: {skills: {name: {name, description, format, has_scripts}}, count: N}
```

### Load a Skill

```python
# Load full skill content
result = skills(action="load", name="task-with-reminder")
# Returns: {content, dependencies, scripts, resources}

# Include reference files
result = skills(action="load", name="my-skill", include_references=True)
# Returns: {content, references: {"REFERENCE.md": "..."}}
```

### Work with Scripts

```python
# List scripts in a skill
result = skills(action="list_scripts", name="task-with-reminder")
# Returns: {scripts: [{name, path, size}]}

# Read a script
result = skills(action="read_script", name="task-with-reminder", script="create_task.py")
# Returns: {content: "..."}
```

### Work with Resources

```python
# Read a text resource
result = skills(action="read_resource", name="my-skill", resource="config.json")
# Returns: {content: "..."}

# Binary resources return path only
result = skills(action="read_resource", name="my-skill", resource="image.png")
# Returns: {path: "/full/path/to/image.png", note: "Binary file"}
```

## Example Agent

```python
from strands import Agent
from strands_pack import (
    skills,
    google_tasks,
    google_calendar,
    gmail,
    discord,
    github,
)

# Create agent with skills + tools that skills use
agent = Agent(tools=[
    skills,
    google_tasks,
    google_calendar,
    gmail,
    discord,
    github,
])

# The agent can now:
# 1. List available skills
# 2. Load skill instructions when needed
# 3. Execute the workflow using the available tools
response = agent("Remind me to review the PR tomorrow at 10am")
```

## Included Skills

The following skills are included in `.agent-skills/`:

| Skill | Dependencies | Description |
|-------|--------------|-------------|
| task-with-reminder | google_tasks, google_calendar | Create tasks with calendar reminders |
| email-to-tasks | gmail, google_tasks, google_calendar | Convert emails into actionable tasks |
| weekly-productivity-report | google_tasks, google_calendar, gmail | Generate weekly productivity summary |
| github-to-social | github, discord, linkedin | Announce releases on social platforms |
| deploy-and-notify | github, discord, slack, gmail | Notify team about deployments |
| video-content-pipeline | gemini_video, gemini_image, image, carbon | Create video content packages |

## Creating Your Own Skills

1. Create a directory in `~/.agent-skills/` (or your custom skills dir):
   ```bash
   mkdir ~/.agent-skills/my-new-skill
   ```

2. Create `Skill.md` with frontmatter and workflow instructions:
   ```bash
   cat > ~/.agent-skills/my-new-skill/Skill.md << 'EOF'
   ---
   name: My New Skill
   description: Does something useful
   dependencies: tool_a, tool_b
   ---

   ## Workflow

   1. First step
   2. Second step
   EOF
   ```

3. Add scripts or resources as needed:
   ```bash
   mkdir ~/.agent-skills/my-new-skill/scripts
   touch ~/.agent-skills/my-new-skill/scripts/helper.py
   ```

4. Test with the skills tool:
   ```python
   from strands_pack import skills
   result = skills(action="load", name="my-new-skill")
   print(result)
   ```

## Best Practices

1. **Use strands-pack tools as dependencies** - Skills should reference tools from this library
2. **Be specific in descriptions** - Help agents understand when to use the skill
3. **Include code examples** - Show exact tool calls with parameters
4. **Define output format** - Specify what the agent should return to the user
5. **Keep skills focused** - One skill = one workflow
6. **Use scripts for complex logic** - Put reusable code in the scripts/ directory
