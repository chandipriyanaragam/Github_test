import base64
import binascii
from datetime import datetime
import json
import logging
import os
from pathlib import Path
import re
import sqlite3
import shutil
from uuid import uuid4
import zipfile

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile, status
from fastapi.responses import Response

from ..database import get_db
from ..repositories import (attach_documents, conversation_messages, conversation_summary, create_conversation,
                            create_document, delete_conversation as repo_delete_conversation, delete_document as repo_delete_document,
                            document_attachment_state, document_out, get_document, list_documents as list_document_rows, list_conversations as list_conversation_rows, message_citations, message_out, new_id,
                            owned_conversation, create_message, record_turn, set_conversation_jurisdiction, set_turn_status, timestamp, update_conversation)
from ..schemas import ConversationCreate, ConversationDetail, ConversationPage, ConversationPatch, ConversationSummary, DocumentOut, DocumentStatus, ErrorResponse, TurnCreate, TurnResponse
from ..settings import settings
from ..workflows import extract_document, run_workflow

logger = logging.getLogger("legallens.api")
router = APIRouter(prefix="/api/v1", responses={
    400: {"model": ErrorResponse}, 404: {"model": ErrorResponse}, 413: {"model": ErrorResponse},
    415: {"model": ErrorResponse}, 422: {"model": ErrorResponse}, 500: {"model": ErrorResponse},
    501: {"model": ErrorResponse},
})


def _cursor_encode(updated_at: str, conversation_id: str) -> str:
    raw = json.dumps([updated_at, conversation_id], separators=(",", ":")).encode()
    return base64.urlsafe_b64encode(raw).decode().rstrip("=")


def _cursor_decode(cursor: str) -> tuple[str, str]:
    try:
        padded = cursor + "=" * (-len(cursor) % 4)
        value = json.loads(base64.urlsafe_b64decode(padded.encode()))
        if not isinstance(value, list) or len(value) != 2 or not all(isinstance(v, str) for v in value):
            raise ValueError
        datetime.fromisoformat(value[0].replace("Z", "+00:00"))
        return value[0], value[1]
    except (ValueError, TypeError, json.JSONDecodeError, binascii.Error):
        raise HTTPException(status_code=400, detail="The pagination cursor is invalid.") from None


def _document_path(storage_key: str) -> Path:
    path = (settings.storage_dir / storage_key).resolve()
    root = settings.storage_dir.resolve()
    if path.parent != root:
        raise HTTPException(status_code=500, detail="Document storage metadata is invalid.")
    return path


def _safe_filename(original: str | None) -> tuple[str, str]:
    candidate = (original or "").replace("\\", "/").split("/")[-1]
    candidate = re.sub(r"[\x00-\x1f\x7f]", "", candidate).strip(" .")
    if not candidate or len(candidate) > 255:
        raise HTTPException(status_code=400, detail="A valid filename is required.")
    suffix = Path(candidate).suffix.lower()
    if suffix not in {".pdf", ".docx"}:
        raise HTTPException(status_code=415, detail="Only PDF and DOCX files are accepted.")
    return candidate, suffix


def _verify_signature(path: Path, suffix: str) -> bool:
    with path.open("rb") as handle:
        head = handle.read(8)
    if suffix == ".pdf":
        return head.startswith(b"%PDF-")
    if not head.startswith(b"PK\x03\x04"):
        return False
    try:
        with zipfile.ZipFile(path) as archive:
            return "[Content_Types].xml" in archive.namelist() and "word/document.xml" in archive.namelist()
    except (OSError, zipfile.BadZipFile):
        return False


def _validate_document_ids(db: sqlite3.Connection, document_ids: list[str], user_id: str, conversation_id: str | None) -> None:
    if len(document_ids) != len(set(document_ids)):
        raise HTTPException(status_code=422, detail="Document IDs must be unique.")
    for document_id in document_ids:
        row = document_attachment_state(db, document_id, user_id)
        if row is None or row["status"] == "deleted":
            raise HTTPException(status_code=404, detail="A referenced document was not found.")
        if row["conversation_id"] not in (None, conversation_id):
            raise HTTPException(status_code=422, detail="A document belongs to a different conversation.")


@router.post("/conversations", response_model=ConversationSummary, status_code=status.HTTP_201_CREATED)
def post_conversation(payload: ConversationCreate, db: sqlite3.Connection = Depends(get_db)):
    with db:
        row = create_conversation(db, settings.demo_user_id, payload.title)
    return conversation_summary(db, row)


@router.get("/conversations", response_model=ConversationPage)
def list_conversations(
    cursor: str | None = None,
    limit: int = Query(default=20, ge=1, le=100),
    db: sqlite3.Connection = Depends(get_db),
):
    user_id = settings.demo_user_id
    if cursor:
        updated_at, conversation_id = _cursor_decode(cursor)
        rows = list_conversation_rows(db, user_id, limit + 1, (updated_at, conversation_id))
    else:
        rows = list_conversation_rows(db, user_id, limit + 1, None)
    has_more = len(rows) > limit
    page = rows[:limit]
    next_cursor = _cursor_encode(page[-1]["updated_at"], page[-1]["id"]) if has_more and page else None
    return {"items": [conversation_summary(db, row) for row in page], "next_cursor": next_cursor}


