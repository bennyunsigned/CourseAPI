import os
from datetime import datetime
from fastapi import Request, HTTPException
from fastapi.responses import JSONResponse
import traceback

# Ensure the Exception folder exists
EXCEPTION_FOLDER = os.path.join(os.getcwd(), "Exception")
os.makedirs(EXCEPTION_FOLDER, exist_ok=True)

async def global_exception_handler(request: Request, exc: Exception):
    """
    Handle all exceptions globally and log them to a file.
    """
    # Get the current date for the log file
    current_date = datetime.now().strftime("%Y-%m-%d")
    log_file_path = os.path.join(EXCEPTION_FOLDER, f"{current_date}.txt")

    # Prepare the log message
    log_message = (
        f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
        f"URL: {request.url}\n"
        f"Method: {request.method}\n"
        f"Error: {str(exc)}\n"
        f"{'-' * 80}\n"
    )

    # Write the log message to the file
    with open(log_file_path, "a") as log_file:
        log_file.write(log_message)

    # Return a JSON response to the client
    if isinstance(exc, HTTPException):
        return JSONResponse(
            status_code=exc.status_code,
            content={"detail": exc.detail},
        )
    return JSONResponse(
        status_code=500,
        content={"detail": "An unexpected error occurred. Please try again later."},
    )

def log_exception_to_file(exc: Exception, context: str | None = None):
    """Append full traceback and optional context to today's exception file."""
    try:
        current_date = datetime.now().strftime("%Y-%m-%d")
        log_file_path = os.path.join(EXCEPTION_FOLDER, f"{current_date}.txt")
        tb = ''.join(traceback.format_exception(type(exc), exc, exc.__traceback__))
        header = f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        if context:
            header += f" | Context: {context}"
        header += "\n"
        with open(log_file_path, 'a') as f:
            f.write(header)
            f.write(tb)
            f.write('\n' + ('-' * 80) + '\n')
    except Exception:
        # never raise from the logger
        pass