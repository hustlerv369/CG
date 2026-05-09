"""Optional HTTP Basic auth for the CG dashboard.

Disabled by default — the dashboard runs unauthenticated when bound to
``127.0.0.1`` (the normal local-dev case). Enable for any public
deployment by setting the ``CG_AUTH_PASSWORD_HASH`` environment
variable (and optionally ``CG_AUTH_USER``, default ``admin``).

Hash format: ``pbkdf2_sha256$<iterations>$<salt_hex>$<hash_hex>``.
Generate one with ``python src/cg.py auth init`` — it creates a strong
random password, hashes it with 600,000 PBKDF2-SHA256 rounds, prints
the env var and config file to set, and (on Windows) drops a copy of
the credentials on the user's Desktop so they can be retrieved later.

No third-party dependencies — only ``hashlib``, ``hmac``, ``secrets``,
``base64`` from the stdlib.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import os
import secrets
import string
from pathlib import Path
from typing import Any

# 600k rounds is the OWASP-recommended minimum for PBKDF2-SHA256 in
# 2024+. Tune higher if hardware allows; lower only if explicitly told
# by the user.
PBKDF2_ITERATIONS = 600_000
PBKDF2_ALGO = "sha256"
HASH_PREFIX = "pbkdf2_sha256"


def hash_password(password: str, *, iterations: int = PBKDF2_ITERATIONS) -> str:
    """Return the canonical hash string for ``password``.

    Format: ``pbkdf2_sha256$<iter>$<salt_hex>$<hash_hex>``.
    """
    salt = secrets.token_bytes(16)
    derived = hashlib.pbkdf2_hmac(PBKDF2_ALGO, password.encode("utf-8"),
                                     salt, iterations)
    return f"{HASH_PREFIX}${iterations}${salt.hex()}${derived.hex()}"


def verify_password(password: str, encoded: str) -> bool:
    """Constant-time check of ``password`` against an ``encoded`` hash.

    Returns False on any malformed input; never raises.
    """
    if not encoded or not password:
        return False
    try:
        algo, iter_str, salt_hex, hash_hex = encoded.split("$", 3)
    except ValueError:
        return False
    if algo != HASH_PREFIX:
        return False
    try:
        iterations = int(iter_str)
        salt = bytes.fromhex(salt_hex)
        expected = bytes.fromhex(hash_hex)
    except (ValueError, TypeError):
        return False
    derived = hashlib.pbkdf2_hmac(PBKDF2_ALGO, password.encode("utf-8"),
                                     salt, iterations)
    return hmac.compare_digest(derived, expected)


def generate_password(length: int = 28) -> str:
    """Cryptographically strong password.

    Uses an ambiguous-char-stripped alphabet so the user can read it
    off a printed page or a slack message without confusing 1/l/I or
    0/O. Length 28 ≈ 161 bits of entropy with this alphabet — fine for
    a single-user password that's never typed (always pasted).
    """
    alphabet = "".join(set(string.ascii_letters + string.digits)
                         - set("0O1Il"))
    return "".join(secrets.choice(alphabet) for _ in range(length))


def auth_enabled() -> bool:
    """Auth is on iff CG_AUTH_PASSWORD_HASH is set + non-empty."""
    return bool(os.environ.get("CG_AUTH_PASSWORD_HASH", "").strip())


def expected_user() -> str:
    return os.environ.get("CG_AUTH_USER", "admin").strip() or "admin"


def expected_hash() -> str:
    return os.environ.get("CG_AUTH_PASSWORD_HASH", "").strip()


def check_credentials(user: str, password: str) -> bool:
    """Verify a single (user, password) pair against the env config.

    Returns True iff auth is enabled AND user matches AND password
    verifies. Constant-time username comparison is unnecessary (the
    username is not a secret) but we keep it cheap with a single
    string compare.
    """
    if not auth_enabled():
        # If auth is off, there is no notion of "correct credentials".
        # Callers should check auth_enabled() first; this returns
        # False to be safe.
        return False
    return user == expected_user() and verify_password(password, expected_hash())


# ---------------------------------------------------------------------------
# Credentials file helpers (used by `cg auth init`)
# ---------------------------------------------------------------------------

def credentials_text(user: str, password: str, hash_str: str,
                       *, target_url: str | None = None) -> str:
    """Render the human-readable credentials block saved to disk.

    Format is plain text — no Markdown — so a user can open it in
    Notepad and read it without rendering quirks.
    """
    lines = [
        "ClaudeGravity dashboard credentials",
        "===================================",
        "",
    ]
    if target_url:
        lines.append(f"URL:      {target_url}")
    lines.append(f"Username: {user}")
    lines.append(f"Password: {password}")
    lines += [
        "",
        "Keep this file private. Anyone with this password can:",
        "  - run agents that consume your Claude Pro / Google subscription",
        "  - read every project the orchestrator has ever produced",
        "  - read your CG notes + workflow drafts",
        "",
        "To rotate the password, run `python src/cg.py auth init` again.",
        "The new credentials will overwrite the existing config + this file.",
        "",
        "Server-side configuration (set on the host running the dashboard):",
        "  CG_AUTH_USER=" + user,
        f"  CG_AUTH_PASSWORD_HASH={hash_str}",
        "",
        "On Windows: System Properties → Environment Variables → User variables",
        "On macOS/Linux: append to ~/.bashrc or ~/.zshrc, or use a systemd unit",
        "",
    ]
    return "\n".join(lines)


def desktop_path() -> Path | None:
    """Best-effort lookup of the current user's Desktop folder.

    Falls back to None if the standard locations don't exist (e.g.
    in a CI runner). Caller decides what to do with that.
    """
    home = Path.home()
    candidates = [
        home / "Desktop",
        home / "OneDrive" / "Desktop",  # Windows + OneDrive default
        home / "Plocha",                 # Czech Windows localization
    ]
    for c in candidates:
        if c.exists() and c.is_dir():
            return c
    return None


def write_credentials_file(user: str, password: str, hash_str: str,
                              *, target_url: str | None = None,
                              dest: Path | None = None) -> Path:
    """Write the credentials text to ``dest`` (or Desktop, or HOME).

    Returns the actual path written.
    """
    text = credentials_text(user, password, hash_str, target_url=target_url)
    if dest is None:
        d = desktop_path()
        if d is None:
            d = Path.home()
        dest = d / "claudegravity-login.txt"
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(text, encoding="utf-8")
    # On POSIX, restrict to owner-read. On Windows, the default ACL
    # already restricts to the current user under their profile.
    try:
        if os.name == "posix":
            os.chmod(dest, 0o600)
    except Exception:
        pass
    return dest
