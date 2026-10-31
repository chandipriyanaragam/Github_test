from collections.abc import Iterator
import sqlite3

from .settings import settings


SCHEMA = """
PRAGMA foreign_keys = ON;
CREATE TABLE IF NOT EXISTS conversations (
    id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL,
    title TEXT NOT NULL,
    jurisdiction TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_conversations_owner_updated
    ON conversations(user_id, updated_at DESC, id DESC);
CREATE TABLE IF NOT EXISTS messages (
    id TEXT PRIMARY KEY,
    conversation_id TEXT NOT NULL REFERENCES conversations(id) ON DELETE CASCADE,
    role TEXT NOT NULL CHECK(role IN ('user', 'assistant')),
    content TEXT NOT NULL,
    workflow TEXT CHECK(workflow IN ('ask', 'draft', 'summary') OR workflow IS NULL),
    created_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_messages_conversation_created
    ON messages(conversation_id, created_at, id);
CREATE TABLE IF NOT EXISTS turns (
    id TEXT PRIMARY KEY,
    conversation_id TEXT NOT NULL REFERENCES conversations(id) ON DELETE CASCADE,
    user_message_id TEXT NOT NULL REFERENCES messages(id) ON DELETE CASCADE,
    workflow TEXT NOT NULL CHECK(workflow IN ('ask', 'draft', 'summary')),
    status TEXT NOT NULL CHECK(status IN ('awaiting_orchestration', 'completed', 'failed')),
    created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS documents (
    id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL,
    conversation_id TEXT REFERENCES conversations(id) ON DELETE CASCADE,
    filename TEXT NOT NULL,
    media_type TEXT NOT NULL,
    size_bytes INTEGER NOT NULL,
    sha256 TEXT NOT NULL,
    storage_key TEXT NOT NULL UNIQUE,
    status TEXT NOT NULL CHECK(status IN ('awaiting_processing', 'ready', 'failed', 'deleted')),
    extracted_text TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_documents_owner_conversation
    ON documents(user_id, conversation_id);
"""


def connect() -> sqlite3.Connection:
    settings.db_path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(settings.db_path, timeout=10, check_same_thread=False)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    connection.execute("PRAGMA journal_mode = WAL")
    return connection


def initialize_database() -> None:
    connection = connect()
    try:
        connection.execute("PRAGMA foreign_keys = OFF")
        connection.executescript(SCHEMA)
        connection.execute("PRAGMA foreign_keys = OFF")
        # Rebuild early tables so their CHECK constraints permit completed states.
        turn_sql = connection.execute("SELECT sql FROM sqlite_master WHERE type='table' AND name='turns'").fetchone()[0]
        if "'completed'" not in turn_sql:
            connection.execute("ALTER TABLE turns RENAME TO turns_legacy")
            connection.execute("CREATE TABLE turns (id TEXT PRIMARY KEY, conversation_id TEXT NOT NULL REFERENCES conversations(id) ON DELETE CASCADE, user_message_id TEXT NOT NULL REFERENCES messages(id) ON DELETE CASCADE, workflow TEXT NOT NULL CHECK(workflow IN ('ask','draft','summary')), status TEXT NOT NULL CHECK(status IN ('awaiting_orchestration','completed','failed')), created_at TEXT NOT NULL)")
            connection.execute("INSERT INTO turns SELECT * FROM turns_legacy")
            connection.execute("DROP TABLE turns_legacy")
        document_sql = connection.execute("SELECT sql FROM sqlite_master WHERE type='table' AND name='documents'").fetchone()[0]
        if "'ready'" not in document_sql:
            connection.execute("DROP TABLE IF EXISTS citations")
            document_columns = {row["name"] for row in connection.execute("PRAGMA table_info(documents)")}
            extracted_text = "COALESCE(extracted_text,'')" if "extracted_text" in document_columns else "''"
            connection.execute("ALTER TABLE documents RENAME TO documents_legacy")
            connection.execute("CREATE TABLE documents (id TEXT PRIMARY KEY, user_id TEXT NOT NULL, conversation_id TEXT REFERENCES conversations(id) ON DELETE CASCADE, filename TEXT NOT NULL, media_type TEXT NOT NULL, size_bytes INTEGER NOT NULL, sha256 TEXT NOT NULL, storage_key TEXT NOT NULL UNIQUE, status TEXT NOT NULL CHECK(status IN ('awaiting_processing','ready','failed','deleted')), created_at TEXT NOT NULL, extracted_text TEXT NOT NULL DEFAULT '')")
            connection.execute(f"INSERT INTO documents(id,user_id,conversation_id,filename,media_type,size_bytes,sha256,storage_key,status,created_at,extracted_text) SELECT id,user_id,conversation_id,filename,media_type,size_bytes,sha256,storage_key,status,created_at,{extracted_text} FROM documents_legacy")
            connection.execute("DROP TABLE documents_legacy")
            connection.execute("CREATE INDEX IF NOT EXISTS idx_documents_owner_conversation ON documents(user_id,conversation_id)")
        connection.executescript("CREATE TABLE IF NOT EXISTS citations (id TEXT PRIMARY KEY, message_id TEXT NOT NULL REFERENCES messages(id) ON DELETE CASCADE, document_id TEXT NOT NULL REFERENCES documents(id) ON DELETE CASCADE, filename TEXT NOT NULL, page INTEGER, excerpt TEXT NOT NULL, source_number INTEGER NOT NULL DEFAULT 1, created_at TEXT NOT NULL); CREATE INDEX IF NOT EXISTS idx_citations_message ON citations(message_id);")
        # Upgrade databases created by the initial API-only version.
        for table, column, definition in (
            ("documents", "extracted_text", "TEXT NOT NULL DEFAULT ''"),
            ("citations", "source_number", "INTEGER NOT NULL DEFAULT 1"),
        ):
            existing = {row["name"] for row in connection.execute(f"PRAGMA table_info({table})")}
            if column not in existing:
                connection.execute(f"ALTER TABLE {table} ADD COLUMN {column} {definition}")
        connection.execute("PRAGMA foreign_keys = ON")
    finally:
        connection.close()


def get_db() -> Iterator[sqlite3.Connection]:
    connection = connect()
    try:
        yield connection
    finally:
        connection.close()


def check_database() -> bool:
    connection = None
    try:
        connection = connect()
        connection.execute("SELECT 1").fetchone()
        return True
    except sqlite3.Error:
        return False
    finally:
        if connection is not None:
            connection.close()
