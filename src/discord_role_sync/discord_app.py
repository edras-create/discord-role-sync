from __future__ import annotations

import asyncio
import logging

import discord

from .config import Config
from .core import collect_candidates, synchronize_role
from .models import SyncSummary


class DiscordRoleSyncError(RuntimeError):
    """Friendly runtime error suitable for CLI output."""


class DiscordRoleSyncClient(discord.Client):
    def __init__(self, config: Config, logger: logging.Logger) -> None:
        intents = discord.Intents.none()
        intents.guilds = True
        super().__init__(intents=intents)
        self.config = config
        self.logger = logger
        self.summary: SyncSummary | None = None
        self.failure: BaseException | None = None
        self._executing = False

    async def on_ready(self) -> None:
        if self._executing:
            return
        self._executing = True
        try:
            self.summary = await self._execute_once()
        except BaseException as exc:
            self.failure = exc
        finally:
            await self.close()

    async def _execute_once(self) -> SyncSummary:
        if self.user is None:
            raise DiscordRoleSyncError("Discord login succeeded without a bot user")

        guild = self.get_guild(self.config.server_id)
        if guild is None:
            raise DiscordRoleSyncError(
                "Server not found. Check DISCORD_SERVER_ID and confirm the bot is invited."
            )

        role = guild.get_role(self.config.role_id)
        if role is None:
            raise DiscordRoleSyncError("Role not found in the configured server")
        self._validate_role_permissions(guild, role)

        message = await self._find_message(guild)
        candidates = await collect_candidates(message, self.config.source)
        self.logger.info(
            "MATCHED users=%s source=%s message=%s",
            len(candidates),
            self.config.source.value,
            self.config.message_id,
        )

        summary = await synchronize_role(
            guild=guild,
            role=role,
            candidates=candidates,
            action=self.config.action,
            dry_run=self.config.dry_run,
            logger=self.logger,
        )
        self.logger.info(
            "SUMMARY matched=%s changed=%s would_change=%s skipped=%s failed=%s dry_run=%s",
            summary.matched,
            summary.changed,
            summary.would_change,
            summary.skipped,
            summary.failed,
            self.config.dry_run,
        )
        return summary

    def _validate_role_permissions(self, guild: discord.Guild, role: discord.Role) -> None:
        bot_member = guild.get_member(self.user.id) if self.user is not None else None
        if bot_member is None:
            raise DiscordRoleSyncError("Could not resolve the bot member in the server")
        if not bot_member.guild_permissions.manage_roles:
            raise DiscordRoleSyncError("The bot needs the Manage Roles permission")
        if role.is_default() or role.managed:
            raise DiscordRoleSyncError("The target role is managed by Discord and cannot be edited")
        if role >= bot_member.top_role:
            raise DiscordRoleSyncError(
                "Move the bot's role above the target role in Server Settings > Roles"
            )

    async def _find_message(self, guild: discord.Guild) -> discord.Message:
        if self.config.channel_id is not None:
            channel = guild.get_channel(self.config.channel_id)
            if channel is None or not hasattr(channel, "fetch_message"):
                raise DiscordRoleSyncError("Configured channel was not found or is unsupported")
            try:
                return await channel.fetch_message(self.config.message_id)
            except discord.NotFound as exc:
                raise DiscordRoleSyncError(
                    "Message was not found in the configured channel"
                ) from exc
            except discord.Forbidden as exc:
                raise DiscordRoleSyncError(
                    "The bot cannot view the channel or read its message history"
                ) from exc

        self.logger.info("CHANNEL_SCAN started reason=DISCORD_CHANNEL_ID_not_set")
        forbidden_channels = 0
        for channel in guild.text_channels:
            try:
                return await channel.fetch_message(self.config.message_id)
            except discord.NotFound:
                continue
            except discord.Forbidden:
                forbidden_channels += 1
                continue
            except discord.HTTPException as exc:
                self.logger.warning("CHANNEL_SCAN channel=%s error=%s", channel.id, exc)

        detail = (
            f"; {forbidden_channels} channel(s) were not readable" if forbidden_channels else ""
        )
        raise DiscordRoleSyncError(
            "Message was not found in accessible text channels. Set DISCORD_CHANNEL_ID" + detail
        )


async def run_sync(config: Config, logger: logging.Logger) -> SyncSummary:
    client = DiscordRoleSyncClient(config, logger)
    try:
        await client.start(config.token)
    except discord.LoginFailure as exc:
        raise DiscordRoleSyncError("Discord rejected DISCORD_BOT_TOKEN") from exc
    except discord.PrivilegedIntentsRequired as exc:
        raise DiscordRoleSyncError(
            "Discord requires an intent that is disabled for this bot"
        ) from exc
    finally:
        if not client.is_closed():
            await client.close()

    if client.failure is not None:
        if isinstance(client.failure, DiscordRoleSyncError):
            raise client.failure
        raise DiscordRoleSyncError(str(client.failure)) from client.failure
    if client.summary is None:
        raise DiscordRoleSyncError("The bot disconnected before synchronization completed")
    return client.summary


def run(config: Config, logger: logging.Logger) -> SyncSummary:
    return asyncio.run(run_sync(config, logger))
