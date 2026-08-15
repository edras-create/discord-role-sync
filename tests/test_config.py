import pytest

from discord_role_sync.config import ConfigError, load_config
from discord_role_sync.models import Action, SourceMode

BASE_ENV = {
    "DISCORD_BOT_TOKEN": "secret-value",
    "DISCORD_SERVER_ID": "100",
    "DISCORD_MESSAGE_ID": "200",
    "DISCORD_ROLE_ID": "300",
    "DISCORD_ACTION": "ADD",
}


def test_loads_required_environment_values() -> None:
    config = load_config([], BASE_ENV)
    assert config.server_id == 100
    assert config.message_id == 200
    assert config.role_id == 300
    assert config.action is Action.ADD
    assert config.source is SourceMode.AUTO
    assert config.channel_id is None
    assert config.dry_run is False
    assert "secret-value" not in repr(config)


def test_cli_values_override_environment() -> None:
    config = load_config(
        [
            "--server-id",
            "101",
            "--message-id",
            "201",
            "--role-id",
            "301",
            "--channel-id",
            "401",
            "--action",
            "remove",
            "--source",
            "poll",
            "--dry-run",
        ],
        BASE_ENV,
    )
    assert config.server_id == 101
    assert config.message_id == 201
    assert config.role_id == 301
    assert config.channel_id == 401
    assert config.action is Action.REMOVE
    assert config.source is SourceMode.POLL
    assert config.dry_run is True


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("DISCORD_SERVER_ID", "not-an-id"),
        ("DISCORD_MESSAGE_ID", "0"),
        ("DISCORD_ROLE_ID", "-1"),
        ("DISCORD_ACTION", "CHANGE"),
        ("DISCORD_DRY_RUN", "sometimes"),
    ],
)
def test_rejects_invalid_values(field: str, value: str) -> None:
    env = {**BASE_ENV, field: value}
    with pytest.raises(ConfigError):
        load_config([], env)


def test_requires_token() -> None:
    env = {key: value for key, value in BASE_ENV.items() if key != "DISCORD_BOT_TOKEN"}
    with pytest.raises(ConfigError, match="DISCORD_BOT_TOKEN"):
        load_config([], env)
