import os
from dotenv import load_dotenv

load_dotenv()
from datetime import datetime, timedelta, timezone

import jwt
from pwdlib import PasswordHash


# ============================================================
# CONFIGURATION
# ============================================================

SECRET_KEY = os.getenv(
    "SCHOLARAI_JWT_SECRET",
    ""
)

ALGORITHM = "HS256"

ACCESS_TOKEN_EXPIRE_MINUTES = 15

REFRESH_TOKEN_EXPIRE_DAYS = 30


# ============================================================
# PASSWORD HASHING
# ============================================================

password_hash = PasswordHash.recommended()


def hash_password(password: str) -> str:

    return password_hash.hash(password)


def verify_password(
    plain_password: str,
    hashed_password: str
) -> bool:

    return password_hash.verify(
        plain_password,
        hashed_password
    )


# ============================================================
# JWT SECRET VALIDATION
# ============================================================

def validate_jwt_secret():

    if not SECRET_KEY:

        raise RuntimeError(
            "SCHOLARAI_JWT_SECRET is not configured. "
            "Add a strong secret key to your environment variables."
        )


# ============================================================
# CREATE ACCESS TOKEN
# ============================================================

def create_access_token(
    user_id: str,
    email: str
) -> str:

    validate_jwt_secret()

    now = datetime.now(timezone.utc)

    expires_at = (
        now +
        timedelta(
            minutes=ACCESS_TOKEN_EXPIRE_MINUTES
        )
    )

    payload = {
        "sub": user_id,
        "email": email,
        "type": "access",
        "iat": now,
        "exp": expires_at,
    }

    return jwt.encode(
        payload,
        SECRET_KEY,
        algorithm=ALGORITHM
    )


# ============================================================
# CREATE REFRESH TOKEN
# ============================================================

def create_refresh_token(
    user_id: str,
    email: str
) -> str:

    validate_jwt_secret()

    now = datetime.now(timezone.utc)

    expires_at = (
        now +
        timedelta(
            days=REFRESH_TOKEN_EXPIRE_DAYS
        )
    )

    payload = {
        "sub": user_id,
        "email": email,
        "type": "refresh",
        "iat": now,
        "exp": expires_at,
    }

    return jwt.encode(
        payload,
        SECRET_KEY,
        algorithm=ALGORITHM
    )


# ============================================================
# DECODE TOKEN
# ============================================================

def decode_token(token: str) -> dict:

    validate_jwt_secret()

    return jwt.decode(
        token,
        SECRET_KEY,
        algorithms=[ALGORITHM]
    )


# ============================================================
# VERIFY TOKEN TYPE
# ============================================================

def verify_access_token(
    token: str
) -> dict:

    payload = decode_token(token)

    if payload.get("type") != "access":

        raise ValueError(
            "Invalid access token"
        )

    return payload


def verify_refresh_token(
    token: str
) -> dict:

    payload = decode_token(token)

    if payload.get("type") != "refresh":

        raise ValueError(
            "Invalid refresh token"
        )

    return payload