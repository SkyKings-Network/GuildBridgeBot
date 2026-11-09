"""
Hypixel API key budget for this project.

One Hypixel key is shared by every SkyKings project, so each one has its own
limit per 5-minute window and stops there instead of using up the others'
share. Limits are set on the SkyKings website (owner console, API key tab).
This module checks in with the website as soon as it's imported and then
about every 15 seconds (from a background thread, so it works however the
project runs its event loop), reporting usage and errors and picking up its
limit. Problems are posted to the staff Discord channel by the website's
Discord bot.

Windows follow Hypixel's own (RateLimit-Reset on every response). The
website also sends back the freshest window any project on the same key has
seen, so a quiet project resets at the same moment as the busy ones.

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

Spare capacity (what the key won't otherwise use before it resets): in the
last SPARE_TAIL seconds of a window, key_guard.check_spare() asks the website
how low the key may go (its "floor": what every project still needs, plus a
margin). Requests made inside `with key_guard.spare(n):` (n requests reserved
up front) come out of what's above that floor, not this project's limit.

Settings (environment):
    HYPIXEL_PROJECT        this project's name (each copy sets a default)
    HYPIXEL_BUDGET         limit to use until the website answers
    HYPIXEL_MONITOR_URL    default https://skykings.net
    HYPIXEL_MONITOR_TOKEN  shared secret (falls back to SKYKINGS_API_KEY)
"""
from __future__ import annotations

import asyncio
import contextvars
import hashlib
import json
import os
import re
import socket
import threading
import time
import urllib.error
import urllib.request
from contextlib import contextmanager

