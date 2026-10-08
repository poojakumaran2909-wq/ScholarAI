from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from pydantic import BaseModel, EmailStr, Field

import hashlib
import secrets
import os
import smtplib

from email.message import EmailMessage
from datetime import datetime, timedelta

from backendd.auth import (
    hash_password,
    verify_password,
    create_access_token,
    create_refresh_token,
    verify_access_token,
    verify_refresh_token,
)

from services.database import (
    create_user,
    get_user_by_email,
    get_user_by_id,

    # Password reset
    create_password_reset_token,
    get_valid_password_reset_tokens,
    mark_password_reset_token_used,
    update_user_password,

    # Email verification
    create_email_verification_token,
    get_valid_email_verification_tokens,
    mark_email_verification_token_used,
    mark_user_verified,
)


# ============================================================
# ROUTER
# ============================================================

router = APIRouter(
    prefix="/auth",
    tags=["Authentication"]
)

security = HTTPBearer()


# ============================================================
# EMAIL CONFIGURATION
# ============================================================

SMTP_HOST = os.getenv(
    "SMTP_HOST",
    "smtp.gmail.com"
)

SMTP_PORT = int(
    os.getenv(
        "SMTP_PORT",
        "587"
    )
)

SMTP_USERNAME = os.getenv(
    "SMTP_USERNAME",
    ""
)

SMTP_PASSWORD = os.getenv(
    "SMTP_PASSWORD",
    ""
)

SMTP_FROM_EMAIL = os.getenv(
    "SMTP_FROM_EMAIL",
    SMTP_USERNAME
)


# ============================================================
# SEND PASSWORD RESET EMAIL
# ============================================================

def send_password_reset_email(
    recipient_email: str,
    reset_token: str,
    expires_at: str
):
    """
    Send password reset token through Gmail SMTP.
    """

    if not SMTP_USERNAME or not SMTP_PASSWORD:
        raise RuntimeError(
            "SMTP email configuration is missing. "
            "Check SMTP_USERNAME and SMTP_PASSWORD in .env"
        )

    message = EmailMessage()

    message["Subject"] = "ScholarAI - Password Reset"
    message["From"] = SMTP_FROM_EMAIL
    message["To"] = recipient_email

    message.set_content(
        f"""
Hello,

We received a request to reset your ScholarAI account password.

Your password reset token is:

{reset_token}

This token will expire in 15 minutes.

Enter this token in the ScholarAI app to create a new password.

If you did not request a password reset, you can safely ignore this email.

For security reasons, do not share this token with anyone.

Regards,

ScholarAI Team
"""
    )

    try:

        with smtplib.SMTP(
            SMTP_HOST,
            SMTP_PORT,
            timeout=30
        ) as server:

            server.ehlo()
            server.starttls()
            server.ehlo()

            server.login(
                SMTP_USERNAME,
                SMTP_PASSWORD
            )

            server.send_message(
                message
            )

    except Exception as error:

        print(
            "Password reset email error:",
            str(error)
        )

        raise RuntimeError(
            "Unable to send password reset email."
        )


# ============================================================
# SEND EMAIL VERIFICATION OTP
# ============================================================

def send_verification_email(
    recipient_email: str,
    verification_code: str
):
    """
    Send email verification OTP through Gmail SMTP.
    """

    if not SMTP_USERNAME or not SMTP_PASSWORD:
        raise RuntimeError(
            "SMTP email configuration is missing."
        )

    message = EmailMessage()

    message["Subject"] = "ScholarAI - Verify Your Email"
    message["From"] = SMTP_FROM_EMAIL
    message["To"] = recipient_email

    message.set_content(
        f"""
Hello,

Welcome to ScholarAI!

Your email verification code is:

{verification_code}

This code will expire in 10 minutes.

Enter this code in the ScholarAI app to verify your email address.

If you did not create a ScholarAI account, you can safely ignore this email.

Regards,

ScholarAI Team
"""
    )

    try:

        with smtplib.SMTP(
            SMTP_HOST,
            SMTP_PORT,
            timeout=30
        ) as server:

            server.ehlo()
            server.starttls()
            server.ehlo()

            server.login(
                SMTP_USERNAME,
                SMTP_PASSWORD
            )

            server.send_message(
                message
            )

    except Exception as error:

        print(
            "Verification email error:",
            str(error)
        )

        raise RuntimeError(
            "Unable to send verification email."
        )


# ============================================================
# REQUEST SCHEMAS
# ============================================================

class RegisterRequest(BaseModel):

    email: EmailStr

    password: str = Field(
        min_length=8,
        max_length=128
    )


class LoginRequest(BaseModel):

    email: EmailStr

    password: str


