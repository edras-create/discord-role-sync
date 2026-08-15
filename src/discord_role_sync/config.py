from __future__ import annotations

import argparse
import os
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field

from .models import Action, SourceMode


class ConfigError(ValueError):
    """Raised when CLI or environment configuration is invalid."""


@dataclass(frozen=True, slots=True)
class Config:
    token: str = field(repr=False)
    server_id: int
    message_id: int
    role_id: int
    action: Action
    channel_id: int | None = None
    source: SourceMode = SourceMode.AUTO
    dry_run: bool = False


def _first(cli_value: str | None, env: Mapping[str, str], env_name: str) -> str | None:
    return cli_value if cli_value is not None else env.get(env_name)


def _snowflake(value: str | None, label: str, *, required: bool = True) -> int | None:
    if value is None or not value.strip():
        if required:
            raise ConfigError(f"{label} is required")
        return None
    try:
        parsed = int(value)
    except ValueError as exc:
        raise ConfigError(f"{label} must be a positive integer Discord ID") from exc
    if parsed <= 0:
        raise ConfigError(f"{label} must be a positive integer Discord ID")
    return parsed


def _boolean(value: str | None, label: str, *, default: bool = False) -> bool:
    if value is None:
        return default
    normalized = value.strip().lower()
    if normalized in {"1", "true", "yes", "on"}:
        return True
    if normalized in {"0", "false", "no", "off"}:
        return False
    raise ConfigError(f"{label} must be true or false")


def _enum(value: str | None, enum_type: type[Action] | type[SourceMode], label: str):
    if value is None:
        raise ConfigError(f"{label} is required")
    try:
        if enum_type is Action:
            return Action(value.strip().upper())
        return SourceMode(value.strip().lower())
    except ValueError as exc:
        allowed = ", ".join(item.value for item in enum_type)
        raise ConfigError(f"{label} must be one of: {allowed}") from exc


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="discord-role-sync",
        description=(
            "Add or remove one Discord role for users who reacted to a message "
            "or voted in its native poll. The program exits after one run."
        ),
    )
    parser.add_argument("--server-id", help="Discord server/guild ID")
    parser.add_argument("--message-id", help="Discord message ID")
    parser.add_argument("--role-id", help="Discord role ID")
    parser.add_argument("--channel-id", help="Discord channel ID (recommended)")
    parser.add_argument("--action", choices=["ADD", "REMOVE", "add", "remove"])
    parser.add_argument("--source", choices=[item.value for item in SourceMode])
    parser.add_argument(
        "--dry-run",
        action="store_true",
        default=None,
        help="Show intended changes without modifying roles",
    )
    return parser


def load_config(
    argv: Sequence[str] | None = None,
    environ: Mapping[str, str] | None = None,
) -> Config:
    env = os.environ if environ is None else environ
    args = build_parser().parse_args(argv)

    token = env.get("DISCORD_BOT_TOKEN", "").strip()
    if not token:
        raise ConfigError("DISCORD_BOT_TOKEN is required and must be set in the environment")

    server_id = _snowflake(_first(args.server_id, env, "DISCORD_SERVER_ID"), "server ID")
    message_id = _snowflake(_first(args.message_id, env, "DISCORD_MESSAGE_ID"), "message ID")
    role_id = _snowflake(_first(args.role_id, env, "DISCORD_ROLE_ID"), "role ID")
    channel_id = _snowflake(
        _first(args.channel_id, env, "DISCORD_CHANNEL_ID"),
        "channel ID",
        required=False,
    )
    action = _enum(_first(args.action, env, "DISCORD_ACTION"), Action, "action")
    source = _enum(
        _first(args.source, env, "DISCORD_SOURCE") or SourceMode.AUTO.value,
        SourceMode,
        "source",
    )
    dry_run_value = "true" if args.dry_run else env.get("DISCORD_DRY_RUN")
    dry_run = _boolean(dry_run_value, "DISCORD_DRY_RUN")

    return Config(
        token=token,
        server_id=server_id,
        message_id=message_id,
        role_id=role_id,
        action=action,
        channel_id=channel_id,
        source=source,
        dry_run=dry_run,
    )
