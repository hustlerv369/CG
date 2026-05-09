"""Tests for src/auth.py — password hashing + credentials handling."""

from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from auth import (  # noqa: E402
    HASH_PREFIX,
    auth_enabled,
    check_credentials,
    credentials_text,
    generate_password,
    hash_password,
    verify_password,
    write_credentials_file,
)


# ---------------------------------------------------------------------------
# hash_password / verify_password
# ---------------------------------------------------------------------------

def test_hash_password_format():
    h = hash_password("hunter2")
    parts = h.split("$")
    assert len(parts) == 4
    assert parts[0] == HASH_PREFIX
    assert int(parts[1]) >= 100_000  # respect minimum cost
    # salt + hash are hex-encoded, even-length, valid hex chars
    bytes.fromhex(parts[2])
    bytes.fromhex(parts[3])


def test_hash_password_uses_random_salt():
    a = hash_password("same")
    b = hash_password("same")
    assert a != b  # different salts → different output


def test_verify_password_round_trip():
    h = hash_password("correct horse battery staple")
    assert verify_password("correct horse battery staple", h) is True
    assert verify_password("wrong", h) is False
    assert verify_password("", h) is False


def test_verify_password_handles_garbage_input():
    # None of these should raise
    assert verify_password("anything", "") is False
    assert verify_password("", "") is False
    assert verify_password("x", "not-a-hash") is False
    assert verify_password("x", "wrong$prefix$abc$def") is False
    assert verify_password("x", f"{HASH_PREFIX}$abc$def$ghi") is False  # bad iter
    assert verify_password("x", f"{HASH_PREFIX}$1000$nothex$nothex") is False


def test_verify_password_lower_iterations_for_speed():
    # A quick hash with low iter count still verifies
    h = hash_password("fast", iterations=1000)
    assert verify_password("fast", h) is True


# ---------------------------------------------------------------------------
# generate_password
# ---------------------------------------------------------------------------

def test_generate_password_default_length():
    p = generate_password()
    assert len(p) == 28


def test_generate_password_excludes_ambiguous_chars():
    for _ in range(20):
        p = generate_password()
        assert "0" not in p and "O" not in p
        assert "1" not in p and "l" not in p and "I" not in p


def test_generate_password_is_random():
    seen = {generate_password() for _ in range(50)}
    # Even with collisions, 50 28-char passwords should produce 50 distinct
    assert len(seen) == 50


# ---------------------------------------------------------------------------
# auth_enabled / check_credentials
# ---------------------------------------------------------------------------

def test_auth_disabled_when_no_env(monkeypatch):
    monkeypatch.delenv("CG_AUTH_PASSWORD_HASH", raising=False)
    assert auth_enabled() is False
    assert check_credentials("admin", "anything") is False


def test_auth_disabled_when_empty_env(monkeypatch):
    monkeypatch.setenv("CG_AUTH_PASSWORD_HASH", "")
    assert auth_enabled() is False


def test_check_credentials_default_user(monkeypatch):
    monkeypatch.delenv("CG_AUTH_USER", raising=False)
    monkeypatch.setenv("CG_AUTH_PASSWORD_HASH", hash_password("pw"))
    assert auth_enabled() is True
    assert check_credentials("admin", "pw") is True
    assert check_credentials("admin", "wrong") is False
    assert check_credentials("other", "pw") is False


def test_check_credentials_custom_user(monkeypatch):
    monkeypatch.setenv("CG_AUTH_USER", "hustler")
    monkeypatch.setenv("CG_AUTH_PASSWORD_HASH", hash_password("pw"))
    assert check_credentials("hustler", "pw") is True
    assert check_credentials("admin", "pw") is False


# ---------------------------------------------------------------------------
# credentials_text / write_credentials_file
# ---------------------------------------------------------------------------

def test_credentials_text_contains_all_parts():
    h = hash_password("pw")
    text = credentials_text("hustler", "pw", h,
                              target_url="https://claudegravity.space")
    assert "hustler" in text
    assert "pw" in text
    assert h in text
    assert "claudegravity.space" in text
    assert "Keep this file private" in text


def test_write_credentials_file(tmp_path):
    h = hash_password("pw")
    dest = tmp_path / "creds.txt"
    out = write_credentials_file("hustler", "pw", h, dest=dest,
                                    target_url="https://example.test")
    assert out == dest
    assert dest.exists()
    content = dest.read_text(encoding="utf-8")
    assert "hustler" in content
    assert "pw" in content
    assert "example.test" in content
