"""
Hypixel API key budget for this project.

One Hypixel key (300 requests per 5 minutes) is shared by every SkyKings
project, so each one has its own limit per 5-minute window and stops there
instead of using up the others' share. Limits are set on the SkyKings website
(owner console, API key tab); this module checks in with the website about
once a minute to report usage and errors and to pick up its limit. Problems
are posted to the staff Discord channel by the website's Discord bot.

Windows follow Hypixel's own (RateLimit-Reset on every response), so every
project resets at the same moment.

The same file lives in each Python project; the hub is
"SkyKings V2 Website/skyblock/hypixel-key.js".

Use:
    from hypixel_key_guard import key_guard, BudgetExceeded
    await key_guard.acquire()              # before a keyed Hypixel request
    key_guard.observe(resp.status, resp.headers)   # after it

Settings (environment):
    HYPIXEL_PROJECT        this project's name (each file sets a default)
    HYPIXEL_BUDGET         limit to use until the website answers
    HYPIXEL_MONITOR_URL    default https://skykings.net
    HYPIXEL_MONITOR_TOKEN  shared secret (falls back to SKYKINGS_API_KEY)
"""
from __future__ import annotations

import asyncio
import os
import re
import socket
import time

import aiohttp

WINDOW = 300.0
# Hypixel endpoints that don't take the key, so don't count.
_KEYLESS = re.compile(r"api\.hypixel\.net/(?:v2/)?(?:resources/|skyblock/(?:auctions|auctions_ended|bazaar|firesales)(?:[/?]|$))")


def needs_key(url: str) -> bool:
    url = str(url)
    return "api.hypixel.net" in url and not _KEYLESS.search(url)


class BudgetExceeded(Exception):
    """This project has used its Hypixel limit for the current 5 minutes."""

    def __init__(self, project: str, budget: int, retry_after: float):
        self.retry_after = retry_after
        super().__init__(
            f"{project} has used its Hypixel limit of {budget} requests for this 5 minutes; "
            f"try again in {int(retry_after) + 1}s"
        )


class KeyGuard:
    def __init__(self, project: str, default_budget: int = 20):
        self.project = os.getenv("HYPIXEL_PROJECT") or project
        try:
            self.budget = int(os.getenv("HYPIXEL_BUDGET") or default_budget)
        except ValueError:
            self.budget = default_budget
        self.default_budget = self.budget
        self.window_end = 0.0
        self.used = 0
        self.blocked = 0
        self.prev = None
        self.key_limit = None
        self.key_remaining = None
        self.errors: list[dict] = []
        self._task: asyncio.Task | None = None
        self._lock: asyncio.Lock | None = None
        self._last_report = 0.0

    # ── Window ────────────────────────────────────────────────────────────
    def _roll(self) -> None:
        now = time.time()
        if not self.window_end:
            self.window_end = now + WINDOW
        if now >= self.window_end:
            self.prev = {"window_end": int(self.window_end * 1000), "used": self.used, "blocked": self.blocked}
            while now >= self.window_end:
                self.window_end += WINDOW
            self.used = 0
            self.blocked = 0

    async def acquire(self, wait: float = 8.0) -> None:
        """Take one request from this project's limit. When it's used up,
        wait up to `wait` seconds for the next window, else raise
        BudgetExceeded."""
        self._start()
        self._roll()
        if self.used >= self.budget:
            delay = self.window_end - time.time()
            if delay > wait:
                self.blocked += 1
                raise BudgetExceeded(self.project, self.budget, delay)
            await asyncio.sleep(max(0.0, delay) + 0.25)
            self._roll()
            if self.used >= self.budget:
                self.blocked += 1
                raise BudgetExceeded(self.project, self.budget, self.window_end - time.time())
        self.used += 1

    def observe(self, status: int | None, headers=None) -> None:
        """Learn the key's window and remaining requests from a response."""
        h = headers or {}

        def num(name):
            try:
                v = h.get(name)
                return None if v is None else int(float(v))
            except (TypeError, ValueError):
                return None

        reset = num("RateLimit-Reset") if num("RateLimit-Reset") is not None else num("ratelimit-reset")
        if reset is not None and 0 <= reset <= WINDOW:
            end = time.time() + reset
            if not self.window_end or abs(end - self.window_end) > 3:
                if self.window_end and end > self.window_end + 3:
                    # Hypixel started a new window before we expected.
                    self.prev = {"window_end": int(self.window_end * 1000), "used": self.used, "blocked": self.blocked}
                    self.used = 1
                    self.blocked = 0
                self.window_end = end
        limit = num("RateLimit-Limit") if num("RateLimit-Limit") is not None else num("ratelimit-limit")
        remaining = num("RateLimit-Remaining") if num("RateLimit-Remaining") is not None else num("ratelimit-remaining")
        if limit is not None:
            self.key_limit = limit
        if remaining is not None:
            self.key_remaining = remaining
        if status in (403, 429) or (status or 0) >= 500:
            self.errors.append({"status": status, "at": int(time.time() * 1000)})
            del self.errors[:-20]
            self._report_soon()

    # ── Check-ins with the website ───────────────────────────────────────
    def _start(self) -> None:
        if self._task is not None and not self._task.done():
            return
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            return
        self._task = loop.create_task(self._loop())

    def _report_soon(self) -> None:
        try:
            asyncio.get_running_loop().create_task(self.report(force=True))
        except RuntimeError:
            pass

    async def _loop(self) -> None:
        while True:
            try:
                await self.report()
            except Exception as e:  # never let reporting break the project
                print(f"[hypixel-key] check-in failed: {e}")
            await asyncio.sleep(60)

    async def report(self, force: bool = False) -> None:
        token = os.getenv("HYPIXEL_MONITOR_TOKEN") or os.getenv("SKYKINGS_API_KEY") or ""
        if not token:
            return
        # About once a minute (some projects start a fresh event loop per
        # request, which restarts the check-in loop each time).
        if not force and time.time() - self._last_report < 50:
            return
        self._last_report = time.time()
        if self._lock is None:
            self._lock = asyncio.Lock()
        async with self._lock:
            self._roll()
            errors, self.errors = self.errors, []
            prev, self.prev = self.prev, None
            body = {
                "project": self.project,
                "host": socket.gethostname(),
                "budget_default": self.default_budget,
                "window_end": int(self.window_end * 1000),
                "used": self.used,
                "blocked": self.blocked,
                "key_limit": self.key_limit,
                "key_remaining": self.key_remaining,
                "errors": errors,
                "prev": prev,
            }
            url = (os.getenv("HYPIXEL_MONITOR_URL") or "https://skykings.net").rstrip("/") + "/api/hypixel-key/report"
            try:
                async with aiohttp.ClientSession() as s:
                    async with s.post(
                        url, json=body, timeout=aiohttp.ClientTimeout(total=10),
                        headers={"Authorization": f"Bearer {token}", "X-Requested-With": "SkyKingsWeb"},
                    ) as r:
                        if r.status == 200:
                            data = await r.json()
                            if isinstance(data.get("budget"), int):
                                self.budget = data["budget"]
                            return
                        print(f"[hypixel-key] check-in refused: HTTP {r.status}")
            except Exception as e:
                print(f"[hypixel-key] could not reach {url}: {e}")
            # Not delivered: keep what we had for the next try.
            self.errors = (errors + self.errors)[-20:]
            if prev and not self.prev:
                self.prev = prev


# This project's guard. HYPIXEL_PROJECT overrides the name.
key_guard = KeyGuard("bridge-bot", 15)
