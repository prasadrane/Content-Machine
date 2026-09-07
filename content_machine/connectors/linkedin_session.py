"""LinkedIn Session Manager: stores and auto-syncs browser authentication session."""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import requests

from content_machine.storage.paths import home_root

logger = logging.getLogger(__name__)

DEFAULT_SESSION_FILE = "linkedin_session.json"
DEFAULT_PROFILE_DIR = "browser_profile"


class LinkedInSessionManager:
    """Manages the persistence, validation, and browser-sync of the LinkedIn li_at session cookie."""

    def __init__(self, session_file: Optional[Path] = None, profile_dir: Optional[Path] = None):
        self.session_file = session_file or (home_root() / DEFAULT_SESSION_FILE)
        self.profile_dir = profile_dir or (home_root() / DEFAULT_PROFILE_DIR)

    def get_saved_cookie(self) -> Optional[str]:
        """Read saved cookie from session file if available."""
        if not self.session_file.is_file():
            return None
        try:
            data = json.loads(self.session_file.read_text(encoding="utf-8"))
            cookie = data.get("li_at", "").strip()
            return cookie if cookie else None
        except Exception as e:
            logger.warning("Failed to read LinkedIn session file: %s", e)
            return None

    def get_session_metadata(self) -> dict:
        """Read saved metadata dict from session file if available."""
        if not self.session_file.is_file():
            return {}
        try:
            return json.loads(self.session_file.read_text(encoding="utf-8"))
        except Exception:
            return {}


    def save_session(self, li_at: str) -> None:
        """Persist li_at cookie and metadata to disk."""
        self.session_file.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "li_at": li_at.strip(),
            "saved_at": datetime.now(tz=timezone.utc).isoformat(),
        }
        self.session_file.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    def is_valid(self, cookie: Optional[str] = None) -> bool:
        """Validate if the cookie is accepted by LinkedIn's Voyager API."""
        val = cookie or self.get_saved_cookie()
        if not val:
            return False

        headers = {
            "Cookie": f'li_at={val}; JSESSIONID="ajax:1234567890123456789"',
            "csrf-token": "ajax:1234567890123456789",
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36"
            ),
        }
        try:
            resp = requests.get(
                "https://www.linkedin.com/voyager/api/me",
                headers=headers,
                timeout=10,
            )
            return resp.status_code == 200
        except Exception:
            return False

    def get_valid_cookie(self) -> Optional[str]:
        """Return the saved cookie if valid; otherwise None."""
        saved = self.get_saved_cookie()
        if saved and self.is_valid(saved):
            return saved
        return None

    def sync_from_browser(self, headless: bool = False, timeout_ms: int = 30000) -> Optional[str]:
        """Launch Playwright with persistent context to extract or refresh li_at."""
        try:
            from playwright.sync_api import sync_playwright
        except ImportError:
            logger.error("Playwright is not installed.")
            return None

        self.profile_dir.mkdir(parents=True, exist_ok=True)
        with sync_playwright() as p:
            browser_context = p.chromium.launch_persistent_context(
                user_data_dir=str(self.profile_dir),
                headless=headless,
                timeout=timeout_ms,
            )
            page = browser_context.new_page()
            try:
                page.goto("https://www.linkedin.com/feed/", timeout=timeout_ms)
                page.wait_for_timeout(2000)
                cookies = browser_context.cookies(["https://www.linkedin.com"])
                for c in cookies:
                    if c.get("name") == "li_at":
                        val = c.get("value")
                        if val:
                            self.save_session(val)
                            return val
            finally:
                browser_context.close()
        return None