class RefreshRequest(BaseModel):

    refresh_token: str


class ForgotPasswordRequest(BaseModel):

    email: EmailStr


class VerifyEmailRequest(BaseModel):

    email: EmailStr

    verification_code: str = Field(
        min_length=6,
        max_length=6
    )


class ResendVerificationRequest(BaseModel):

    email: EmailStr


class ResetPasswordRequest(BaseModel):

    email: EmailStr

    reset_token: str

    new_password: str = Field(
        min_length=8,
        max_length=128
    )


# ============================================================
# RESPONSE HELPERS
# ============================================================

def user_response(user):

    return {
        "id": user["id"],
        "email": user["email"],
        "is_verified": bool(
            user["is_verified"]
        ),
        "created_at": user["created_at"],
    }


# ============================================================
# REGISTER
# ============================================================

@router.post("/register")
def register(
    request: RegisterRequest
):

    email = request.email.strip().lower()

    # --------------------------------------------------------
    # CHECK EXISTING USER
    # --------------------------------------------------------

    existing_user = get_user_by_email(
        email
    )

    if existing_user:

        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An account with this email already exists."
        )

    # --------------------------------------------------------
    # HASH PASSWORD
    # --------------------------------------------------------

    password_hash = hash_password(
        request.password
    )

    # --------------------------------------------------------
    # CREATE USER
    # --------------------------------------------------------

    user = create_user(
        email=email,
        password_hash=password_hash
    )

    if user is None:

        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An account with this email already exists."
        )

    # --------------------------------------------------------
    # GENERATE 6-DIGIT VERIFICATION CODE
    # --------------------------------------------------------

    verification_code = str(
        secrets.randbelow(1000000)
    ).zfill(6)

    # --------------------------------------------------------
    # HASH VERIFICATION CODE
    # --------------------------------------------------------

    token_hash = hashlib.sha256(
        verification_code.encode("utf-8")
    ).hexdigest()

    # --------------------------------------------------------
    # EXPIRE AFTER 10 MINUTES
    # --------------------------------------------------------

    expires_at = (
        datetime.now()
        + timedelta(minutes=10)
    ).isoformat(
        timespec="seconds"
    )

    # --------------------------------------------------------
    # STORE HASH
    # --------------------------------------------------------

    create_email_verification_token(
        user_id=user["id"],
        token_hash=token_hash,
        expires_at=expires_at
    )

    # --------------------------------------------------------
    # SEND VERIFICATION EMAIL
    # --------------------------------------------------------

    try:

        send_verification_email(
            recipient_email=email,
            verification_code=verification_code
        )

    except Exception as error:

        print(
            "Verification email failed:",
            str(error)
        )

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=(
                "Account was created, but verification email "
                "could not be sent. Please use resend verification."
            )
        )

    return {
        "message": (
            "Account created successfully. "
            "A verification code has been sent to your email."
        ),
        "user": user_response(user)
    }


# ============================================================
# VERIFY EMAIL
# ============================================================

@router.post("/verify-email")
def verify_email(
    request: VerifyEmailRequest
):

    email = request.email.strip().lower()

    # --------------------------------------------------------
    # FIND USER
    # --------------------------------------------------------

    user = get_user_by_email(
        email
    )

    if user is None:

        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid verification request."
        )

    # --------------------------------------------------------
    # ALREADY VERIFIED
    # --------------------------------------------------------

    if bool(user["is_verified"]):

        return {
            "message": "Email is already verified."
        }

    # --------------------------------------------------------
    # HASH PROVIDED CODE
    # --------------------------------------------------------

    provided_hash = hashlib.sha256(
        request.verification_code.encode("utf-8")
    ).hexdigest()

    # --------------------------------------------------------
    # GET UNUSED TOKENS
    # --------------------------------------------------------

    tokens = get_valid_email_verification_tokens(
        user["id"]
    )

    matching_token = None

    for token in tokens:

        if token["token_hash"] != provided_hash:
            continue

        # ----------------------------------------------------
        # CHECK EXPIRATION
        # ----------------------------------------------------

        try:

            expires_at = datetime.fromisoformat(
                token["expires_at"]
            )

        except ValueError:

            continue

        if datetime.now() > expires_at:

            continue

        matching_token = token

        break

    # --------------------------------------------------------
    # INVALID / EXPIRED CODE
    # --------------------------------------------------------

    if matching_token is None:

        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired verification code."
        )

    # --------------------------------------------------------
    # MARK USER VERIFIED
    # --------------------------------------------------------

    verified = mark_user_verified(
        user["id"]
    )

    if not verified:

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Could not verify email."
        )

    # --------------------------------------------------------
    # MARK TOKEN USED
    # --------------------------------------------------------

    mark_email_verification_token_used(
        matching_token["id"]
    )

    return {
        "message": (
            "Email verified successfully. "
            "You can now login."
        )
    }


