# Google Sheets MCP Server for Claude Code

An MCP server that gives Claude Code direct read/write access to Google Sheets.

## For users

Give Claude this prompt to install:

> Install the Google Sheets MCP skill from https://github.com/irritant-in-residence/google_sheets_claude_skill — follow the INSTALL instructions in the README.

## INSTALL — Instructions for Claude

### Step 1: Clone into skills directory

```bash
git clone https://github.com/irritant-in-residence/google_sheets_claude_skill.git ~/.claude/skills/google_sheets_claude_skill
```

### Step 2: Run the skill

Load and run `/google-sheets`. The skill's own setup instructions will handle everything else — Python checks, dependency installation, Google Cloud project creation, OAuth, MCP server registration, and tool whitelisting.
