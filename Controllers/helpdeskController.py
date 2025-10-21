from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Body, status, Form
from fastapi.responses import JSONResponse
from typing import List
import os
import uuid
import html

import sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from DB.db import get_db_connection
from Utils.JWT import authenticate_request

helpdesk_router = APIRouter()

from datetime import datetime

# Save helpdesk images into Uploads/HelpdeskImages using timestamp+uuid naming (similar to utilController.upload_image)
UPLOAD_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "Uploads", "HelpdeskImages")
os.makedirs(UPLOAD_DIR, exist_ok=True)

# Allowed image extensions and mime types for attachments
ALLOWED_IMAGE_EXTS = {'.png', '.jpg', '.jpeg', '.gif', '.webp'}
ALLOWED_IMAGE_MIMES = {'image/png', 'image/jpeg', 'image/jpg', 'image/gif', 'image/webp'}


@helpdesk_router.post("/tickets/", status_code=status.HTTP_201_CREATED)
def create_ticket(
    subject: str = Form(...),
    description: str = Form(None),
    priority: str = Form("medium"),
    file: UploadFile = File(None),
    claims: dict = Depends(authenticate_request),
):
    """
    Create a ticket. Accepts optional image attachment in the same request.
    Fields (form-data): subject (required), description (optional), priority (optional), file (optional image).
    The authenticated user id is taken from JWT claims.
    """
    user_id = claims.get("id")
    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid token: user id missing")
    # sanitize and validate inputs to prevent XSS and bad data
    subject = (subject or "").strip()
    if not subject:
        raise HTTPException(status_code=400, detail="subject is required")
    # escape HTML characters to prevent stored XSS — renderers should still escape on output
    subject_s = html.escape(subject)
    description_s = html.escape((description or "").strip())
    priority = (priority or "medium").lower()
    if priority not in ("low", "medium", "high", "urgent"):
        priority = "medium"

    # Insert ticket
    conn = get_db_connection()
    if not conn:
        raise HTTPException(status_code=500, detail="DB connection failed")
    try:
        cur = conn.cursor()
        # Use parameterized queries (no string concatenation) to prevent SQL injection
        cur.execute(
            "INSERT INTO tickets (user_id, subject, description, priority) VALUES (%s, %s, %s, %s)",
            (user_id, subject_s, description_s, priority)
        )
        conn.commit()
        ticket_id = cur.lastrowid

        attachment_info = None
        # If a file is present, validate it is an allowed image and save as ticket-level attachment
        if file is not None:
            content_type = (file.content_type or "").lower()
            # normalize filename and extension
            original_basename = os.path.basename(file.filename or "")
            ext = os.path.splitext(original_basename)[1].lower()
            if content_type not in ALLOWED_IMAGE_MIMES or ext not in ALLOWED_IMAGE_EXTS:
                raise HTTPException(status_code=400, detail="Only image attachments (png/jpg/jpeg/gif/webp) are allowed")
            timestamp = datetime.now().strftime("%d%m%Y%H%M%S")
            fname = f"{timestamp}_{uuid.uuid4().hex}{ext}"
            save_path = os.path.join(UPLOAD_DIR, fname)
            try:
                # read/write in chunks to avoid large memory spikes
                with open(save_path, "wb") as f:
                    while True:
                        chunk = file.file.read(8192)
                        if not chunk:
                            break
                        f.write(chunk)
            except Exception as e:
                raise HTTPException(status_code=500, detail=f"File save failed: {str(e)}")
            file_url = f"/uploads/HelpdeskImages/{fname}"
            cur2 = conn.cursor()
            # store sanitized original file name to DB (escaped to avoid stored XSS when serving filenames)
            sanitized_file_name = html.escape(original_basename)
            cur2.execute(
                "INSERT INTO ticket_attachments (ticket_id, file_name, file_url, file_type) VALUES (%s,%s,%s,%s)",
                (ticket_id, sanitized_file_name, file_url, content_type)
            )
            conn.commit()
            attachment_id = cur2.lastrowid
            attachment_info = {"attachment_id": attachment_id, "file_url": file_url}

        return {"ticket_id": ticket_id, "attachment": attachment_info}
    finally:
        try:
            cur.close()
            conn.close()
        except Exception:
            pass


@helpdesk_router.get("/tickets/open")
def list_open_tickets_admin(claims: dict = Depends(authenticate_request)):
    """List tickets with status 'open' — admin only (claim user id == 1)."""
    requester_id = claims.get("id")
    if requester_id != 1:
        raise HTTPException(status_code=403, detail="Admin access required")
    conn = get_db_connection()
    try:
        cur = conn.cursor(dictionary=True)
        cur.execute("SELECT * FROM tickets WHERE status<>'closed' ORDER BY created_at DESC")
        rows = cur.fetchall()
        return rows
    finally:
        try:
            cur.close()
            conn.close()
        except Exception:
            pass





