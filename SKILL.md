---
name: google-sheets
description: Access and manage Google Sheets via the Sheets API. Use when reading, writing, appending, or deleting rows/columns in Google Sheets. Covers first-time Google API setup, OAuth, and all CRUD operations.
---

# Google Sheets Skill

Read, write, append, and delete data in Google Sheets via the Google Sheets API v4.

**On load:** Run the pre-flight checks below silently. If all pass, say only "Google Sheets skill ready." If any fail, tell the user what's missing and begin walking through setup starting from the first failing step.

**Skill directory:** `~/.claude/skills/google-sheets/`

**IMPORTANT — Bash invocation rule:** Never start a Bash tool call with a variable assignment (`VAR=...`) or shell keyword (`for`, `if`, `while`). The first token must always be a binary/command.

## Pre-Flight Checks (always run on load)

Run all four checks on load to determine setup state. Run each as a separate Bash tool call (they're independent):

```bash
# 1. python3 3.10+ available? Check common locations for newest version.
python3 --version 2>&1
ls /usr/local/bin/python3* /Library/Frameworks/Python.framework/Versions/*/bin/python3* /opt/homebrew/bin/python3* 2>/dev/null

# 2. Python deps installed? (use the 3.10+ python3 found above; skip if #1 failed)
<python3_path> -c "import googleapiclient; import google_auth_oauthlib; import mcp; print('deps OK')" 2>&1

# 3. credentials.json exists?
ls ~/.claude/skills/google-sheets/credentials.json 2>&1

# 4. token.json exists?
ls ~/.claude/skills/google-sheets/token.json 2>&1
```

**Decision tree:**
- All four pass → say "Google Sheets skill ready." and stop
- python3 missing or only < 3.10 available → start at Step 0 (Install Python 3.13)
- python3 3.10+ present but deps missing → start at Step 1 (Install Python deps)
- token.json exists but deps missing → install deps, then ready
- credentials.json exists but no token.json → start at Step 5 (Authenticate)
- No credentials.json → start at the first failing step

**Python version note:** Use the newest python3 3.10+ found on the system for all commands. The system `/usr/bin/python3` on macOS is often 3.9 (end-of-life) which is too old for the `mcp` package. Prefer `/usr/local/bin/python3` or `/Library/Frameworks/Python.framework/Versions/3.13/bin/python3` if available.

## First-Time Setup

Walk the user through setup starting from the first failing pre-flight check. Open each page in Safari via `osascript` and guide the user through one action at a time.

**Setup conversation style:**
- Give **one instruction at a time** — never dump all steps at once
- Start each instruction with the **action** the user needs to take, then explain why
- Wait for confirmation before proceeding to the next step
- If something goes wrong, ask the user for a screenshot to diagnose

### Step 0: Install Python 3.13

If no python3 is found, or only a version below 3.10 is available (e.g., macOS system Python 3.9). Download and open the official macOS installer from python.org:

```bash
curl -L -o /tmp/python3-installer.pkg "https://www.python.org/ftp/python/3.13.3/python-3.13.3-macos11.pkg"
```

Then open the installer:
```bash
open /tmp/python3-installer.pkg
```

Tell the user: "Click through the installer steps and let me know when it's done."

After the user confirms, verify it worked:
```bash
/usr/local/bin/python3 --version
```

If `/usr/local/bin/python3` isn't found, check `/Library/Frameworks/Python.framework/Versions/3.13/bin/python3` — the installer puts it there and symlinks to `/usr/local/bin/`. If neither works, ask the user to open a new terminal tab and retry (the PATH may need refreshing).

### Step 1: Install Python dependencies

```bash
/usr/local/bin/python3 -m pip install google-api-python-client google-auth-oauthlib google-auth-httplib2 mcp
```

### Step 2: Create a Google Cloud project

Open the project creation page:
```bash
osascript -e 'tell application "Safari" to make new document with properties {URL:"https://console.cloud.google.com/projectcreate"}'
```

The user may need to sign in first. Tell them: "Sign in to Google if prompted, then let me know when you're on the New Project page."

Once on the form: "Type `Claude Sheets` in the Project name field. Leave Organization at its default (or select 'No organization' — setting an organization ties the project to admin policies, which is unnecessary for a personal OAuth client). Click **Create**."

### Step 3: Enable the Google APIs

Enable the Sheets API:
```bash
osascript -e 'tell application "Safari" to set URL of front document to "https://console.cloud.google.com/apis/library/sheets.googleapis.com"'
```

"Click the blue **Enable** button. Let me know when done."

Then enable the Drive API (needed to list available spreadsheets):
```bash
osascript -e 'tell application "Safari" to set URL of front document to "https://console.cloud.google.com/apis/library/drive.googleapis.com"'
```

"Click the blue **Enable** button. Let me know when done."

### Step 4: Create OAuth credentials

#### 4a: Consent screen

```bash
osascript -e 'tell application "Safari" to set URL of front document to "https://console.cloud.google.com/apis/credentials/consent"'
```

Walk through one at a time, waiting for confirmation between each:

1. "Click **Get Started**."
2. "Type `Claude Sheets` for App name, select your email for User support email. Click **Next**."
3. "Select **External** for Audience. Click **Next**."
4. "Enter your email for Contact information. Click **Next**."
5. "Check **Agree to API Services User Data Policy**. Click **Continue**."
6. "Click **Create**."

#### 4b: Add test user

This is required — without a test user, auth fails with 403 "Access blocked."

1. "Click **Audience** in the left sidebar."
2. "Click **+ Add users**, type your Google email, click **Save**."

#### 4c: Create OAuth client ID

1. "Click **Clients** in the left sidebar, then **+ Create Client**."
2. "Set Application type to **Desktop app**, name it `Claude Desktop`, click **Create**."
3. "Click **Download JSON** to save the credentials file."
4. Verify the download: `ls -t ~/Downloads/client_secret_*.json 2>/dev/null | head -1`
5. "Click **OK** to close the popup."

Move the credentials into place:
```bash
cp "$(ls -t ~/Downloads/client_secret_*.json | head -1)" ~/.claude/skills/google-sheets/credentials.json
```

### Step 5: Authenticate

Run the auth script in the background (use `run_in_background: true`) — it starts a local HTTP server to catch Google's OAuth callback and must be running before the user clicks through the consent flow:

```bash
/usr/local/bin/python3 ~/.claude/skills/google-sheets/sheets_auth.py --setup
```

A browser tab opens. Guide the user:

1. "Select the Google account you used to create the OAuth project."
2. "You'll see 'Google hasn't verified this app' — this is normal. Click **Continue**."
3. "The permissions page shows what access Claude Sheets needs. Click **Continue** to grant access."

The script catches the callback and saves `token.json`. Verify: `ls ~/.claude/skills/google-sheets/token.json`

### Step 6: Register MCP server

```bash
claude mcp add --transport stdio google-sheets -- /usr/local/bin/python3 ~/.claude/skills/google-sheets/sheets_mcp.py
```

Verify: `claude mcp list` — should show `google-sheets: ✓ Connected`

### Step 7: Whitelist MCP tools

Add the MCP tools to `~/.claude/settings.json` in the `permissions.allow` array. Use the Edit tool to add them directly — `claude config add` is unreliable for this:

```json
"mcp__google-sheets__read",
"mcp__google-sheets__write",
"mcp__google-sheets__append",
"mcp__google-sheets__delete_rows",
"mcp__google-sheets__delete_cols",
"mcp__google-sheets__info",
"mcp__google-sheets__list_spreadsheets"
```

### Step 8: Set default spreadsheet (optional)

There is no hardcoded default spreadsheet. The user can either:
- Pass `spreadsheet_id` to each MCP tool call
- Set the `GOOGLE_SHEET_ID` environment variable
- Use `list_spreadsheets` to discover available spreadsheets and get their IDs

### Step 9: Restart Claude Code

Tell the user: "Quit Claude Code and restart it. The MCP tools won't be available until the next session."

Setup is complete.

**Security:** `credentials.json` and `token.json` contain secrets. They are `.gitignore`d and should never be committed.

## Available MCP Tools

Once installed, these tools are available as `mcp__google-sheets__<name>`:

| Tool | Description |
|------|-------------|
| `read` | Read data from a sheet. Range uses A1 notation (e.g., `Sheet1!A1:D10`). |
| `write` | Write data to specific cells (overwrite). Values is an array of arrays. |
| `append` | Append rows after existing data. |
| `delete_rows` | Delete rows by 1-indexed row numbers (inclusive). |
| `delete_cols` | Delete columns by 1-indexed column numbers (inclusive). |
| `info` | Show spreadsheet metadata: title, URL, sheets and dimensions. |
| `list_spreadsheets` | List all Google Sheets accessible to the account. Optional search query. |

## Key Concepts

### Range notation
- `Sheet1!A1:D10` — specific rectangle
- `Sheet1!A:D` — entire columns A through D
- `Sheet1!2:5` — entire rows 2 through 5
- `A1:D10` — defaults to the first sheet
- `Sheet1` — entire sheet

### Values format
Always array of arrays: `[["row1col1", "row1col2"], ["row2col1", "row2col2"]]`

### Index conventions
- **Range notation**: 1-indexed, inclusive (`A1` = first cell)
- **MCP tools**: Accept 1-indexed values (as seen in the sheet) and convert internally

### Tips
- **Formulas**: Write as strings starting with `=` (e.g., `"=SUM(A1:A10)"`)
- **Empty cells**: The API omits trailing empty cells in rows. Pad with `""` if needed.
- **Rate limits**: 60 reads/min, 60 writes/min per user. Batch when possible.
- **Large reads**: For sheets with >10K rows, read in chunks rather than all at once.
