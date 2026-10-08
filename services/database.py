import os
import uuid
from datetime import datetime

import psycopg2
from psycopg2.extras import RealDictCursor
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    raise RuntimeError(
        "DATABASE_URL is missing from .env"
    )


# ============================================================
# DATABASE CONNECTION
# ============================================================

def get_connection():
    return psycopg2.connect(
        DATABASE_URL
    )


# ============================================================
# HELPERS
# ============================================================

def _get_user_id(cursor, email):
    cursor.execute(
        """
        SELECT id
        FROM users
        WHERE LOWER(email) = LOWER(%s)
        """,
        (email,)
    )

    row = cursor.fetchone()

    if row is None:
        return None

    return row["id"] if isinstance(row, dict) else row[0]


# ============================================================
# CREATE TABLES
# ============================================================

def init_db():

    connection = get_connection()
    cursor = connection.cursor()

    try:

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS users (
                id TEXT PRIMARY KEY,
                email TEXT NOT NULL UNIQUE,
                password_hash TEXT NOT NULL,
                is_verified BOOLEAN NOT NULL DEFAULT FALSE,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
            """
        )

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS student_profiles (
                user_id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                education_level TEXT,
                course TEXT,
                category TEXT,
                gender TEXT,
                state TEXT,
                year TEXT,
                marks DOUBLE PRECISION,
                family_income DOUBLE PRECISION,

                FOREIGN KEY (user_id)
                    REFERENCES users(id)
                    ON DELETE CASCADE
            )
            """
        )

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS saved_scholarships (
                id BIGSERIAL PRIMARY KEY,
                user_id TEXT NOT NULL,
                scholarship_id TEXT NOT NULL,
                scholarship_name TEXT NOT NULL,
                deadline TEXT,
                status TEXT DEFAULT 'saved',
                saved_at TEXT NOT NULL,

                UNIQUE(user_id, scholarship_id),

                FOREIGN KEY (user_id)
                    REFERENCES users(id)
                    ON DELETE CASCADE
            )
            """
        )

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS password_reset_tokens (
                id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                token_hash TEXT NOT NULL,
                expires_at TEXT NOT NULL,
                used BOOLEAN NOT NULL DEFAULT FALSE,
                created_at TEXT NOT NULL,

                FOREIGN KEY (user_id)
                    REFERENCES users(id)
                    ON DELETE CASCADE
            )
            """
        )

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS email_verification_tokens (
                id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                token_hash TEXT NOT NULL,
                expires_at TEXT NOT NULL,
                used BOOLEAN NOT NULL DEFAULT FALSE,
                created_at TEXT NOT NULL,

                FOREIGN KEY (user_id)
                    REFERENCES users(id)
                    ON DELETE CASCADE
            )
            """
        )

        connection.commit()

    except Exception:
        connection.rollback()
        raise

    finally:
        cursor.close()
        connection.close()


# ============================================================
# USER / AUTHENTICATION
# ============================================================

def create_user(email, password_hash):

    connection = get_connection()
    cursor = connection.cursor(
        cursor_factory=RealDictCursor
    )

    user_id = str(uuid.uuid4())

    now = datetime.now().isoformat(
        timespec="seconds"
    )

    try:

        cursor.execute(
            """
            INSERT INTO users (
                id,
                email,
                password_hash,
                is_verified,
                created_at,
                updated_at
            )
            VALUES (%s, %s, %s, %s, %s, %s)
            """,
            (
                user_id,
                email,
                password_hash,
                False,
                now,
                now
            )
        )

        connection.commit()

        return {
            "id": user_id,
            "email": email,
            "is_verified": False,
            "created_at": now,
            "updated_at": now
        }

    except psycopg2.IntegrityError:

        connection.rollback()

        return None

    finally:

        cursor.close()
        connection.close()


def get_user_by_email(email):

    connection = get_connection()
    cursor = connection.cursor(
        cursor_factory=RealDictCursor
    )

    cursor.execute(
        """
        SELECT
            id,
            email,
            password_hash,
            is_verified,
            created_at,
            updated_at
        FROM users
        WHERE LOWER(email) = LOWER(%s)
        """,
        (email,)
    )

    row = cursor.fetchone()

    cursor.close()
    connection.close()

    if row is None:
        return None

    return dict(row)


def get_user_by_id(user_id):

    connection = get_connection()
    cursor = connection.cursor(
        cursor_factory=RealDictCursor
    )

    cursor.execute(
        """
        SELECT
            id,
            email,
            password_hash,
            is_verified,
            created_at,
            updated_at
        FROM users
        WHERE id = %s
        """,
        (user_id,)
    )

    row = cursor.fetchone()

    cursor.close()
    connection.close()

    if row is None:
        return None

    return dict(row)


def user_exists(email):

    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute(
        """
        SELECT id
        FROM users
        WHERE LOWER(email) = LOWER(%s)
        """,
        (email,)
    )

    row = cursor.fetchone()

    cursor.close()
    connection.close()

    return row is not None


def update_user_timestamp(user_id):

    connection = get_connection()
    cursor = connection.cursor()

    now = datetime.now().isoformat(
        timespec="seconds"
    )

    cursor.execute(
        """
        UPDATE users
        SET updated_at = %s
        WHERE id = %s
        """,
        (now, user_id)
    )

    updated = cursor.rowcount > 0

    connection.commit()

    cursor.close()
    connection.close()

    return updated


def mark_user_verified(user_id):

    connection = get_connection()
    cursor = connection.cursor()

    now = datetime.now().isoformat(
        timespec="seconds"
    )

    cursor.execute(
        """
        UPDATE users
        SET
            is_verified = TRUE,
            updated_at = %s
        WHERE id = %s
        """,
        (now, user_id)
    )

    updated = cursor.rowcount > 0

    connection.commit()

    cursor.close()
    connection.close()

    return updated


# ============================================================
# PROFILE
# ============================================================

def save_profile(profile):

    connection = get_connection()
    cursor = connection.cursor()

    user_id = _get_user_id(
        cursor,
        profile.email
    )

    if user_id is None:

        cursor.close()
        connection.close()

        return False

    cursor.execute(
        """
        INSERT INTO student_profiles (
            user_id,
            name,
            education_level,
            course,
            category,
            gender,
            state,
            year,
            marks,
            family_income
        )
        VALUES (
            %s, %s, %s, %s, %s,
            %s, %s, %s, %s, %s
        )

        ON CONFLICT(user_id)
        DO UPDATE SET
            name = EXCLUDED.name,
            education_level = EXCLUDED.education_level,
            course = EXCLUDED.course,
            category = EXCLUDED.category,
            gender = EXCLUDED.gender,
            state = EXCLUDED.state,
            year = EXCLUDED.year,
            marks = EXCLUDED.marks,
            family_income = EXCLUDED.family_income
        """,
        (
            user_id,
            profile.name,
            profile.education_level,
            profile.course,
            profile.category,
            profile.gender,
            profile.state,
            profile.year,
            profile.marks,
            profile.family_income
        )
    )

    connection.commit()

    cursor.close()
    connection.close()

    return True


def get_profile(email):

    connection = get_connection()

    cursor = connection.cursor(
        cursor_factory=RealDictCursor
    )

    cursor.execute(
        """
        SELECT
            u.email,
            p.name,
            p.education_level,
            p.course,
            p.category,
            p.gender,
            p.state,
            p.year,
            p.marks,
            p.family_income
        FROM student_profiles p
        JOIN users u
            ON u.id = p.user_id
        WHERE LOWER(u.email) = LOWER(%s)
        """,
        (email,)
    )

    row = cursor.fetchone()

    cursor.close()
    connection.close()

    if row is None:
        return None

    return dict(row)


# ============================================================
# SAVED SCHOLARSHIPS
# ============================================================

def save_scholarship(
    email,
    scholarship_id,
    scholarship_name,
    deadline=None
):

    connection = get_connection()

    cursor = connection.cursor()

    user_id = _get_user_id(
        cursor,
        email
    )

    if user_id is None:

        cursor.close()
        connection.close()

        return False

    saved_at = datetime.now().isoformat(
        timespec="seconds"
    )

    cursor.execute(
        """
        INSERT INTO saved_scholarships (
            user_id,
            scholarship_id,
            scholarship_name,
            deadline,
            status,
            saved_at
        )
        VALUES (%s, %s, %s, %s, %s, %s)

        ON CONFLICT(user_id, scholarship_id)
        DO UPDATE SET
            scholarship_name =
                EXCLUDED.scholarship_name,
            deadline =
                EXCLUDED.deadline
        """,
        (
            user_id,
            scholarship_id,
            scholarship_name,
            deadline,
            "saved",
            saved_at
        )
    )

    connection.commit()

    cursor.close()
    connection.close()

    return True


def get_saved_scholarships(email):

    connection = get_connection()

    cursor = connection.cursor(
        cursor_factory=RealDictCursor
    )

    cursor.execute(
        """
        SELECT
            s.id,
            u.email,
            s.scholarship_id,
            s.scholarship_name,
            s.deadline,
            s.status,
            s.saved_at
        FROM saved_scholarships s
        JOIN users u
            ON u.id = s.user_id
        WHERE LOWER(u.email) = LOWER(%s)
        ORDER BY s.saved_at DESC
        """,
        (email,)
    )

    rows = cursor.fetchall()

    cursor.close()
    connection.close()

    return [dict(row) for row in rows]


def remove_saved_scholarship(
    email,
    scholarship_id
):

    connection = get_connection()

    cursor = connection.cursor()

    user_id = _get_user_id(
        cursor,
        email
    )

    if user_id is None:

        cursor.close()
        connection.close()

        return False

    cursor.execute(
        """
        DELETE FROM saved_scholarships
        WHERE user_id = %s
        AND scholarship_id = %s
        """,
        (
            user_id,
            scholarship_id
        )
    )

    deleted = cursor.rowcount > 0

    connection.commit()

    cursor.close()
    connection.close()

    return deleted


def update_scholarship_status(
    email,
    scholarship_id,
    status
):

    allowed_statuses = {
        "saved",
        "applied",
        "not_applied"
    }

    if status not in allowed_statuses:
        return False

    connection = get_connection()

    cursor = connection.cursor()

    user_id = _get_user_id(
        cursor,
        email
    )

    if user_id is None:

        cursor.close()
        connection.close()

        return False

    cursor.execute(
        """
        UPDATE saved_scholarships
        SET status = %s
        WHERE user_id = %s
        AND scholarship_id = %s
        """,
        (
            status,
            user_id,
            scholarship_id
        )
    )

    updated = cursor.rowcount > 0

    connection.commit()

    cursor.close()
    connection.close()

    return updated


# ============================================================
# PASSWORD RESET
# ============================================================

def create_password_reset_token(
    user_id,
    token_hash,
    expires_at
):

    connection = get_connection()
    cursor = connection.cursor()

    token_id = str(uuid.uuid4())

    created_at = datetime.now().isoformat(
        timespec="seconds"
    )

    cursor.execute(
        """
        INSERT INTO password_reset_tokens (
            id,
            user_id,
            token_hash,
            expires_at,
            used,
            created_at
        )
        VALUES (%s, %s, %s, %s, %s, %s)
        """,
        (
            token_id,
            user_id,
            token_hash,
            expires_at,
            False,
            created_at
        )
    )

    connection.commit()

    cursor.close()
    connection.close()

    return token_id


def get_valid_password_reset_tokens(user_id):

    connection = get_connection()

    cursor = connection.cursor(
        cursor_factory=RealDictCursor
    )

    cursor.execute(
        """
        SELECT
            id,
            user_id,
            token_hash,
            expires_at,
            used,
            created_at
        FROM password_reset_tokens
        WHERE user_id = %s
        AND used = FALSE
        ORDER BY created_at DESC
        """,
        (user_id,)
    )

    rows = cursor.fetchall()

    cursor.close()
    connection.close()

    return [dict(row) for row in rows]


def mark_password_reset_token_used(
    token_id
):

    connection = get_connection()

    cursor = connection.cursor()

    cursor.execute(
        """
        UPDATE password_reset_tokens
        SET used = TRUE
        WHERE id = %s
        """,
        (token_id,)
    )

    updated = cursor.rowcount > 0

    connection.commit()

    cursor.close()
    connection.close()

    return updated


def update_user_password(
    user_id,
    password_hash
):

    connection = get_connection()

    cursor = connection.cursor()

    now = datetime.now().isoformat(
        timespec="seconds"
    )

    cursor.execute(
        """
        UPDATE users
        SET
            password_hash = %s,
            updated_at = %s
        WHERE id = %s
        """,
        (
            password_hash,
            now,
            user_id
        )
    )

    updated = cursor.rowcount > 0

    connection.commit()

    cursor.close()
    connection.close()

    return updated


# ============================================================
# EMAIL VERIFICATION
# ============================================================

def create_email_verification_token(
    user_id,
    token_hash,
    expires_at
):

    connection = get_connection()

    cursor = connection.cursor()

    token_id = str(uuid.uuid4())

    created_at = datetime.now().isoformat(
        timespec="seconds"
    )

    cursor.execute(
        """
        INSERT INTO email_verification_tokens (
            id,
            user_id,
            token_hash,
            expires_at,
            used,
            created_at
        )
        VALUES (%s, %s, %s, %s, %s, %s)
        """,
        (
            token_id,
            user_id,
            token_hash,
            expires_at,
            False,
            created_at
        )
    )

    connection.commit()

    cursor.close()
    connection.close()

    return token_id


def get_valid_email_verification_tokens(
    user_id
):

    connection = get_connection()

    cursor = connection.cursor(
        cursor_factory=RealDictCursor
    )

    cursor.execute(
        """
        SELECT
            id,
            user_id,
            token_hash,
            expires_at,
            used,
            created_at
        FROM email_verification_tokens
        WHERE user_id = %s
        AND used = FALSE
        ORDER BY created_at DESC
        """,
        (user_id,)
    )

    rows = cursor.fetchall()

    cursor.close()
    connection.close()

    return [dict(row) for row in rows]


def mark_email_verification_token_used(
    token_id
):

    connection = get_connection()

    cursor = connection.cursor()

    cursor.execute(
        """
        UPDATE email_verification_tokens
        SET used = TRUE
        WHERE id = %s
        """,
        (token_id,)
    )

    updated = cursor.rowcount > 0

    connection.commit()

    cursor.close()
    connection.close()

    return updated