WINDOW = 300.0
SPARE_TAIL = 90.0  # spare capacity is handed out in a window's last 90 seconds
# Hypixel endpoints that don't take the key, so don't count.
_KEYLESS = re.compile(r"api\.hypixel\.net/(?:v2/)?(?:resources/|skyblock/(?:auctions|auctions_ended|bazaar|firesales)(?:[/?]|$))")
# Requests reserved by `with key_guard.spare(n)` in this task (a one-item list).
_SPARE = contextvars.ContextVar("hypixel_key_spare", default=None)


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
        self.spare_used = 0
        self.prev = None
        self.key_limit = None
        self.key_remaining = None
        self._remaining_at = 0.0            # when key_remaining was learned
        self.spare_floor: int | None = None  # how low the key may go (this window's tail)
        self._floor_window = 0.0
        self.errors: list[dict] = []
        self.api_key: str | None = None   # assigned on the website (None: own key)
        self._seen_at = 0.0                # when Hypixel last told us the window
        self.key_id: int | None = None
        self.key_fp: str | None = None     # fingerprint of the key actually sent
        self._fp_of: str | None = None
        self._mutex = threading.Lock()
        self._wake = threading.Event()
        self._thread: threading.Thread | None = None
        self._warned = False

    def key(self, own: str | None = None) -> str | None:
        """The Hypixel key to send: the one picked for this project on the
        website, else `own` (this project's .env key)."""
        k = self.api_key or own
        if k and k != self._fp_of:
            # A one-way fingerprint, so the website can tell which projects
            # really share a key without ever seeing it.
            self._fp_of = k
            self.key_fp = hashlib.sha256(k.encode()).hexdigest()[:10]
        return k

    # ── Window ────────────────────────────────────────────────────────────
    def _close(self, end: float, carry: int) -> None:  # call with _mutex held
        self.prev = {"window_end": int(end * 1000), "used": max(0, self.used - carry), "blocked": self.blocked, "spare": self.spare_used}
        self.used = carry
        self.blocked = 0
        self.spare_used = 0
        self.spare_floor = None

    def _roll(self) -> None:  # call with _mutex held
        now = time.time()
        if not self.window_end:
            self.window_end = now + WINDOW
        if now >= self.window_end:
            self._close(self.window_end, 0)
            while now >= self.window_end:
                self.window_end += WINDOW

    def _move_window(self, end: float, carry: int) -> None:  # call with _mutex held
        """Hypixel's window ends at `end`. A window can never end more than 5
        minutes after it's first seen, so a later end than ours means a new
        window has started: close ours (capped at now, as ours was a guess)
        and start counting again with `carry` requests."""
        if end > self.window_end + 3:
            self._close(min(self.window_end, time.time()), carry)
        if abs(end - self.window_end) > 3:
            self.window_end = end

    def _take(self, share: float = 1.0) -> float:
        """Use one request if there's room; else return seconds until the next window."""
        with self._mutex:
            self._roll()
            if self.used < self.budget * share:
                self.used += 1
                return 0.0
            return max(0.0, self.window_end - time.time())

    async def acquire(self, wait: float = 8.0, share: float = 1.0) -> None:
        """Take one request from this project's limit. When it's used up,
        wait up to `wait` seconds for the next window, else raise
        BudgetExceeded. `share` (0-1) stops a background job at that part of
        the limit, leaving the rest for everything else. Inside
        `with key_guard.spare(n)` it uses the spare requests reserved there."""
        self.start()
        held = _SPARE.get()
        if held is not None:
            if held[0] > 0:
                held[0] -= 1
                return
            raise BudgetExceeded(f"{self.project} (spare capacity)", 0, max(0.0, self.window_end - time.time()))
        delay = self._take(share)
        if delay == 0.0:
            return
        if delay <= wait:
            await asyncio.sleep(delay + 0.25)
            delay = self._take(share)
            if delay == 0.0:
                return
        with self._mutex:
            self.blocked += 1
        raise BudgetExceeded(self.project, self.budget, delay)

    # ── Spare capacity ────────────────────────────────────────────────────
    def in_spare(self) -> bool:
        return _SPARE.get() is not None

    def _room(self) -> int:  # call with _mutex held
        self._roll()
        left = self.window_end - time.time()
        if self.spare_floor is None or self._floor_window != self.window_end or left > SPARE_TAIL + 5 or left < 2:
            return 0
        if self.key_remaining is None or time.time() - self._remaining_at > 30:
            return 0
        return max(0, self.key_remaining - self.spare_floor)

    def spare_room(self) -> int:
        """Requests the key can still spare before it resets (0 outside a
        window's last SPARE_TAIL seconds, or until check_spare() has run)."""
        with self._mutex:
            return self._room()

    @contextmanager
    def spare(self, n: int):
        """Reserve `n` spare requests for the code inside (all or nothing, so
        a job that needs several requests never stops halfway). Yields False
        if there isn't room; nothing is reserved then."""
        with self._mutex:
            ok = self._room() >= n
            if ok:
                # Counted now; Hypixel's next RateLimit-Remaining corrects it.
                self.key_remaining -= n
                self.spare_used += n
        if not ok:
            yield False
            return
        held = [n]
        token = _SPARE.set(held)
        try:
            yield True
        finally:
            _SPARE.reset(token)
            if held[0]:
                with self._mutex:  # not all used (e.g. the data was fresh)
                    self.spare_used -= held[0]
                    if self.key_remaining is not None:
                        self.key_remaining += held[0]

    def check_spare(self) -> int:
        """Ask the website for this window's floor (blocking; run it in a
        thread). Returns the spare room."""
        self.report(want_spare=True)
        return self.spare_room()

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
            # A window that has ended is closed first; after that, Hypixel's
            # reset time only corrects our guess of when this one ends (the
            # count carries on).
            self._roll()
            if reset is not None and 0 <= reset <= WINDOW:
                # This request was counted already; it belongs to the window
                # Hypixel says it's in.
                self._move_window(time.time() + reset, 1 if self.used else 0)
                self._seen_at = time.time()
            if limit is not None:
                self.key_limit = limit
            if remaining is not None:
                self.key_remaining = remaining
                self._remaining_at = time.time()
            bad = status in (403, 429) or (status or 0) >= 500
            if bad:
                self.errors.append({"status": status, "at": int(time.time() * 1000)})
                del self.errors[:-20]
                if status == 429:
                    self.spare_floor = None  # the key is out: no more spare this window
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
            time.sleep(3)  # a burst of errors still only checks in every few seconds
            self._wake.wait(12)
            self._wake.clear()

    def report(self, want_spare: bool = False) -> None:
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
                "spare_used": self.spare_used,
                "key_limit": self.key_limit,
                "key_remaining": self.key_remaining,
                "errors": errors,
                "prev": prev,
                "key_id": self.key_id,
                "window_seen_at": int(self._seen_at * 1000) if self._seen_at else None,
                "want_spare": want_spare,
                "key_fp": self.key_fp,
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
            # The key's shared window, unless Hypixel told us ourselves just now.
            end = data.get("window_end")
            if isinstance(end, (int, float)) and end / 1000 > time.time() and time.time() - self._seen_at > 30:
                with self._mutex:
                    self._roll()
                    self._move_window(end / 1000, 0)
            # Spare capacity: the floor for this window, and the key's
            # remaining requests if the website heard more recently than we did.
            spare = data.get("spare")
            if want_spare and isinstance(spare, dict):
                with self._mutex:
                    self._roll()
                    if isinstance(spare.get("floor"), int):
                        self.spare_floor = spare["floor"]
                        self._floor_window = self.window_end
                    rem, at = spare.get("remaining"), spare.get("remaining_at")
                    if isinstance(rem, int) and isinstance(at, (int, float)) and at / 1000 > self._remaining_at:
                        self.key_remaining = rem
                        self._remaining_at = at / 1000
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
