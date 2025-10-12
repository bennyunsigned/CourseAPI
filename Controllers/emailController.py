import os
import threading
import time
from fastapi import APIRouter, BackgroundTasks, HTTPException
from pydantic import BaseModel, EmailStr
from typing import Optional, List

from Services import emailService

router = APIRouter()

class EmailCreate(BaseModel):
    recipient_email: EmailStr
    subject: Optional[str] = None
    body: Optional[str] = None
    attachments: Optional[str] = None

# Background sender control
_sender_thread = None
_sender_stop_event = threading.Event()


def _email_sender_loop(interval_seconds: int = 60):
    """Loop that runs every `interval_seconds` to fetch up to 500 active emails and send them."""
    while not _sender_stop_event.is_set():
        try:
            rows = emailService.fetch_active_emails(500)
            if rows:
                for row in rows:
                    email_id = row.get('EmailId')
                    to = row.get('recipient_email')
                    subject = row.get('subject')
                    body = row.get('body')
                    success, err = emailService.send_email_via_smtp(to, subject, body, row.get('attachments'))
                    if success:
                        ok = emailService.mark_email_sent(email_id)
                        if not ok:
                            print(f"[emailController] Failed to mark EmailId={email_id} as Sent")
                    else:
                        # mark failed; you might want retry logic depending on attempts
                        failed_ok = emailService.mark_email_failed(email_id)
                        print(f"[emailController] Failed to send EmailId={email_id} to {to}: {err}")
                        if not failed_ok:
                            print(f"[emailController] Failed to mark EmailId={email_id} as Failed")
        except Exception:
            # swallow exceptions to keep loop alive; consider logging
            pass
        # wait with early exit support
        _sender_stop_event.wait(interval_seconds)


@router.post('/add', summary='Add an email to EmailMaster')
def add_email(payload: EmailCreate):
    eid = emailService.insert_email(payload.recipient_email, payload.subject, payload.body, payload.attachments)
    if eid is None:
        raise HTTPException(status_code=500, detail='Failed to insert email')
    return {'EmailId': eid}


@router.get('/active', summary='Get up to 500 active emails ordered desc')
def get_active_emails():
    rows = emailService.fetch_active_emails(500)
    return rows


@router.post('/sendNow', summary='Trigger immediate send of up to 500 active emails')
def send_now(background: BackgroundTasks):
    # Run a single immediate send in background to avoid blocking
    background.add_task(_run_once_send)
    return {'status': 'started'}


def _run_once_send():
    try:
        rows = emailService.fetch_active_emails(500)
        for row in rows:
            email_id = row.get('EmailId')
            to = row.get('recipient_email')
            subject = row.get('subject')
            body = row.get('body')
            success, err = emailService.send_email_via_smtp(to, subject, body, row.get('attachments'))
            if success:
                ok = emailService.mark_email_sent(email_id)
                if not ok:
                    print(f"[emailController] Failed to mark EmailId={email_id} as Sent (run_once)")
            else:
                failed_ok = emailService.mark_email_failed(email_id)
                print(f"[emailController] Failed to send EmailId={email_id} to {to} (run_once): {err}")
                if not failed_ok:
                    print(f"[emailController] Failed to mark EmailId={email_id} as Failed (run_once)")
    except Exception:
        import traceback
        tb = traceback.format_exc()
        print("[emailController] _run_once_send exception:\n", tb)


# Helper functions to start/stop the background polling thread from app startup/shutdown

def start_email_sender(interval_seconds: int = 60):
    global _sender_thread, _sender_stop_event
    if _sender_thread and _sender_thread.is_alive():
        return
    _sender_stop_event.clear()
    _sender_thread = threading.Thread(target=_email_sender_loop, args=(interval_seconds,), daemon=True)
    _sender_thread.start()


def stop_email_sender():
    global _sender_thread, _sender_stop_event
    if _sender_thread and _sender_thread.is_alive():
        _sender_stop_event.set()
    _sender_thread.join(timeout=5)