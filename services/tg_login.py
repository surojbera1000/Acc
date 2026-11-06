"""Log into a Telegram account (as a user, via Telethon) and read its details.

Used by the admin Add Account wizard:
    1. start(phone)          -> Telegram sends a login code to that account
    2. submit_code(code)     -> "ok" or "need_password"
    3. submit_password(pw)   -> "ok"            (only when 2FA is on)
    4. fetch_details()       -> username, name, 2FA on/off, recovery email, ...

Needs API_ID and API_HASH from https://my.telegram.org (set them in .env).
"""
import logging
import re
import time

from config import API_HASH, API_ID

logger = logging.getLogger(__name__)

LOGIN_TIMEOUT = 600  # seconds a half-finished login is kept alive


class LoginError(Exception):
    """Login failed with a message that is safe to show to the admin."""


def is_configured() -> bool:
    return bool(API_ID and API_HASH)


def normalize_phone(text: str) -> str:
    digits = re.sub(r"\D", "", text or "")
    return f"+{digits}" if digits else ""


def normalize_code(text: str) -> str:
    """Admins send the code with spaces (e.g. 1 2 3 4 5) so Telegram doesn't
    detect a shared login code and expire it; keep only the digits."""
    return re.sub(r"\D", "", text or "")


def _friendly(e: Exception) -> str:
    from telethon import errors
    if isinstance(e, errors.PhoneNumberInvalidError):
        return "Invalid phone number. Send it with country code, e.g. +919876543210."
    if isinstance(e, errors.PhoneNumberBannedError):
        return "This number is banned by Telegram."
    if isinstance(e, errors.PhoneNumberUnoccupiedError):
        return "No Telegram account exists on this number."
    if isinstance(e, errors.FloodWaitError):
        return f"Telegram rate limit. Try again in {e.seconds} seconds."
    if isinstance(e, errors.PhoneCodeInvalidError):
        return "Wrong OTP. Check the code and send it again."
    if isinstance(e, errors.PhoneCodeExpiredError):
        return "OTP expired. Cancel and start again (send the code with spaces next time)."
    if isinstance(e, errors.PasswordHashInvalidError):
        return "Wrong 2FA password. Send it again."
    return f"Telegram error: {e.__class__.__name__}"


class AccountLogin:
    """One in-progress login. Keep the same object across all steps."""

    def __init__(self, phone: str):
        self.phone = phone
        self.client = None
        self.phone_code_hash = None
        self.password = None
        self.created = time.monotonic()

    @property
    def expired(self) -> bool:
        return time.monotonic() - self.created > LOGIN_TIMEOUT

    async def start(self):
        """Connect and ask Telegram to send the login code."""
        from telethon import TelegramClient
        from telethon.sessions import StringSession

        self.client = TelegramClient(
            StringSession(), int(API_ID), API_HASH,
            device_model="Account Store Bot", system_version="1.0", app_version="1.0",
        )
        await self.client.connect()
        try:
            sent = await self.client.send_code_request(self.phone)
        except Exception as e:
            await self.close()
            raise LoginError(_friendly(e)) from e
        self.phone_code_hash = sent.phone_code_hash

    async def submit_code(self, code: str) -> str:
        from telethon import errors
        try:
            await self.client.sign_in(self.phone, code, phone_code_hash=self.phone_code_hash)
            return "ok"
        except errors.SessionPasswordNeededError:
            return "need_password"
        except (errors.PhoneCodeInvalidError, errors.PhoneCodeExpiredError,
                errors.PhoneNumberUnoccupiedError, errors.FloodWaitError) as e:
            raise LoginError(_friendly(e)) from e

    async def submit_password(self, password: str) -> str:
        from telethon import errors
        try:
            await self.client.sign_in(password=password)
        except (errors.PasswordHashInvalidError, errors.FloodWaitError) as e:
            raise LoginError(_friendly(e)) from e
        self.password = password
        return "ok"

    async def fetch_details(self) -> dict:
        """Read the logged-in account's identity and security settings."""
        from telethon.tl.functions.account import GetAuthorizationsRequest, GetPasswordRequest

        me = await self.client.get_me()
        pwd = await self.client(GetPasswordRequest())
        try:
            auths = await self.client(GetAuthorizationsRequest())
            sessions = len(auths.authorizations)
        except Exception:
            sessions = None
        name = " ".join(x for x in (me.first_name, me.last_name) if x) or None
        return {
            "tg_user_id": me.id,
            "tg_name": name,
            "username": me.username,
            "phone": f"+{me.phone}" if me.phone else self.phone,
            "premium": bool(getattr(me, "premium", False)),
            "two_fa_enabled": bool(pwd.has_password),
            "gmail_added": bool(pwd.has_recovery),
            "email_pending": pwd.email_unconfirmed_pattern or None,
            "sessions": sessions,
            "session": self.client.session.save(),
        }

    async def close(self):
        if self.client:
            try:
                await self.client.disconnect()
            except Exception:
                pass
