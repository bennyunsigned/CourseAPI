from fastapi import APIRouter, Depends, HTTPException, status, Query
from typing import Optional
from datetime import datetime

from Utils.JWT import authenticate_request
from DB.db import get_db_connection

report_router = APIRouter()


def _discover_payment_columns(conn):
    """Return a dict mapping normalized names to actual column names present in Payment table."""
    cur = conn.cursor()
    try:
        cur.execute(
            "SELECT COLUMN_NAME FROM information_schema.COLUMNS WHERE TABLE_SCHEMA=DATABASE() AND TABLE_NAME='Payment'"
        )
        cols = [r[0] for r in cur.fetchall()]
        lc = {c.lower(): c for c in cols}

        def pick(*candidates):
            for cand in candidates:
                if cand.lower() in lc:
                    return lc[cand.lower()]
            return None

        return {
            'user': pick('user_id', 'userid', 'user'),
            'payment_id': pick('payment_id', 'paymentid', 'payment_id', 'transactionid', 'transaction_id'),
            'amount': pick('amount', 'amountpaid', 'amount_paid', 'amountpaid', 'amount'),
            'status': pick('status', 'paymentstatus', 'payment_status'),
            'payment_type': pick('payment_type', 'subscription_type', 'paymenttype'),
            'created_at': pick('created_at', 'createdat', 'createdat', 'createdat', 'createdat', 'created_at', 'createdat', 'createdat')
        }
    finally:
        try:
            cur.close()
        except Exception:
            pass


@report_router.get("/payments/me")
def get_my_payments(claims: dict = Depends(authenticate_request)):
    """Return payments done by the authenticated user (from JWT claims).

    Uses the Payment table rows created by `instamojoController`.
    """
    user_id = claims.get('id')
    if not user_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid auth claims")

    conn = get_db_connection()
    if not conn:
        raise HTTPException(status_code=500, detail="Database connection failed")
    try:
        colmap = _discover_payment_columns(conn)
        if not colmap.get('user'):
            raise HTTPException(status_code=400, detail="No user column found in Payment table")

        sel_cols = []
        # build select list mapping to stable aliases
        if colmap.get('user'):
            sel_cols.append(f"`{colmap['user']}` AS user_id")
        else:
            sel_cols.append("NULL AS user_id")

        if colmap.get('payment_id'):
            sel_cols.append(f"`{colmap['payment_id']}` AS payment_id")
        else:
            sel_cols.append("NULL AS payment_id")

        if colmap.get('amount'):
            sel_cols.append(f"`{colmap['amount']}` AS amount")
        else:
            sel_cols.append("0.0 AS amount")

        if colmap.get('status'):
            sel_cols.append(f"`{colmap['status']}` AS status")
        else:
            sel_cols.append("NULL AS status")

        if colmap.get('payment_type'):
            sel_cols.append(f"`{colmap['payment_type']}` AS payment_type")
        else:
            sel_cols.append("NULL AS payment_type")

        if colmap.get('created_at'):
            sel_cols.append(f"`{colmap['created_at']}` AS created_at")
            order_col = f"`{colmap['created_at']}`"
        else:
            sel_cols.append("NULL AS created_at")
            order_col = "NULL"

        query = f"SELECT {', '.join(sel_cols)} FROM Payment WHERE `{colmap['user']}` = %s ORDER BY {order_col} DESC"
        cur = conn.cursor(dictionary=True)
        cur.execute(query, (user_id,))
        rows = cur.fetchall()
        return rows
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
    finally:
        try:
            cur.close()
        except Exception:
            pass
        try:
            conn.close()
        except Exception:
            pass


@report_router.get("/admin/total")
def admin_total_payments(
    start: Optional[str] = Query(None, description="Start date YYYY-MM-DD"),
    end: Optional[str] = Query(None, description="End date YYYY-MM-DD"),
    claims: dict = Depends(authenticate_request),
):
    """Return total payments received within a date range. Admin only.

    Date params are inclusive. If omitted, returns totals for all time.
    """
    # require admin role
    role = claims.get('role')
    if role != 'Admin':
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permissions")

    # parse dates
    start_dt = None
    end_dt = None
    try:
        if start:
            start_dt = datetime.strptime(start, "%Y-%m-%d")
        if end:
            end_dt = datetime.strptime(end, "%Y-%m-%d")
            # include entire day
            end_dt = end_dt.replace(hour=23, minute=59, second=59)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid date format. Use YYYY-MM-DD")

    conn = get_db_connection()
    if not conn:
        raise HTTPException(status_code=500, detail="Database connection failed")
    try:
        # Discover actual column names in Payment table
        colmap = _discover_payment_columns(conn)
        params = []

        where_clauses = []
        # status filter (if available)
        if colmap.get('status'):
            where_clauses.append(f"LOWER(`{colmap['status']}`) IN ('success','completed')")
        # date filters (if created_at column exists)
        if colmap.get('created_at'):
            if start_dt:
                where_clauses.append(f"`{colmap['created_at']}` >= %s")
                params.append(start_dt)
            if end_dt:
                where_clauses.append(f"`{colmap['created_at']}` <= %s")
                params.append(end_dt)

        where_sql = ""
        if where_clauses:
            where_sql = "WHERE " + " AND ".join(where_clauses)

        amt_expr = f"`{colmap['amount']}`" if colmap.get('amount') else "0"

        cur = conn.cursor()
        query = f"SELECT SUM({amt_expr}) AS total_amount, COUNT(*) AS total_count FROM Payment {where_sql}"
        cur.execute(query, tuple(params))
        total_row = cur.fetchone()

        # breakdown by payment_type
        breakdown = []
        if colmap.get('payment_type'):
            bq = f"SELECT `{colmap['payment_type']}` AS payment_type, SUM({amt_expr}) AS total_amount, COUNT(*) AS count FROM Payment {where_sql} GROUP BY `{colmap['payment_type']}`"
            cur.execute(bq, tuple(params))
            breakdown = cur.fetchall()

        return {
            "total": float(total_row[0]) if total_row and total_row[0] is not None else 0.0,
            "count": int(total_row[1]) if total_row and total_row[1] is not None else 0,
            "breakdown": [
                {"payment_type": r[0], "total_amount": float(r[1]) if r[1] is not None else 0.0, "count": int(r[2]) if r[2] is not None else 0} for r in breakdown
            ],
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
    finally:
        try:
            cur.close()
        except Exception:
            pass
        try:
            conn.close()
        except Exception:
            pass
