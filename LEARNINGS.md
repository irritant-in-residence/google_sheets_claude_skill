# Google Sheets Skill Learnings

> **PREREQUISITE:** Read `~/Library/Mobile Documents/com~apple~CloudDocs/Claude/guides/documentation.md` before editing this file.

---

## Credentials Location

`credentials.json` and `token.json` live in the skill directory on iCloud Drive. Never commit these to git. The iCloud path provides encrypted-at-rest storage and cross-device availability.

## OAuth Consent Screen — Current UI Flow (as of April 2026)

The Google Cloud Console consent screen setup uses a wizard with **Next** buttons (not "Save and Continue"):

1. Click **Get Started** from OAuth Overview
2. App name + User support email → **Next**
3. Audience: select **External** → **Next**
4. Contact information email → **Next**
5. Check **Agree to API Services User Data Policy** → **Continue**
6. Click **Create**

Test users are added separately under **Audience** in the left sidebar after the consent screen is created.

## OAuth Consent Screen — Test Users

Google Cloud projects in "Testing" publishing status require each Google account to be explicitly added as a test user under **Audience** in the left sidebar → **+ Add users**. Without this, auth fails with 403 "Access blocked".

## "Google hasn't verified this app" Warning

After adding a test user, the OAuth flow shows a warning page: "Google hasn't verified this app." Click **Continue** to proceed. This is normal for apps in Testing status.

## OAuth Permissions Grant Screen

After the unverified warning, Google shows a permissions screen: "Claude Sheets wants access to your Google Account — See, edit, create, and delete all your Google Sheets spreadsheets." The button is **Continue** (not "Allow"). This screen comes immediately after the "Google hasn't verified this app" warning — guide the user to expect both screens in sequence.

## OAuth Callback Requires Running Server

`sheets_auth.py --setup` starts a local HTTP server to catch Google's OAuth callback. The script MUST be running before the user clicks through the consent flow. If the script isn't running when Google redirects, Safari shows "Can't Connect to the Server" on `localhost`. Run it via the Bash tool with `run_in_background: true` — do NOT ask the user to type it manually.

After running the script, a "Choose an Account" page appears in the browser. Tell the user: "Select the Google account you used to create the OAuth project." Then guide through the unverified app warning and permissions screens.

## Download JSON for OAuth Client — Full Popup Flow

After creating the OAuth client, a confirmation popup appears with the client ID and secret. Guide the user through every step of the popup:

1. "Click **Download JSON** to save the credentials file."
2. Verify the download completed (check for `~/Downloads/client_secret_*.json`).
3. "Click **OK** to close the popup."

Only then proceed to copy the file into place. Don't skip UI steps — always walk through closing dialogs before moving on.

As of April 2026, the **Download JSON** button on this popup works. If it ever stops working, the fallback is the download icon next to the **Client secret** on the Client ID detail page (under Clients in the left sidebar).

## Token Auto-Refresh

`sheets_auth.py` handles token refresh automatically. The refresh token is long-lived. Re-authentication is only needed if the user revokes access or changes scopes.

## Whitelisting MCP Tools

`claude config add allowedTools` is unreliable — it may trigger an interactive prompt or silently fail. Instead, edit `~/.claude/settings.json` directly using the Edit tool and add the `mcp__google-sheets__*` entries to the `permissions.allow` array.

## Restart Required After MCP Setup

After registering the MCP server (`claude mcp add`) and whitelisting tools, the user must quit Claude Code and restart. The MCP server and new tool permissions aren't picked up mid-session.

## Python 3.10+ Required

The `mcp` Python package requires Python 3.10+. macOS ships with Python 3.9 (`/usr/bin/python3`) which is too old. After installing Python 3.13 from python.org, use `/usr/local/bin/python3` for the MCP server and all skill scripts. The MCP server registration must use the full path to the 3.13 binary.