# ============================================================
# RESEND EMAIL VERIFICATION
# ============================================================

@router.post("/resend-verification")
def resend_verification(
    request: ResendVerificationRequest
):

    email = request.email.strip().lower()

    # --------------------------------------------------------
    # FIND USER
    # --------------------------------------------------------

    user = get_user_by_email(
        email
    )

    # Don't reveal whether the email exists
    if user is None:

        return {
            "message": (
                "If an unverified account exists with this email, "
                "a new verification code has been sent."
            )
        }

    # --------------------------------------------------------
    # ALREADY VERIFIED
    # --------------------------------------------------------

    if bool(user["is_verified"]):

        return {
            "message": "Email is already verified."
        }

    # --------------------------------------------------------
    # GENERATE NEW 6-DIGIT CODE
    # --------------------------------------------------------

    verification_code = str(
        secrets.randbelow(1000000)
    ).zfill(6)

    # --------------------------------------------------------
    # HASH VERIFICATION CODE
    # --------------------------------------------------------

    token_hash = hashlib.sha256(
        verification_code.encode("utf-8")
    ).hexdigest()

    # --------------------------------------------------------
    # EXPIRE AFTER 10 MINUTES
    # --------------------------------------------------------

    expires_at = (
        datetime.now()
        + timedelta(minutes=10)
    ).isoformat(
        timespec="seconds"
    )

    # --------------------------------------------------------
    # STORE HASH
    # --------------------------------------------------------

    create_email_verification_token(
        user_id=user["id"],
        token_hash=token_hash,
        expires_at=expires_at
    )

    # --------------------------------------------------------
    # SEND EMAIL
    # --------------------------------------------------------

    try:

        send_verification_email(
            recipient_email=email,
            verification_code=verification_code
        )

    except Exception as error:

        print(
            "Resend verification email failed:",
            str(error)
        )

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=(
                "Unable to send verification email. "
                "Please try again later."
            )
        )

    # --------------------------------------------------------
    # SUCCESS
    # --------------------------------------------------------

    return {
        "message": (
            "A new verification code has been sent "
            "to your email."
        )
    }


# ============================================================
# LOGIN
# ============================================================

@router.post("/login")
def login(
    request: LoginRequest
):

    email = request.email.strip().lower()

    user = get_user_by_email(
        email
    )

    # --------------------------------------------------------
    # GENERIC ERROR
    # --------------------------------------------------------

    if user is None:

        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password.",
            headers={
                "WWW-Authenticate": "Bearer"
            }
        )

    # --------------------------------------------------------
    # VERIFY PASSWORD
    # --------------------------------------------------------

    password_valid = verify_password(
        request.password,
        user["password_hash"]
    )

    if not password_valid:

        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password.",
            headers={
                "WWW-Authenticate": "Bearer"
            }
        )

    # --------------------------------------------------------
    # CHECK EMAIL VERIFICATION
    # --------------------------------------------------------

    if not bool(user["is_verified"]):

        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=(
                "Please verify your email before logging in."
            )
        )

    # --------------------------------------------------------
    # CREATE TOKENS
    # --------------------------------------------------------

    access_token = create_access_token(
        user_id=user["id"],
        email=user["email"]
    )

    refresh_token = create_refresh_token(
        user_id=user["id"],
        email=user["email"]
    )

    return {
        "message": "Login successful.",
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
        "user": user_response(user)
    }


# ============================================================
# REFRESH ACCESS TOKEN
# ============================================================

@router.post("/refresh")
def refresh(
    request: RefreshRequest
):

    try:

        payload = verify_refresh_token(
            request.refresh_token
        )

    except Exception:

        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired refresh token.",
            headers={
                "WWW-Authenticate": "Bearer"
            }
        )

    user_id = payload.get(
        "sub"
    )

    email = payload.get(
        "email"
    )

    if not user_id or not email:

        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token.",
            headers={
                "WWW-Authenticate": "Bearer"
            }
        )

    # --------------------------------------------------------
    # MAKE SURE USER STILL EXISTS
    # --------------------------------------------------------

    user = get_user_by_id(
        user_id
    )

    if user is None:

        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User no longer exists.",
            headers={
                "WWW-Authenticate": "Bearer"
            }
        )

    # --------------------------------------------------------
    # CREATE NEW ACCESS TOKEN
    # --------------------------------------------------------

    access_token = create_access_token(
        user_id=user["id"],
        email=user["email"]
    )

    return {
        "access_token": access_token,
        "token_type": "bearer"
    }