@router.get("/conversations/{conversation_id}", response_model=ConversationDetail)
def get_conversation(conversation_id: str, db: sqlite3.Connection = Depends(get_db)):
    row = owned_conversation(db, conversation_id, settings.demo_user_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Conversation was not found.")
    result = conversation_summary(db, row)
    messages = conversation_messages(db, conversation_id)
    result["messages"] = [{**message_out(message), "citations": message_citations(db, message["id"])} for message in messages]
    return result


@router.patch("/conversations/{conversation_id}", response_model=ConversationSummary)
def patch_conversation(conversation_id: str, payload: ConversationPatch, db: sqlite3.Connection = Depends(get_db)):
    fields = payload.model_dump(exclude_unset=True)
    if not fields:
        raise HTTPException(status_code=422, detail="At least one conversation field must be supplied.")
    if "title" in fields and fields["title"] is None:
        raise HTTPException(status_code=422, detail="Conversation title cannot be null.")
    with db:
        row = update_conversation(db, conversation_id, settings.demo_user_id, fields)
        if row is None:
            raise HTTPException(status_code=404, detail="Conversation was not found.")
    return conversation_summary(db, row)


@router.delete("/conversations/{conversation_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_conversation(conversation_id: str, db: sqlite3.Connection = Depends(get_db)):
    with db:
        stored_keys = repo_delete_conversation(db, conversation_id, settings.demo_user_id)
        if stored_keys is None:
            raise HTTPException(status_code=404, detail="Conversation was not found.")
    for storage_key in stored_keys:
        try:
            _document_path(storage_key).unlink(missing_ok=True)
        except OSError:
            logger.warning("document_cleanup_failed conversation_id=%s", conversation_id)
    return Response(status_code=204)


@router.post("/chat/turns", response_model=TurnResponse, status_code=status.HTTP_200_OK)
def post_turn(payload: TurnCreate, db: sqlite3.Connection = Depends(get_db)):
    if not settings.openai_api_key:
        raise HTTPException(status_code=503, detail="OPENAI_API_KEY is not configured. Add it to LegalLens/backend/.env.")
    user_id = settings.demo_user_id
    with db:
        if payload.conversation_id:
            conversation = owned_conversation(db, payload.conversation_id, user_id)
            if conversation is None:
                raise HTTPException(status_code=404, detail="Conversation was not found.")
            conversation_id = payload.conversation_id
        else:
            conversation = create_conversation(db, user_id, payload.message.content[:60].strip() or "New conversation", payload.message.jurisdiction)
            conversation_id = conversation["id"]
        _validate_document_ids(db, payload.message.document_ids, user_id, conversation_id)
        attach_documents(db, payload.message.document_ids, conversation_id)
        if payload.message.jurisdiction is not None:
            set_conversation_jurisdiction(db, conversation_id, payload.message.jurisdiction)
        message, turn_id = record_turn(db, conversation_id, payload.message.content, payload.message.workflow)
        documents = []
        for document_id in payload.message.document_ids:
            document = get_document(db, document_id, user_id)
            if document is None or document["status"] != "ready":
                raise HTTPException(status_code=422, detail="A selected document is still processing or could not be read.")
            pages = json.loads(document["extracted_text"])
            documents.append({"id": document["id"], "filename": document["filename"], "pages": pages})
    try:
        workflow, answer, citations = run_workflow(payload.message.content, payload.message.workflow,
                                                   payload.message.jurisdiction, documents)
    except Exception:
        with db:
            set_turn_status(db, turn_id, "failed")
        raise
    with db:
        assistant = create_message(db, conversation_id, answer, workflow, "assistant")
        for citation in citations:
            db.execute("INSERT INTO citations(id,message_id,document_id,filename,page,excerpt,source_number,created_at) VALUES(?,?,?,?,?,?,?,?)",
                       (citation["id"], assistant["id"], citation["document_id"], citation["filename"], citation["page"], citation["excerpt"], citation["source_number"], citation["created_at"]))
        set_turn_status(db, turn_id, "completed")
    return {"turn_id": turn_id, "conversation_id": conversation_id, "user_message": message_out(message),
            "status": "completed", "assistant_message": {**message_out(assistant), "citations": citations}}


@router.post("/documents", response_model=DocumentOut, status_code=status.HTTP_202_ACCEPTED)
async def post_document(
    file: UploadFile = File(...),
    conversation_id: str | None = Form(default=None),
    db: sqlite3.Connection = Depends(get_db),
):
    user_id = settings.demo_user_id
    if conversation_id and owned_conversation(db, conversation_id, user_id) is None:
        raise HTTPException(status_code=404, detail="Conversation was not found.")
    filename, suffix = _safe_filename(file.filename)
    allowed_mime = {"application/pdf", "application/vnd.openxmlformats-officedocument.wordprocessingml.document", "application/octet-stream"}
    if file.content_type not in allowed_mime:
        raise HTTPException(status_code=415, detail="Only PDF and DOCX files are accepted.")

    settings.storage_dir.mkdir(parents=True, exist_ok=True)
    document_id = new_id()
    storage_key = document_id + suffix
    destination = _document_path(storage_key)
    temp_path = _document_path(document_id + ".uploading")
    byte_count = 0
    import hashlib
    digest = hashlib.sha256()
    try:
        with temp_path.open("xb") as output:
            while chunk := await file.read(1024 * 1024):
                byte_count += len(chunk)
                if byte_count > settings.max_upload_bytes:
                    raise HTTPException(status_code=413, detail="The uploaded file exceeds the configured size limit.")
                digest.update(chunk)
                output.write(chunk)
        if byte_count == 0 or not _verify_signature(temp_path, suffix):
            raise HTTPException(status_code=415, detail="The file contents do not match a valid PDF or DOCX document.")
        os.replace(temp_path, destination)
        media_type = "application/pdf" if suffix == ".pdf" else "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        try:
            pages = extract_document(destination, suffix)
        except ValueError as exc:
            destination.unlink(missing_ok=True)
            raise HTTPException(status_code=422, detail=str(exc)) from exc
        values = {"id": document_id, "user_id": user_id, "conversation_id": conversation_id, "filename": filename,
                  "media_type": media_type, "size_bytes": byte_count, "sha256": digest.hexdigest(),
                  "storage_key": storage_key, "status": "ready", "created_at": timestamp(), "extracted_text": json.dumps(pages)}
        try:
            with db:
                row = create_document(db, **values)
        except Exception:
            destination.unlink(missing_ok=True)
            raise
        return document_out(row)
    finally:
        temp_path.unlink(missing_ok=True)
        await file.close()


@router.get("/documents", response_model=list[DocumentOut])
def list_documents(db: sqlite3.Connection = Depends(get_db)):
    return [document_out(row) for row in list_document_rows(db, settings.demo_user_id) if row["status"] != "deleted"]


@router.post("/documents/{document_id}/copy", response_model=DocumentOut, status_code=status.HTTP_201_CREATED)
def copy_document_to_conversation(document_id: str, conversation_id: str, db: sqlite3.Connection = Depends(get_db)):
    source = get_document(db, document_id, settings.demo_user_id)
    if source is None or source["status"] != "ready":
        raise HTTPException(status_code=404, detail="A ready source document was not found.")
    if owned_conversation(db, conversation_id, settings.demo_user_id) is None:
        raise HTTPException(status_code=404, detail="Conversation was not found.")
    clone_id = new_id()
    suffix = Path(source["filename"]).suffix.lower()
    storage_key = clone_id + suffix
    source_path, destination = _document_path(source["storage_key"]), _document_path(storage_key)
    try:
        shutil.copyfile(source_path, destination)
        values = {"id": clone_id, "user_id": settings.demo_user_id, "conversation_id": conversation_id,
                  "filename": source["filename"], "media_type": source["media_type"], "size_bytes": source["size_bytes"],
                  "sha256": source["sha256"], "storage_key": storage_key, "status": "ready",
                  "created_at": timestamp(), "extracted_text": source["extracted_text"]}
        with db:
            row = create_document(db, **values)
        return document_out(row)
    except Exception:
        destination.unlink(missing_ok=True)
        raise


@router.get("/documents/{document_id}/status", response_model=DocumentStatus)
def get_document_status(document_id: str, db: sqlite3.Connection = Depends(get_db)):
    row = get_document(db, document_id, settings.demo_user_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Document was not found.")
    if row["status"] == "awaiting_processing":
        try:
            pages = extract_document(_document_path(row["storage_key"]), Path(row["filename"]).suffix.lower())
            with db:
                db.execute("UPDATE documents SET status='ready',extracted_text=? WHERE id=? AND user_id=?",
                           (json.dumps(pages), document_id, settings.demo_user_id))
            row = get_document(db, document_id, settings.demo_user_id)
        except (ValueError, OSError) as exc:
            with db:
                db.execute("UPDATE documents SET status='failed' WHERE id=? AND user_id=?", (document_id, settings.demo_user_id))
            raise HTTPException(status_code=422, detail=str(exc)) from exc
    result = document_out(row)
    result["detail"] = "Document text is extracted locally and ready for use." if row["status"] == "ready" else "Document processing failed."
    return result


@router.delete("/documents/{document_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_document(document_id: str, db: sqlite3.Connection = Depends(get_db)):
    with db:
        storage_key = repo_delete_document(db, document_id, settings.demo_user_id)
        if storage_key is None:
            return Response(status_code=204)
    try:
        _document_path(storage_key).unlink(missing_ok=True)
    except OSError:
        logger.warning("document_cleanup_failed document_id=%s", document_id)
    return Response(status_code=204)


@router.post("/ncc", status_code=status.HTTP_501_NOT_IMPLEMENTED)
def ncc_not_configured():
    raise HTTPException(status_code=501, detail="NCC purpose and upstream contract have not been defined.")


@router.post("/exports", status_code=status.HTTP_501_NOT_IMPLEMENTED)
def export_not_configured():
    raise HTTPException(status_code=501, detail="Document export is not configured in this backend phase.")
