"""Tests for the GitHub release check behind /info's "Updates" field.

None of these touch the network: `_fetch_latest_tag` is stubbed so the caching,
comparison, and failure-reporting logic can be asserted directly.
"""

import aiohttp
import pytest

from ticketbot.utils import updates
from ticketbot.utils.updates import UpdateStatus, compare_versions, parse_version


@pytest.fixture(autouse=True)
def clear_update_cache():
    updates.clear_cache()
    yield
    updates.clear_cache()


class TestParseVersion:
    @pytest.mark.parametrize(
        ("raw", "expected"),
        [
            ("4.5.0", (4, 5, 0)),
            ("v4.5.0", (4, 5, 0)),
            ("V4.5.0", (4, 5, 0)),
            ("  4.5.0  ", (4, 5, 0)),
            ("4.5.0-rc1", (4, 5, 0)),
            ("4.5.0+build7", (4, 5, 0)),
            ("5", (5,)),
        ],
    )
    def test_parses_the_shapes_github_tags_use(self, raw, expected):
        assert parse_version(raw) == expected

    @pytest.mark.parametrize("raw", [None, "", "latest", "4.5.x", "release-candidate"])
    def test_returns_none_for_anything_non_numeric(self, raw):
        assert parse_version(raw) is None


class TestCompareVersions:
    @pytest.mark.parametrize(
        ("current", "latest", "expected"),
        [
            ("4.4.0", "4.5.0", -1),
            ("4.4.0", "v4.4.1", -1),
            ("4.4.0", "4.4.0", 0),
            ("4.4.0", "v4.4.0", 0),
            ("4.5.0", "4.4.9", 1),
            # Differing lengths pad with zeros rather than comparing tuple sizes.
            ("4.4", "4.4.0", 0),
            ("4.4", "4.4.1", -1),
            ("4.10.0", "4.9.0", 1),
        ],
    )
    def test_orders_versions(self, current, latest, expected):
        assert compare_versions(current, latest) == expected

    @pytest.mark.parametrize(("current", "latest"), [("4.4.0", "nightly"), ("dev", "4.4.0"), ("4.4.0", None)])
    def test_reports_unknown_rather_than_guessing(self, current, latest):
        assert compare_versions(current, latest) is None


class TestUpdateStatusDescribe:
    def test_flags_an_available_update(self):
        status = UpdateStatus(current="4.4.0", latest="v4.5.0")
        assert status.outdated is True
        assert "4.5.0" in status.describe()
        assert updates.RELEASES_PAGE_URL in status.describe()

    def test_reports_up_to_date(self):
        status = UpdateStatus(current="4.4.0", latest="v4.4.0")
        assert status.outdated is False
        assert status.describe() == "✅ Up to date"

    def test_reports_running_ahead_of_the_latest_release(self):
        status = UpdateStatus(current="4.5.0", latest="v4.4.0")
        assert status.outdated is False
        assert "4.4.0" in status.describe()

    def test_surfaces_the_failure_reason(self):
        status = UpdateStatus(current="4.4.0", error="HTTP 403")
        assert status.outdated is False
        assert "HTTP 403" in status.describe()

    def test_handles_a_repository_with_no_releases(self):
        status = UpdateStatus(current="4.4.0", latest=None)
        assert "No releases" in status.describe()


class TestCheckForUpdates:
    async def test_returns_the_latest_published_tag(self, monkeypatch):
        async def fake_fetch():
            return "v4.5.0"

        monkeypatch.setattr(updates, "_fetch_latest_tag", fake_fetch)
        status = await updates.check_for_updates("4.4.0")
        assert status.latest == "v4.5.0"
        assert status.outdated is True

    async def test_caches_successful_lookups(self, monkeypatch):
        calls = 0

        async def fake_fetch():
            nonlocal calls
            calls += 1
            return "v4.5.0"

        monkeypatch.setattr(updates, "_fetch_latest_tag", fake_fetch)
        await updates.check_for_updates("4.4.0")
        await updates.check_for_updates("4.4.0")
        assert calls == 1

    async def test_force_bypasses_the_cache(self, monkeypatch):
        calls = 0

        async def fake_fetch():
            nonlocal calls
            calls += 1
            return "v4.5.0"

        monkeypatch.setattr(updates, "_fetch_latest_tag", fake_fetch)
        await updates.check_for_updates("4.4.0")
        await updates.check_for_updates("4.4.0", force=True)
        assert calls == 2

    async def test_a_network_failure_is_reported_not_raised(self, monkeypatch):
        async def fake_fetch():
            raise aiohttp.ClientConnectionError("no route to host")

        monkeypatch.setattr(updates, "_fetch_latest_tag", fake_fetch)
        status = await updates.check_for_updates("4.4.0")
        assert status.latest is None
        assert status.error == "ClientConnectionError"

    async def test_a_timeout_is_reported_not_raised(self, monkeypatch):
        async def fake_fetch():
            raise TimeoutError

        monkeypatch.setattr(updates, "_fetch_latest_tag", fake_fetch)
        status = await updates.check_for_updates("4.4.0")
        assert status.error == "request timed out"

    async def test_a_rate_limit_reports_its_status_code(self, monkeypatch):
        async def fake_fetch():
            raise aiohttp.ClientResponseError(request_info=None, history=(), status=403)

        monkeypatch.setattr(updates, "_fetch_latest_tag", fake_fetch)
        status = await updates.check_for_updates("4.4.0")
        assert status.error == "HTTP 403"
