"""SQLite persistence operations. Routes depend on these functions rather than SQL details."""
from datetime import datetime, timezone
import sqlite3
from uuid import uuid4


def timestamp() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")


def new_id() -> str:
    return str(uuid4())


def create_conversation(db: sqlite3.Connection, user_id: str, title: str | None = None, jurisdiction: str | None = None) -> sqlite3.Row:
    now = timestamp()
    conversation_id = new_id()
    db.execute(
        "INSERT INTO conversations(id,user_id,title,jurisdiction,created_at,updated_at) VALUES(?,?,?,?,?,?)",
        (conversation_id, user_id, title or "New conversation", jurisdiction, now, now),
    )
    return db.execute("SELECT * FROM conversations WHERE id=?", (conversation_id,)).fetchone()


def owned_conversation(db: sqlite3.Connection, conversation_id: str, user_id: str) -> sqlite3.Row | None:
    return db.execute("SELECT * FROM conversations WHERE id=? AND user_id=?", (conversation_id, user_id)).fetchone()


def conversation_summary(db: sqlite3.Connection, row: sqlite3.Row) -> dict:
    documents = db.execute("SELECT id FROM documents WHERE conversation_id=? AND user_id=? AND status!='deleted' ORDER BY created_at", (row["id"], row["user_id"])).fetchall()
    count = db.execute("SELECT COUNT(*) AS n FROM messages WHERE conversation_id=?", (row["id"],)).fetchone()["n"]
    return {
        "id": row["id"], "title": row["title"], "jurisdiction": row["jurisdiction"],
        "created_at": row["created_at"], "updated_at": row["updated_at"],
        "document_ids": [doc["id"] for doc in documents], "message_count": count,
    }


def create_message(db: sqlite3.Connection, conversation_id: str, content: str, workflow: str, role: str = "user") -> sqlite3.Row:
    message_id, now = new_id(), timestamp()
    db.execute(
        "INSERT INTO messages(id,conversation_id,role,content,workflow,created_at) VALUES(?,?,?,?,?,?)",
        (message_id, conversation_id, role, content, workflow, now),
    )
    db.execute("UPDATE conversations SET updated_at=? WHERE id=?", (now, conversation_id))
    return db.execute("SELECT * FROM messages WHERE id=?", (message_id,)).fetchone()


def message_out(row: sqlite3.Row) -> dict:
    return {"id": row["id"], "role": row["role"], "content": row["content"], "workflow": row["workflow"], "created_at": row["created_at"], "citations": []}


def message_citations(db: sqlite3.Connection, message_id: str) -> list[dict]:
    rows = db.execute("SELECT id,document_id,filename,page,excerpt,source_number FROM citations WHERE message_id=? ORDER BY source_number", (message_id,)).fetchall()
    return [dict(row) for row in rows]


def create_document(db: sqlite3.Connection, **values) -> sqlite3.Row:
    db.execute(
        """INSERT INTO documents(id,user_id,conversation_id,filename,media_type,size_bytes,sha256,storage_key,status,created_at,extracted_text)
           VALUES(:id,:user_id,:conversation_id,:filename,:media_type,:size_bytes,:sha256,:storage_key,:status,:created_at,:extracted_text)""",
        values,
    )
    return db.execute("SELECT * FROM documents WHERE id=?", (values["id"],)).fetchone()


def document_out(row: sqlite3.Row) -> dict:
    return {"id": row["id"], "filename": row["filename"], "media_type": row["media_type"],
            "size_bytes": row["size_bytes"], "status": row["status"],
            "conversation_id": row["conversation_id"], "created_at": row["created_at"]}


def list_conversations(db: sqlite3.Connection, user_id: str, limit: int, cursor: tuple[str, str] | None):
    if cursor:
        updated_at, conversation_id = cursor
        return db.execute(
            """SELECT * FROM conversations WHERE user_id=? AND (updated_at < ? OR (updated_at=? AND id < ?))
               ORDER BY updated_at DESC,id DESC LIMIT ?""", (user_id, updated_at, updated_at, conversation_id, limit),
        ).fetchall()
    return db.execute("SELECT * FROM conversations WHERE user_id=? ORDER BY updated_at DESC,id DESC LIMIT ?", (user_id, limit)).fetchall()


def conversation_messages(db: sqlite3.Connection, conversation_id: str):
    return db.execute("SELECT * FROM messages WHERE conversation_id=? ORDER BY created_at,id", (conversation_id,)).fetchall()


def update_conversation(db: sqlite3.Connection, conversation_id: str, user_id: str, fields: dict) -> sqlite3.Row | None:
    row = owned_conversation(db, conversation_id, user_id)
    if row is None:
        return None
    assignments = ",".join(f"{key}=?" for key in fields)
    db.execute(f"UPDATE conversations SET {assignments},updated_at=? WHERE id=? AND user_id=?",
               (*fields.values(), timestamp(), conversation_id, user_id))
    return owned_conversation(db, conversation_id, user_id)


def delete_conversation(db: sqlite3.Connection, conversation_id: str, user_id: str) -> list[str] | None:
    row = owned_conversation(db, conversation_id, user_id)
    if row is None:
        return None
    stored = db.execute("SELECT storage_key FROM documents WHERE conversation_id=? AND user_id=?", (conversation_id, user_id)).fetchall()
    db.execute("DELETE FROM conversations WHERE id=? AND user_id=?", (conversation_id, user_id))
    return [item["storage_key"] for item in stored]


def attach_documents(db: sqlite3.Connection, document_ids: list[str], conversation_id: str) -> None:
    for document_id in document_ids:
        db.execute("UPDATE documents SET conversation_id=? WHERE id=? AND conversation_id IS NULL", (conversation_id, document_id))


def set_conversation_jurisdiction(db: sqlite3.Connection, conversation_id: str, jurisdiction: str) -> None:
    db.execute("UPDATE conversations SET jurisdiction=? WHERE id=?", (jurisdiction, conversation_id))


def document_attachment_state(db: sqlite3.Connection, document_id: str, user_id: str):
    return db.execute("SELECT id,conversation_id,status FROM documents WHERE id=? AND user_id=?", (document_id, user_id)).fetchone()


def record_turn(db: sqlite3.Connection, conversation_id: str, content: str, workflow: str) -> tuple[sqlite3.Row, str]:
    message = create_message(db, conversation_id, content, workflow)
    turn_id = new_id()
    db.execute("INSERT INTO turns(id,conversation_id,user_message_id,workflow,status,created_at) VALUES(?,?,?,?,?,?)",
               (turn_id, conversation_id, message["id"], workflow, "awaiting_orchestration", timestamp()))
    return message, turn_id


def set_turn_status(db: sqlite3.Connection, turn_id: str, state: str) -> None:
    db.execute("UPDATE turns SET status=? WHERE id=?", (state, turn_id))


def get_document(db: sqlite3.Connection, document_id: str, user_id: str) -> sqlite3.Row | None:
    return db.execute("SELECT * FROM documents WHERE id=? AND user_id=?", (document_id, user_id)).fetchone()


def list_documents(db: sqlite3.Connection, user_id: str) -> list[sqlite3.Row]:
    return db.execute("SELECT * FROM documents WHERE user_id=? ORDER BY created_at DESC,id", (user_id,)).fetchall()


def delete_document(db: sqlite3.Connection, document_id: str, user_id: str) -> str | None:
    row = get_document(db, document_id, user_id)
    if row is None:
        return None
    db.execute("DELETE FROM documents WHERE id=? AND user_id=?", (document_id, user_id))
    return row["storage_key"]
