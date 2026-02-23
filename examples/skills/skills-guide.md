# Skills Guide

## What Are Skills?

Skills are reusable instructions that extend an agent's capabilities. When you invoke a skill, the agent loads the instructions and follows them for your request.

Think of skills as **saved prompts** that you can call anytime.

---

## Using the Skills Tool

The `skills` tool provides token-efficient skill management:

```python
from strands_pack import skills

# List available skills (returns index only - minimal tokens)
skills(action="list")

# Load a skill's full content
skills(action="load", name="add-task")

# Match user input to a skill based on triggers
skills(action="match", input="remind me to call mom tomorrow")
```

---

## Creating a Skill

Skills are markdown files with YAML frontmatter:

```markdown
---
description: Brief description (shown in list)
triggers:
  - phrase that activates this skill
  - another trigger phrase
---

# Skill Name

Full instructions for the agent to follow.

## Instructions

Step-by-step instructions for Agent to follow.

## Output Format

How Agent should structure the response.

## Examples (optional)

Show input/output examples to guide behavior.
```

### Key Points

- **description**: Shown in `list` action (keep it short)
- **triggers**: Phrases that suggest this skill should be used
- **Content**: Full instructions loaded only when needed

---

## Skill File Location

Default: `~/.agent-skills/`

Override with `SKILLS_DIR` environment variable or `skills_dir` parameter.

```
~/.agent-skills/
├── add-task.md
├── daily-tasks.md
├── code-review.md
└── blog-post.md
```

---

## Skill File Naming

| Convention | Example | Skill Name |
|------------|---------|------------|
| Kebab-case | `code-review.md` | `code-review` |
| Lowercase | `lint.md` | `lint` |
| Descriptive | `aws-l7-writing.md` | `aws-l7-writing` |

The filename (minus `.md`) becomes the skill name.

---

## Token Efficiency

The skills tool is designed for minimal token usage:

| Action | Tokens | What's Loaded |
|--------|--------|---------------|
| `list` | ~50 | Names + descriptions only |
| `match` | ~50 | Trigger matching, no content |
| `load` | ~200-500 | Full skill content |

Agent workflow:
1. System prompt includes: "Skills available. Use `skills(action='list')` to see them."
2. Agent matches user request to skill via triggers
3. Agent loads full content only when needed

---

## Example Skills

### Example 1: Add Task with Reminders

**File:** `~/.agent-skills/add-task.md`

```markdown
---
description: Create task with reminders via Google Tasks + Calendar
triggers:
  - remind me
  - add task
  - todo
---

# Add Task

Create a task with reminder across Google Tasks and Calendar.

## Instructions

1. Parse the task title and due date from user input
2. Create task in Google Tasks
3. Create calendar event with reminders

## Output Format

✅ **Task created:** <title>
📅 **Due:** <date/time>
🔔 **Reminders:** <list>
```

---

### Example 2: Daily Tasks Review

**File:** `~/.agent-skills/daily-tasks.md`

```markdown
---
description: Show today's tasks and calendar events
triggers:
  - today's tasks
  - daily review
  - what's on my calendar
---

# Daily Tasks

Show my tasks and calendar for today.

## Instructions

1. Get today's tasks from Google Tasks
2. Get today's events from Google Calendar
3. Format and present the combined view

## Output Format

## Today's Tasks
- [ ] Task 1 (due 10am)
- [ ] Task 2 (due 2pm)

## Calendar
- 9:00 AM - Meeting
- 12:00 PM - Lunch
```

---

### Example 3: Code Review

**File:** `~/.agent-skills/code-review.md`

```markdown
---
description: Review code for quality, security, and best practices
triggers:
  - review this code
  - code review
---

# Code Review

Review code for quality, security, and maintainability.

## Checklist

### Security
- [ ] No hardcoded secrets
- [ ] Input validation present

### Quality
- [ ] Functions are single-purpose
- [ ] Variable names are descriptive

## Output Format

### Summary
[One paragraph assessment]

### Issues Found
| Severity | Location | Issue | Suggestion |
|----------|----------|-------|------------|

### Verdict
- [ ] Ready to merge
- [ ] Needs changes
```

---

## Advanced Patterns

### Pattern 1: Level-based output

```yaml
---
description: Flexible analysis depth
triggers:
  - analyze
---
```

```markdown
## Output Levels

If user says "quick": Provide 2-3 bullet summary
If user says "detailed": Provide full analysis
Default: Provide standard analysis
```

### Pattern 2: Tool-specific instructions

Include actual tool calls in your skill:

```markdown
## Instructions

1. Use the github tool to get PR details:
   \`\`\`python
   github(action="get_pr", repo="owner/repo", pr_number=123, include_files=True)
   \`\`\`

2. Analyze the changes...
```

### Pattern 3: Checklists with status

```markdown
## Review Checklist

For each item, mark as:
- ✅ Pass - meets criteria
- ⚠️ Warning - minor issues
- ❌ Fail - needs attention
```

---

## Tips for Effective Skills

### Do:
- Keep descriptions short (shown in list)
- Use specific triggers (avoid generic words)
- Include actual tool calls in instructions
- Define clear output format
- Test the skill before relying on it

### Don't:
- Make skills too broad/generic
- Use triggers that overlap with other skills
- Skip the output format section
- Include large examples (wastes tokens when loaded)

---

## Agent Integration

Add skills to your agent:

```python
from strands import Agent
from strands_pack import skills, google_tasks, google_calendar

# Include skills tool + any tools your skills use
agent = Agent(tools=[skills, google_tasks, google_calendar])

# Agent can now:
# 1. List available skills
# 2. Match user input to skills
# 3. Load and follow skill instructions
```
