import os
import sqlite3
import psycopg2
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    raise RuntimeError("DATABASE_URL is missing from .env")

BASE_DIR = os.path.dirname(
    os.path.dirname(os.path.abspath(__file__))
)

SQLITE_DB = os.path.join(
    BASE_DIR,
    "data",
    "scholarai.db"
)


def create_postgres_schema(pg):
    cur = pg.cursor()

    print("\nCreating PostgreSQL tables...")

    cur.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id TEXT PRIMARY KEY,
            email TEXT NOT NULL UNIQUE,
            password_hash TEXT NOT NULL,
            is_verified BOOLEAN NOT NULL DEFAULT FALSE,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )
    """)

    cur.execute("""
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
    """)

    cur.execute("""
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
    """)

    cur.execute("""
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
    """)

    cur.execute("""
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
    """)

    pg.commit()
    cur.close()

    print("PostgreSQL tables created.")


def table_exists_sqlite(sqlite, table_name):
    cur = sqlite.cursor()

    cur.execute("""
        SELECT name
        FROM sqlite_master
        WHERE type='table'
        AND name=?
    """, (table_name,))

    exists = cur.fetchone() is not None
    cur.close()

    return exists


def migrate_users(sqlite, pg):
    src = sqlite.cursor()
    dst = pg.cursor()

    src.execute("""
        SELECT
            id,
            email,
            password_hash,
            is_verified,
            created_at,
            updated_at
        FROM users
    """)

    rows = src.fetchall()

    for row in rows:
        dst.execute("""
            INSERT INTO users (
                id,
                email,
                password_hash,
                is_verified,
                created_at,
                updated_at
            )
            VALUES (%s, %s, %s, %s, %s, %s)
            ON CONFLICT (id)
            DO UPDATE SET
                email = EXCLUDED.email,
                password_hash = EXCLUDED.password_hash,
                is_verified = EXCLUDED.is_verified,
                updated_at = EXCLUDED.updated_at
        """, (
            row[0],
            row[1],
            row[2],
            bool(row[3]),
            row[4],
            row[5]
        ))

    pg.commit()

    src.close()
    dst.close()

    print(f"Users migrated: {len(rows)}")


def migrate_profiles(sqlite, pg):
    src = sqlite.cursor()
    dst = pg.cursor()

    src.execute("""
        SELECT
            email,
            name,
            education_level,
            course,
            category,
            gender,
            state,
            year,
            marks,
            family_income
        FROM student_profiles
    """)

    rows = src.fetchall()

    migrated = 0

    for row in rows:
        email = row[0]

        dst.execute("""
            SELECT id
            FROM users
            WHERE LOWER(email) = LOWER(%s)
        """, (email,))

        user = dst.fetchone()

        if not user:
            print(f"Skipping profile - user not found: {email}")
            continue

        user_id = user[0]

        dst.execute("""
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
            ON CONFLICT (user_id)
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
        """, (
            user_id,
            row[1],
            row[2],
            row[3],
            row[4],
            row[5],
            row[6],
            row[7],
            row[8],
            row[9]
        ))

        migrated += 1

    pg.commit()

    src.close()
    dst.close()

    print(f"Profiles migrated: {migrated}")


def migrate_saved_scholarships(sqlite, pg):
    src = sqlite.cursor()
    dst = pg.cursor()

    src.execute("""
        SELECT
            email,
            scholarship_id,
            scholarship_name,
            deadline,
            status,
            saved_at
        FROM saved_scholarships
    """)

    rows = src.fetchall()

    migrated = 0

    for row in rows:
        email = row[0]

        dst.execute("""
            SELECT id
            FROM users
            WHERE LOWER(email) = LOWER(%s)
        """, (email,))

        user = dst.fetchone()

        if not user:
            print(
                f"Skipping saved scholarship - "
                f"user not found: {email}"
            )
            continue

        user_id = user[0]

        dst.execute("""
            INSERT INTO saved_scholarships (
                user_id,
                scholarship_id,
                scholarship_name,
                deadline,
                status,
                saved_at
            )
            VALUES (%s, %s, %s, %s, %s, %s)
            ON CONFLICT (user_id, scholarship_id)
            DO UPDATE SET
                scholarship_name = EXCLUDED.scholarship_name,
                deadline = EXCLUDED.deadline,
                status = EXCLUDED.status
        """, (
            user_id,
            row[1],
            row[2],
            row[3],
            row[4],
            row[5]
        ))

        migrated += 1

    pg.commit()

    src.close()
    dst.close()

    print(f"Saved scholarships migrated: {migrated}")


def migrate_tokens(sqlite, pg, table_name):
    if not table_exists_sqlite(sqlite, table_name):
        print(f"{table_name}: source table not found, skipping.")
        return

    src = sqlite.cursor()
    dst = pg.cursor()

    src.execute(f"""
        SELECT
            id,
            user_id,
            token_hash,
            expires_at,
            used,
            created_at
        FROM {table_name}
    """)

    rows = src.fetchall()

    for row in rows:
        dst.execute(f"""
            INSERT INTO {table_name} (
                id,
                user_id,
                token_hash,
                expires_at,
                used,
                created_at
            )
            VALUES (%s, %s, %s, %s, %s, %s)
            ON CONFLICT (id)
            DO NOTHING
        """, (
            row[0],
            row[1],
            row[2],
            row[3],
            bool(row[4]),
            row[5]
        ))

    pg.commit()

    src.close()
    dst.close()

    print(f"{table_name} migrated: {len(rows)}")


def show_counts(pg):
    cur = pg.cursor()

    print("\n" + "=" * 50)
    print("POSTGRESQL VERIFICATION")
    print("=" * 50)

    tables = [
        "users",
        "student_profiles",
        "saved_scholarships",
        "password_reset_tokens",
        "email_verification_tokens"
    ]

    for table in tables:
        cur.execute(f"SELECT COUNT(*) FROM {table}")
        count = cur.fetchone()[0]
        print(f"{table:30} : {count}")

    cur.close()


def main():
    print("=" * 50)
    print("SCHOLARAI SQLITE → POSTGRESQL MIGRATION")
    print("=" * 50)

    if not os.path.exists(SQLITE_DB):
        raise FileNotFoundError(
            f"SQLite database not found: {SQLITE_DB}"
        )

    print("\nSQLite database:")
    print(SQLITE_DB)

    print("\nConnecting to PostgreSQL...")

    pg = psycopg2.connect(DATABASE_URL)

    print("PostgreSQL connection successful.")

    sqlite = sqlite3.connect(SQLITE_DB)

    try:
        create_postgres_schema(pg)

        migrate_users(sqlite, pg)
        migrate_profiles(sqlite, pg)
        migrate_saved_scholarships(sqlite, pg)

        migrate_tokens(
            sqlite,
            pg,
            "password_reset_tokens"
        )

        migrate_tokens(
            sqlite,
            pg,
            "email_verification_tokens"
        )

        show_counts(pg)

        print("\n" + "=" * 50)
        print("MIGRATION COMPLETED SUCCESSFULLY")
        print("=" * 50)

    except Exception:
        pg.rollback()
        raise

    finally:
        sqlite.close()
        pg.close()


if __name__ == "__main__":
    main()