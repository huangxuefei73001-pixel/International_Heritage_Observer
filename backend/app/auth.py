from __future__ import annotations

import hashlib
import secrets

_PBKDF2_ALGORITHM = "pbkdf2_sha256"
_PBKDF2_ITERATIONS = 120_000
_PBKDF2_SALT_BYTES = 16


def build_login_code() -> tuple[str, str]:
    plain_code = f"{secrets.randbelow(999_999) + 1:06d}"
    salt = secrets.token_bytes(_PBKDF2_SALT_BYTES)
    digest = hashlib.pbkdf2_hmac(
        "sha256",
        plain_code.encode("utf-8"),
        salt,
        _PBKDF2_ITERATIONS,
    ).hex()
    stored_hash = f"{_PBKDF2_ALGORITHM}${_PBKDF2_ITERATIONS}${salt.hex()}${digest}"
    return stored_hash, plain_code


def verify_login_code(plain_code: str, stored_hash: str) -> bool:
    try:
        algorithm, iterations, salt_hex, digest = stored_hash.split("$", 3)
    except ValueError:
        return False

    if algorithm != _PBKDF2_ALGORITHM:
        return False

    try:
        candidate_digest = hashlib.pbkdf2_hmac(
            "sha256",
            plain_code.encode("utf-8"),
            bytes.fromhex(salt_hex),
            int(iterations),
        ).hex()
    except ValueError:
        return False

    return secrets.compare_digest(candidate_digest, digest)
