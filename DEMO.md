# Demo checklist

This is a suggested 2–4 minute recording that proves the script works in a test
server without exposing the bot token.

1. Show a test server with:
   - a role named `Verified Reactor`,
   - the bot's role above it,
   - a message with reactions from at least two non-bot users,
   - one user who already has `Verified Reactor`.
2. Briefly show `.env.example`, not the real `.env` file.
3. Run `discord-role-sync --dry-run` and show:
   - matched users,
   - planned changes,
   - the already-assigned user being skipped.
4. Run `discord-role-sync` with `DISCORD_ACTION=ADD`.
5. Return to Discord and refresh the member list to show the role was added.
6. Run the command a second time to demonstrate idempotency: all users should
   be skipped because they already have the role.
7. Change `DISCORD_ACTION=REMOVE`, run once more, and show the role was removed.
8. Optional: repeat with a native Discord poll and `DISCORD_SOURCE=poll`.

Before publishing the video, verify that the recording does not reveal the
bot token, private server invites, personal email addresses, or unrelated
Discord messages.

