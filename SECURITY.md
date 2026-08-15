# Security policy

## Secret handling

`DISCORD_BOT_TOKEN` is loaded only from the process environment or a local
`.env` file. The token is excluded from the `Config` representation and is not
logged. Real `.env` files are ignored by Git.

If a token is exposed, reset it immediately in the Discord Developer Portal and
replace the local value.

## Least privilege

Grant the bot only View Channels, Read Message History, and Manage Roles in the
test server. Keep the bot's managed role above the target role but below any
administrative roles. Do not grant Administrator.

Use `--dry-run` before changing roles, and set `DISCORD_CHANNEL_ID` so the bot
does not need access to unrelated channels.

