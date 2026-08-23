"""Real-time release checks against the project's GitHub releases page.

The version in `pyproject.toml` says what is running; it says nothing about whether a
newer build has been published. This module answers that by asking GitHub for the
latest release whenever `/info` is used, so an operator can see they are behind
without leaving Discord.
"""

import asyncio
import re
import time
from dataclasses import dataclass

import aiohttp

# The releases API returns the newest published, non-draft release. The HTML page is
# what gets linked in the embed, since that is what a human wants to read.
LATEST_RELEASE_API_URL = "https://api.github.com/repos/WebTheDev/TicketBot/releases/latest"
RELEASES_PAGE_URL = "https://github.com/WebTheDev/TicketBot/releases"

REQUEST_TIMEOUT_SECONDS = 5.0
# Unauthenticated GitHub API calls are limited to 60 per hour per IP, so successful
# lookups are cached. Failures are cached far more briefly so a blip does not pin a
# stale error in place for the rest of the window.
CACHE_TTL_SECONDS = 300.0
FAILURE_CACHE_TTL_SECONDS = 30.0


def parse_version(raw: str | None) -> tuple[int, ...] | None:
    """Parse a version or release tag into comparable numbers.

    Accepts the shapes GitHub tags actually use -- "4.5.0", "v4.5.0", "4.5.0-rc1" --
    and returns None for anything that is not a dotted numeric version, which is the
    signal to fall back on a plain string comparison rather than guess an ordering.
    """
    if not raw:
        return None
    text = raw.strip().lstrip("vV")
    # Drop any pre-release or build suffix before splitting: "4.5.0-rc1" compares as 4.5.0.
    text = re.split(r"[-+]", text, maxsplit=1)[0]
    parts = text.split(".")
    numbers: list[int] = []
    for part in parts:
        if not part.isdigit():
            return None
        numbers.append(int(part))
    return tuple(numbers) if numbers else None


def compare_versions(current: str | None, latest: str | None) -> int | None:
    """Order two versions: -1 if `current` is older, 0 if equal, 1 if newer.

    Returns None when either side cannot be parsed, so callers can report "unknown"
    instead of showing a confidently wrong verdict.
    """
    parsed_current = parse_version(current)
    parsed_latest = parse_version(latest)
    if parsed_current is None or parsed_latest is None:
        return None
    width = max(len(parsed_current), len(parsed_latest))
    padded_current = parsed_current + (0,) * (width - len(parsed_current))
    padded_latest = parsed_latest + (0,) * (width - len(parsed_latest))
    return (padded_current > padded_latest) - (padded_current < padded_latest)


@dataclass(frozen=True)
class UpdateStatus:
    """What the latest release lookup found, ready to be rendered into an embed."""

    current: str
    latest: str | None = None
    error: str | None = None

    @property
    def outdated(self) -> bool:
        return compare_versions(self.current, self.latest) == -1

    def describe(self) -> str:
        """Render the lookup for an embed field."""
        if self.error is not None:
            return f"⚠️ Check failed ({self.error})"
        if self.latest is None:
            return f"⚠️ No releases published ([releases]({RELEASES_PAGE_URL}))"
        order = compare_versions(self.current, self.latest)
        if order is None:
            # Unparseable on one side -- say what was found and let a human judge.
            return f"❓ Latest release is `{self.latest}` ([releases]({RELEASES_PAGE_URL}))"
        if order < 0:
            return f"⬆️ Update available: `{self.latest}` ([download]({RELEASES_PAGE_URL}))"
        if order > 0:
            return f"\U0001f9ea Ahead of the latest release (`{self.latest}`)"
        return "✅ Up to date"


# Cached as (expires_at, status). Module-level rather than per-call so every /info in
# the cache window shares one lookup; the lock keeps concurrent commands from each
# firing their own request while the first is still in flight.
_cache: tuple[float, UpdateStatus] | None = None
_cache_lock = asyncio.Lock()


def clear_cache() -> None:
    """Forget the cached lookup. Exists for tests and for a forced re-check."""
    global _cache
    _cache = None


async def _fetch_latest_tag() -> str | None:
    """Ask GitHub for the newest published release tag, or None if there are none."""
    timeout = aiohttp.ClientTimeout(total=REQUEST_TIMEOUT_SECONDS)
    headers = {
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    async with aiohttp.ClientSession(timeout=timeout, headers=headers) as session:
        async with session.get(LATEST_RELEASE_API_URL) as response:
            if response.status == 404:
                # A repository with no published releases -- not an error worth shouting about.
                return None
            response.raise_for_status()
            payload = await response.json()
    tag = payload.get("tag_name") or payload.get("name")
    return tag.strip() if isinstance(tag, str) and tag.strip() else None


async def check_for_updates(current_version: str, *, force: bool = False) -> UpdateStatus:
    """Compare the running version against the latest GitHub release.

    Never raises: a network failure, a rate limit, or a malformed response all come
    back as an `UpdateStatus` carrying the reason, because `/info` should still render
    the rest of its fields when GitHub is having a bad day.
    """
    global _cache
    async with _cache_lock:
        now = time.monotonic()
        if not force and _cache is not None:
            expires_at, cached = _cache
            if now < expires_at and cached.current == current_version:
                return cached
        try:
            status = UpdateStatus(current=current_version, latest=await _fetch_latest_tag())
            ttl = CACHE_TTL_SECONDS
        except TimeoutError:
            status = UpdateStatus(current=current_version, error="request timed out")
            ttl = FAILURE_CACHE_TTL_SECONDS
        except aiohttp.ClientResponseError as error:
            status = UpdateStatus(current=current_version, error=f"HTTP {error.status}")
            ttl = FAILURE_CACHE_TTL_SECONDS
        except (aiohttp.ClientError, OSError, ValueError) as error:
            status = UpdateStatus(current=current_version, error=type(error).__name__)
            ttl = FAILURE_CACHE_TTL_SECONDS
        _cache = (time.monotonic() + ttl, status)
        return status
