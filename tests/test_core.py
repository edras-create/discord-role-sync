import logging

import pytest

from discord_role_sync.core import collect_candidates, synchronize_role
from discord_role_sync.models import Action, Candidate, SourceMode


class AsyncUsers:
    def __init__(self, users):
        self.users_list = users

    def __aiter__(self):
        self._iterator = iter(self.users_list)
        return self

    async def __anext__(self):
        try:
            return next(self._iterator)
        except StopIteration as exc:
            raise StopAsyncIteration from exc


class FakeUser:
    def __init__(self, user_id, name, *, bot=False):
        self.id = user_id
        self.display_name = name
        self.bot = bot


class FakeReaction:
    def __init__(self, users):
        self._users = users

    def users(self, *, limit):
        assert limit is None
        return AsyncUsers(self._users)


class FakeAnswer(FakeReaction):
    def voters(self, *, limit):
        return self.users(limit=limit)


class FakePoll:
    def __init__(self, answers):
        self.answers = answers


class FakeMessage:
    def __init__(self, reactions=(), poll=None):
        self.reactions = reactions
        self.poll = poll


class FakeRole:
    def __init__(self, role_id):
        self.id = role_id


class FakeMember(FakeUser):
    def __init__(self, user_id, name, role_ids=(), *, bot=False, fail=False):
        super().__init__(user_id, name, bot=bot)
        self.roles = [FakeRole(role_id) for role_id in role_ids]
        self.fail = fail
        self.add_calls = 0
        self.remove_calls = 0

    async def add_roles(self, role, *, reason):
        if self.fail:
            raise RuntimeError("simulated failure")
        self.add_calls += 1
        self.roles.append(role)
        assert reason

    async def remove_roles(self, role, *, reason):
        if self.fail:
            raise RuntimeError("simulated failure")
        self.remove_calls += 1
        self.roles = [item for item in self.roles if item.id != role.id]
        assert reason


class FakeGuild:
    def __init__(self, cached=(), fetched=()):
        self.cached = {member.id: member for member in cached}
        self.fetched = {member.id: member for member in fetched}

    def get_member(self, user_id):
        return self.cached.get(user_id)

    async def fetch_member(self, user_id):
        return self.fetched[user_id]


@pytest.mark.asyncio
async def test_collects_and_deduplicates_reactors_and_poll_voters() -> None:
    alice = FakeUser(1, "alice")
    bob = FakeUser(2, "bob")
    bot = FakeUser(3, "robot", bot=True)
    message = FakeMessage(
        reactions=[FakeReaction([alice, bot]), FakeReaction([bob, alice])],
        poll=FakePoll([FakeAnswer([bob]), FakeAnswer([alice, bot])]),
    )

    candidates = await collect_candidates(message, SourceMode.AUTO)

    assert candidates == [Candidate(1, "alice"), Candidate(2, "bob")]


@pytest.mark.asyncio
async def test_source_mode_limits_collection() -> None:
    message = FakeMessage(
        reactions=[FakeReaction([FakeUser(1, "reactor")])],
        poll=FakePoll([FakeAnswer([FakeUser(2, "voter")])]),
    )

    reactors = await collect_candidates(message, SourceMode.REACTIONS)
    voters = await collect_candidates(message, SourceMode.POLL)

    assert [item.user_id for item in reactors] == [1]
    assert [item.user_id for item in voters] == [2]


@pytest.mark.asyncio
async def test_add_is_idempotent_and_continues_after_failure(caplog) -> None:
    role = FakeRole(99)
    needs_role = FakeMember(1, "alice")
    already_has_role = FakeMember(2, "bob", [99])
    failure = FakeMember(3, "carol", fail=True)
    guild = FakeGuild(cached=[needs_role, already_has_role, failure])
    candidates = [Candidate(1, "alice"), Candidate(2, "bob"), Candidate(3, "carol")]

    summary = await synchronize_role(
        guild=guild,
        role=role,
        candidates=candidates,
        action=Action.ADD,
        dry_run=False,
        logger=logging.getLogger("test-add"),
    )

    assert needs_role.add_calls == 1
    assert already_has_role.add_calls == 0
    assert summary.matched == 3
    assert summary.changed == 1
    assert summary.skipped == 1
    assert summary.failed == 1
    assert summary.exit_code == 1


@pytest.mark.asyncio
async def test_remove_fetches_uncached_member() -> None:
    role = FakeRole(99)
    member = FakeMember(1, "alice", [99])
    guild = FakeGuild(fetched=[member])

    summary = await synchronize_role(
        guild=guild,
        role=role,
        candidates=[Candidate(1, "alice")],
        action=Action.REMOVE,
        dry_run=False,
        logger=logging.getLogger("test-remove"),
    )

    assert member.remove_calls == 1
    assert summary.changed == 1
    assert summary.exit_code == 0


@pytest.mark.asyncio
async def test_dry_run_makes_no_changes() -> None:
    role = FakeRole(99)
    member = FakeMember(1, "alice")
    guild = FakeGuild(cached=[member])

    summary = await synchronize_role(
        guild=guild,
        role=role,
        candidates=[Candidate(1, "alice")],
        action=Action.ADD,
        dry_run=True,
        logger=logging.getLogger("test-dry-run"),
    )

    assert member.add_calls == 0
    assert summary.changed == 0
    assert summary.would_change == 1
