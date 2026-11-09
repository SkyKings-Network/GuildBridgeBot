"""
Hypixel API key budget for this project.

One Hypixel key is shared by every SkyKings project, so each one has its own
limit per 5-minute window and stops there instead of using up the others'
share. Limits are set on the SkyKings website (owner console, API key tab).
This module checks in with the website as soon as it's imported and then
about once a minute (from a background thread, so it works however the
project runs its event loop), reporting usage and errors and picking up its
limit. Problems are posted to the staff Discord channel by the website's
Discord bot.

Windows follow Hypixel's own (RateLimit-Reset on every response), so every
project resets at the same moment.

The same file lives in each Python project; the hub is
"SkyKings V2 Website/skyblock/hypixel-key.js".

Which Hypixel key to use is also picked on the website: key_guard.key(own)
returns the key assigned there, or `own` (this project's .env key) when
none is.

Use:
    from hypixel_key_guard import key_guard, BudgetExceeded
    await key_guard.acquire()                        # before a keyed Hypixel request
    api_key = key_guard.key(os.getenv("HYPIXEL_API_KEY"))   # the key to send
    key_guard.observe(resp.status, resp.headers)     # after it

Settings (environment):
    HYPIXEL_PROJECT        this project's name (each copy sets a default)
    HYPIXEL_BUDGET         limit to use until the website answers
    HYPIXEL_MONITOR_URL    default https://skykings.net
    HYPIXEL_MONITOR_TOKEN  shared secret (falls back to SKYKINGS_API_KEY)
"""
from __future__ import annotations

import asyncio
import json
import os
import re
import socket
import threading
import time
import urllib.error
import urllib.request

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
        self.api_key: str | None = None   # assigned on the website (None: own key)
        self.key_id: int | None = None
        self._mutex = threading.Lock()
        self._wake = threading.Event()
        self._thread: threading.Thread | None = None
        self._warned = False

    def key(self, own: str | None = None) -> str | None:
        """The Hypixel key to send: the one picked for this project on the
        website, else `own` (this project's .env key)."""
        return self.api_key or own

    # ── Window ────────────────────────────────────────────────────────────
    def _roll(self) -> None:  # call with _mutex held
        now = time.time()
        if not self.window_end:
            self.window_end = now + WINDOW
        if now >= self.window_end:
            self.prev = {"window_end": int(self.window_end * 1000), "used": self.used, "blocked": self.blocked}
            while now >= self.window_end:
                self.window_end += WINDOW
            self.used = 0
            self.blocked = 0

    def _take(self) -> float:
        """Use one request if there's room; else return seconds until the next window."""
        with self._mutex:
            self._roll()
            if self.used < self.budget:
                self.used += 1
                return 0.0
            return max(0.0, self.window_end - time.time())

    async def acquire(self, wait: float = 8.0) -> None:
        """Take one request from this project's limit. When it's used up,
        wait up to `wait` seconds for the next window, else raise
        BudgetExceeded."""
        self.start()
        delay = self._take()
        if delay == 0.0:
            return
        if delay <= wait:
            await asyncio.sleep(delay + 0.25)
            delay = self._take()
            if delay == 0.0:
                return
        with self._mutex:
            self.blocked += 1
        raise BudgetExceeded(self.project, self.budget, delay)

    def observe(self, status: int | None, headers=None) -> None:
        """Learn the key's window and remaining requests from a response."""
        h = headers or {}

        def num(*names):
            for name in names:
                try:
                    v = h.get(name)
                except Exception:
                    v = None
                if v is not None:
                    try:
                        return int(float(v))
                    except (TypeError, ValueError):
                        return None
            return None

        reset = num("RateLimit-Reset", "ratelimit-reset")
        limit = num("RateLimit-Limit", "ratelimit-limit")
        remaining = num("RateLimit-Remaining", "ratelimit-remaining")
        with self._mutex:
            if reset is not None and 0 <= reset <= WINDOW:
                end = time.time() + reset
                if not self.window_end or abs(end - self.window_end) > 3:
                    if self.window_end and end > self.window_end + 3:
                        # Hypixel started a new window before we expected.
                        self.prev = {"window_end": int(self.window_end * 1000), "used": self.used, "blocked": self.blocked}
                        self.used = 1
                        self.blocked = 0
                    self.window_end = end
            if limit is not None:
                self.key_limit = limit
            if remaining is not None:
                self.key_remaining = remaining
            bad = status in (403, 429) or (status or 0) >= 500
            if bad:
                self.errors.append({"status": status, "at": int(time.time() * 1000)})
                del self.errors[:-20]
        if bad:
            self._wake.set()  # report it now

    # ── Check-ins with the website (background thread) ───────────────────
    def start(self) -> None:
        if self._thread is not None and self._thread.is_alive():
            return
        self._thread = threading.Thread(target=self._run, name="hypixel-key-checkin", daemon=True)
        self._thread.start()

    def _run(self) -> None:
        while True:
            try:
                self.report()
            except Exception as e:  # never let reporting break the project
                print(f"[hypixel-key] check-in failed: {e}")
            self._wake.wait(60)
            self._wake.clear()

    def report(self) -> None:
        token = os.getenv("HYPIXEL_MONITOR_TOKEN") or os.getenv("SKYKINGS_API_KEY") or ""
        if not token:
            if not self._warned:
                print("[hypixel-key] HYPIXEL_MONITOR_TOKEN isn't set, so this project can't check in with skykings.net")
                self._warned = True
            return
        with self._mutex:
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
                "key_id": self.key_id,
            }
        url = (os.getenv("HYPIXEL_MONITOR_URL") or "https://skykings.net").rstrip("/") + "/api/hypixel-key/report"
        req = urllib.request.Request(
            url, data=json.dumps(body).encode(), method="POST",
            headers={
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json",
                "X-Requested-With": "SkyKingsWeb",
                "User-Agent": "SkyKings-hypixel-key",
            },
        )
        try:
            with urllib.request.urlopen(req, timeout=10) as r:
                data = json.loads(r.read() or b"{}")
            if isinstance(data.get("budget"), int):
                self.budget = data["budget"]
            if "key_id" in data:
                with self._mutex:
                    if data.get("key_id") != self.key_id:
                        # A different key has its own window and numbers.
                        self.window_end = 0.0
                        self.used = 0
                        self.key_limit = None
                        self.key_remaining = None
                    self.key_id = data.get("key_id")
                    self.api_key = data.get("api_key") or None
            return
        except urllib.error.HTTPError as e:
            print(f"[hypixel-key] check-in refused: HTTP {e.code}" + (" (HYPIXEL_MONITOR_TOKEN doesn't match the website's)" if e.code == 401 else ""))
        except Exception as e:
            print(f"[hypixel-key] could not reach {url}: {e}")
        # Not delivered: keep it for the next try.
        with self._mutex:
            self.errors = (errors + self.errors)[-20:]
            if prev and not self.prev:
                self.prev = prev


# This project's guard (HYPIXEL_PROJECT overrides the name). It checks in
# straight away, so the project shows up on the website even before it uses
# the key.
key_guard = KeyGuard("bridge-bot", 15)
key_guard.start()