@helpdesk_router.get("/tickets/{ticket_id}")
def get_ticket(ticket_id: int, claims: dict = Depends(authenticate_request)):
    conn = get_db_connection()
    try:
        cur = conn.cursor(dictionary=True)
        cur.execute("SELECT * FROM tickets WHERE ticket_id=%s", (ticket_id,))
        ticket = cur.fetchone()
        if not ticket:
            raise HTTPException(status_code=404, detail="Ticket not found")
        requester_id = claims.get("id")
        # Admin when user id == 1
        is_admin = (requester_id == 1)
        if requester_id != ticket.get("user_id") and not is_admin:
            raise HTTPException(status_code=403, detail="Insufficient permissions")

        cur.execute("SELECT * FROM ticket_messages WHERE ticket_id=%s ORDER BY created_at ASC", (ticket_id,))
        messages = cur.fetchall()

        # Attachments are linked to ticket (not messages) per new schema
        cur.execute("SELECT * FROM ticket_attachments WHERE ticket_id=%s ORDER BY uploaded_at ASC", (ticket_id,))
        attachments = cur.fetchall()

        ticket["messages"] = messages
        ticket["attachments"] = attachments
        return ticket
    finally:
        try:
            cur.close()
            conn.close()
        except Exception:
            pass


# ...existing code...


@helpdesk_router.get("/tickets/mine")
def list_my_tickets(claims: dict = Depends(authenticate_request)):
    """List all tickets created by the authenticated user (uses user id from JWT claims)."""
    user_id = claims.get("id")
    if user_id is None:
        raise HTTPException(status_code=401, detail="Invalid auth claims")
    conn = get_db_connection()
    try:
        cur = conn.cursor(dictionary=True)
        cur.execute("SELECT * FROM tickets WHERE user_id=%s ORDER BY created_at DESC", (user_id,))
        rows = cur.fetchall()
        return rows
    finally:
        try:
            cur.close()
            conn.close()
        except Exception:
            pass


@helpdesk_router.patch("/tickets/{ticket_id}/status")
def update_ticket_status(ticket_id: int, payload: dict = Body(...), claims: dict = Depends(authenticate_request)):
    new_status = payload.get("status")
    if new_status not in ("open", "in_progress", "resolved", "closed"):
        raise HTTPException(status_code=400, detail="Invalid status")
    conn = get_db_connection()
    try:
        cur = conn.cursor(dictionary=True)
        cur.execute("SELECT user_id FROM tickets WHERE ticket_id=%s", (ticket_id,))
        row = cur.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Ticket not found")
        requester_id = claims.get("id")
        is_admin = (requester_id == 1)
        if requester_id != row["user_id"] and not is_admin:
            raise HTTPException(status_code=403, detail="Insufficient permissions")

        cur.execute("UPDATE tickets SET status=%s, updated_at=NOW() WHERE ticket_id=%s", (new_status, ticket_id))
        conn.commit()
        return {"success": True}
    finally:
        try:
            cur.close()
            conn.close()
        except Exception:
            pass


@helpdesk_router.post("/tickets/{ticket_id}/messages", status_code=status.HTTP_201_CREATED)
def add_message(ticket_id: int, payload: dict = Body(...), claims: dict = Depends(authenticate_request)):
    # Messages are plain text and not tied to sender in DB (per new schema)
    message = payload.get("message")
    if not message:
        raise HTTPException(status_code=400, detail="message is required")
    conn = get_db_connection()
    try:
        cur = conn.cursor(dictionary=True)
        cur.execute("SELECT ticket_id, user_id FROM tickets WHERE ticket_id=%s", (ticket_id,))
        ticket = cur.fetchone()
        if not ticket:
            raise HTTPException(status_code=404, detail="Ticket not found")

        requester_id = claims.get("id")
        is_admin = (requester_id == 1)
        # only ticket owner or admin can post messages
        if requester_id != ticket.get("user_id") and not is_admin:
            raise HTTPException(status_code=403, detail="Insufficient permissions")

        cur2 = conn.cursor()
        sender_id = requester_id
        # Escape message to avoid stored XSS; DB insertion uses parameterized query to avoid SQL injection
        safe_message = html.escape(message)
        cur2.execute(
            "INSERT INTO ticket_messages (ticket_id, user_id, message) VALUES (%s, %s, %s)",
            (ticket_id, sender_id, safe_message)
        )
        conn.commit()
        message_id = cur2.lastrowid
        return {"message_id": message_id, "user_id": sender_id}
    finally:
        try:
            cur.close()
            conn.close()
        except Exception:
            pass



