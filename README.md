# Discord Role Sync

A safe, one-shot command-line tool that adds or removes a Discord role for every
non-bot user who reacted to a specific message or voted in its native Discord
poll. It logs in, performs one synchronization, prints a per-user audit log,
and exits. It is **not** a continuously running bot.

## Features

- Supports `ADD` and `REMOVE` actions.
- Reads classic message reactions, native Discord poll votes, or both.
- Deduplicates users who selected multiple reactions or poll answers.
- Handles users who already have (or do not have) the role without failing.
- Continues processing after an individual member error.
- Supports a no-change `--dry-run` safety mode.
- Keeps the bot token in environment variables and never prints it.
- Scans readable text channels when a channel ID is not supplied.
- Includes automated tests for configuration, collection, idempotency, dry-run,
  member fetching, and partial failure behavior.

## Requirements

- Python 3.11 or newer.
- A Discord application with a bot user.
- The bot invited to the target server with:
  - **View Channels**
  - **Read Message History**
  - **Manage Roles**
- The bot's role placed **above** the role it will add or remove.

The program only reads existing message participation and edits the configured
role. It does not read or respond to ordinary chat content.

## Install

```bash
git clone <your-repository-url>
cd discord-role-sync
python -m venv .venv
```

Activate the virtual environment:

```bash
# macOS/Linux
source .venv/bin/activate

# Windows PowerShell
.venv\Scripts\Activate.ps1
```

Install the package:

```bash
python -m pip install -e .
```

## Discord setup

1. Open the Discord Developer Portal and create an application.
2. Add a bot to the application and copy its token.
3. In **OAuth2 > URL Generator**, select the `bot` scope and the three
   permissions listed above, then use the generated URL to invite it.
4. In **Server Settings > Roles**, move the bot role above the target role.
5. Enable Developer Mode in Discord under **User Settings > Advanced**.
6. Right-click the server, message, role, and (recommended) channel to copy IDs.

Do not commit or share the bot token. If it is exposed, reset it immediately in
the Developer Portal.

## Configure

Copy the example file and insert real values:

```bash
cp .env.example .env
```

Required values:

```dotenv
DISCORD_BOT_TOKEN=replace_with_your_bot_token
DISCORD_SERVER_ID=123456789012345678
DISCORD_MESSAGE_ID=123456789012345678
DISCORD_ROLE_ID=123456789012345678
DISCORD_ACTION=ADD
```

Recommended and optional values:

```dotenv
DISCORD_CHANNEL_ID=123456789012345678
DISCORD_SOURCE=auto
DISCORD_DRY_RUN=false
```

`DISCORD_SOURCE` accepts:

- `auto`: combine reaction users and native poll voters.
- `reactions`: only users attached to message reactions.
- `poll`: only voters from native Discord poll answers.

When `DISCORD_CHANNEL_ID` is omitted, the program searches the server's
readable text channels for the configured message. Supplying it is faster and
avoids unnecessary API requests.

## Run

First perform a dry run:

```bash
discord-role-sync --dry-run
```

Then apply the configured action:

```bash
discord-role-sync
```

CLI flags can override IDs, action, or source without editing `.env`:

```bash
discord-role-sync \
  --server-id 123456789012345678 \
  --channel-id 123456789012345678 \
  --message-id 123456789012345678 \
  --role-id 123456789012345678 \
  --action REMOVE \
  --source reactions
```

The token intentionally has no CLI flag so it is less likely to leak through
shell history or process listings.

## Example output

```text
2026-08-15T12:00:00Z INFO MATCHED users=3 source=auto message=123456789012345678
2026-08-15T12:00:00Z INFO SUCCESS action=ADD user=alice id=111 role=999
2026-08-15T12:00:00Z INFO SKIP user=bob id=222 reason=already_has_role
2026-08-15T12:00:01Z INFO SUCCESS action=ADD user=carol id=333 role=999
2026-08-15T12:00:01Z INFO SUMMARY matched=3 changed=2 would_change=0 skipped=1 failed=0 dry_run=False
```

Exit codes:

- `0`: run completed with no per-user failures.
- `1`: Discord/runtime error or one or more member updates failed.
- `2`: invalid or missing configuration.
- `130`: interrupted by the operator.

## Test

```bash
python -m pip install -e '.[dev]'
pytest
ruff check .
```

Tests use local fakes and never contact Discord.

## Operational notes

- A user appearing in several reactions or poll answers is changed once.
- Bot users are ignored.
- `ADD` skips users who already have the role.
- `REMOVE` skips users who do not have the role.
- An individual API failure is logged while remaining users continue.
- Discord rate limiting is handled by `discord.py`.
- Native poll voter retrieval requires `discord.py` 2.5 or newer.

See [DEMO.md](DEMO.md) for a concise end-to-end demonstration checklist.