# ============================================================
# FORGOT PASSWORD
# ============================================================

@router.post("/forgot-password")
def forgot_password(
    request: ForgotPasswordRequest
):

    email = request.email.strip().lower()

    user = get_user_by_email(
        email
    )

    # --------------------------------------------------------
    # ALWAYS RETURN SAME MESSAGE
    #
    # This prevents attackers from discovering
    # whether an email is registered.
    # --------------------------------------------------------

    generic_message = (
        "If an account with this email exists, "
        "a password reset request has been created."
    )

    if user is None:

        return {
            "message": generic_message
        }

    # --------------------------------------------------------
    # GENERATE SECURE RANDOM TOKEN
    # --------------------------------------------------------

    reset_token = secrets.token_urlsafe(
        32
    )

    # --------------------------------------------------------
    # HASH TOKEN BEFORE DATABASE STORAGE
    # --------------------------------------------------------

    token_hash = hashlib.sha256(
        reset_token.encode("utf-8")
    ).hexdigest()

    # --------------------------------------------------------
    # TOKEN EXPIRATION
    # 15 MINUTES
    # --------------------------------------------------------

    expires_at = (
        datetime.now()
        + timedelta(minutes=15)
    ).isoformat(
        timespec="seconds"
    )

    # --------------------------------------------------------
    # SAVE HASH
    # --------------------------------------------------------

    create_password_reset_token(
        user_id=user["id"],
        token_hash=token_hash,
        expires_at=expires_at
    )

    # --------------------------------------------------------
    # SEND RESET EMAIL
    # --------------------------------------------------------

    try:

        send_password_reset_email(
            recipient_email=email,
            reset_token=reset_token,
            expires_at=expires_at
        )

    except Exception as error:

        print(
            "Password reset email failed:",
            str(error)
        )

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=(
                "Unable to send password reset email. "
                "Please try again later."
            )
        )

    return {
        "message": generic_message
    }


# ============================================================
# RESET PASSWORD
# ============================================================

@router.post("/reset-password")
def reset_password(
    request: ResetPasswordRequest
):

    email = request.email.strip().lower()

    # --------------------------------------------------------
    # FIND USER
    # --------------------------------------------------------

    user = get_user_by_email(
        email
    )

    if user is None:

        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired reset request."
        )

    # --------------------------------------------------------
    # HASH PROVIDED TOKEN
    # --------------------------------------------------------

    provided_token_hash = hashlib.sha256(
        request.reset_token.encode("utf-8")
    ).hexdigest()

    # --------------------------------------------------------
    # GET UNUSED TOKENS
    # --------------------------------------------------------

    tokens = get_valid_password_reset_tokens(
        user["id"]
    )

    matching_token = None

    for token in tokens:

        if token["token_hash"] != provided_token_hash:
            continue

        # ----------------------------------------------------
        # CHECK EXPIRATION
        # ----------------------------------------------------

        try:

            expires_at = datetime.fromisoformat(
                token["expires_at"]
            )

        except ValueError:

            continue

        if datetime.now() > expires_at:

            continue

        matching_token = token

        break

    # --------------------------------------------------------
    # INVALID TOKEN
    # --------------------------------------------------------

    if matching_token is None:

        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired reset request."
        )

    # --------------------------------------------------------
    # HASH NEW PASSWORD
    # --------------------------------------------------------

    new_password_hash = hash_password(
        request.new_password
    )

    # --------------------------------------------------------
    # UPDATE PASSWORD
    # --------------------------------------------------------

    updated = update_user_password(
        user_id=user["id"],
        password_hash=new_password_hash
    )

    if not updated:

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Could not update password."
        )

    # --------------------------------------------------------
    # MARK TOKEN AS USED
    # --------------------------------------------------------

    mark_password_reset_token_used(
        matching_token["id"]
    )

    return {
        "message": (
            "Password reset successful. "
            "You can now log in with your new password."
        )
    }


# ============================================================
# GET CURRENT USER
# ============================================================

@router.get("/me")
def get_current_user(
    credentials: HTTPAuthorizationCredentials =
        Depends(security)
):

    token = credentials.credentials

    try:

        payload = verify_access_token(
            token
        )

    except Exception:

        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired access token.",
            headers={
                "WWW-Authenticate": "Bearer"
            }
        )

    user_id = payload.get(
        "sub"
    )

    if not user_id:

        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid access token.",
            headers={
                "WWW-Authenticate": "Bearer"
            }
        )

    user = get_user_by_id(
        user_id
    )

    if user is None:

        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found.",
            headers={
                "WWW-Authenticate": "Bearer"
            }
        )

    return {
        "user": user_response(user)
    }