@helpdesk_router.get("/tickets/user/{user_id}")
def list_tickets_by_user_id(user_id: int, claims: dict = Depends(authenticate_request)):
    """List all tickets created by a specific user. Owner or admin allowed."""
    requester_id = claims.get("id")
    is_admin = (requester_id == 1)
    if requester_id != user_id and not is_admin:
        raise HTTPException(status_code=403, detail="Insufficient permissions")
    conn = get_db_connection()
    try:
        cur = conn.cursor(dictionary=True)
        cur.execute("SELECT * FROM tickets WHERE user_id=%s ORDER BY created_at DESC", (user_id,))
        rows = cur.fetchall()
        return rows
    finally:
        try:
            cur.close()
            conn.close()
        except Exception:
            pass


@helpdesk_router.delete("/tickets/{ticket_id}")
def delete_ticket(ticket_id: int, claims: dict = Depends(authenticate_request)):
    """Delete a ticket (admin only: claim user id == 1)."""
    requester_id = claims.get("id")
    if requester_id != 1:
        raise HTTPException(status_code=403, detail="Admin access required")
    conn = get_db_connection()
    try:
        cur = conn.cursor()
        cur.execute("DELETE FROM tickets WHERE ticket_id=%s", (ticket_id,))
        conn.commit()
        return {"deleted": True}
    finally:
        try:
            cur.close()
            conn.close()
        except Exception:
            pass


@helpdesk_router.get("/tickets/{ticket_id}/messages")
def get_messages(ticket_id: int, claims: dict = Depends(authenticate_request)):
    conn = get_db_connection()
    try:
        cur = conn.cursor(dictionary=True)
        cur.execute("SELECT * FROM tickets WHERE ticket_id=%s", (ticket_id,))
        ticket = cur.fetchone()
        if not ticket:
            raise HTTPException(status_code=404, detail="Ticket not found")
        requester_id = claims.get("id")
        is_admin = (requester_id == 1)
        if requester_id != ticket.get("user_id") and not is_admin:
            raise HTTPException(status_code=403, detail="Insufficient permissions")

        cur.execute("SELECT * FROM ticket_messages WHERE ticket_id=%s ORDER BY created_at ASC", (ticket_id,))
        msgs = cur.fetchall()
        return msgs
    finally:
        try:
            cur.close()
            conn.close()
        except Exception:
            pass


@helpdesk_router.post("/tickets/{ticket_id}/attachments", status_code=status.HTTP_201_CREATED)
async def add_attachment(ticket_id: int, file: UploadFile = File(...), claims: dict = Depends(authenticate_request)):
    conn = get_db_connection()
    try:
        cur = conn.cursor(dictionary=True)
        cur.execute("SELECT ticket_id FROM tickets WHERE ticket_id=%s", (ticket_id,))
        if cur.fetchone() is None:
            raise HTTPException(status_code=404, detail="Ticket not found")
        # Accept only image content types
        content_type = (file.content_type or "").lower()
        if not content_type.startswith("image/"):
            raise HTTPException(status_code=400, detail="Only image attachments are allowed")

        # Naming: ddMMyyyyHHMMSS_<uuid><ext>
        timestamp = datetime.now().strftime("%d%m%Y%H%M%S")
        ext = os.path.splitext(file.filename)[1]
        fname = f"{timestamp}_{uuid.uuid4().hex}{ext}"
        save_path = os.path.join(UPLOAD_DIR, fname)
        try:
            with open(save_path, "wb") as f:
                content = await file.read()
                f.write(content)
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"File save failed: {str(e)}")
        file_url = f"/uploads/HelpdeskImages/{fname}"

        cur2 = conn.cursor()
        cur2.execute(
            "INSERT INTO ticket_attachments (ticket_id, file_name, file_url, file_type) VALUES (%s,%s,%s,%s)",
            (ticket_id, file.filename, file_url, file.content_type)
        )
        conn.commit()
        attachment_id = cur2.lastrowid
        return {"attachment_id": attachment_id, "file_url": file_url}
    finally:
        try:
            cur.close()
            conn.close()
        except Exception:
            pass


@helpdesk_router.get("/tickets/{ticket_id}/attachments")
def list_attachments(ticket_id: int, claims: dict = Depends(authenticate_request)):
    conn = get_db_connection()
    try:
        cur = conn.cursor(dictionary=True)
        cur.execute("SELECT * FROM tickets WHERE ticket_id=%s", (ticket_id,))
        ticket = cur.fetchone()
        if ticket is None:
            raise HTTPException(status_code=404, detail="Ticket not found")
        requester_id = claims.get("id")
        is_admin = (requester_id == 1)
        if requester_id != ticket.get("user_id") and not is_admin:
            raise HTTPException(status_code=403, detail="Insufficient permissions")
        cur.execute("SELECT * FROM ticket_attachments WHERE ticket_id=%s ORDER BY uploaded_at ASC", (ticket_id,))
        rows = cur.fetchall()
        return rows
    finally:
        try:
            cur.close()
            conn.close()
        except Exception:
            pass
