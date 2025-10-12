import os
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.middleware.httpsredirect import HTTPSRedirectMiddleware
from fastapi.staticfiles import StaticFiles
import base64
import secrets
from fastapi import Response

# Exception Handler
from Utils.ExceptionHandler import global_exception_handler

# Routers
from Controllers.authController import auth_router
from Controllers.courseController import course_router
from Controllers.courseModuleController import course_module_router
from Controllers.utilController import util_router
from Controllers.categoryController import category_router
from Controllers.courseProgressController import course_progress_router
from Controllers.courseProgressController import start_cache_refresh_thread, stop_cache_refresh_thread
from Controllers.instamojoController import router as instamojo_router
from Controllers.cartController import cart_router
from Controllers.emailController import router as email_router, start_email_sender, stop_email_sender


# ✅ FastAPI app
app = FastAPI(
    title="Vidyaroop API",
    description="API for Vidyaroop Learning Platform",
    version="1.0.0"
)

# Protect interactive docs (Swagger UI / ReDoc / OpenAPI JSON) with HTTP Basic auth
# when DOCS_USERNAME and DOCS_PASSWORD environment variables are set. If they are
# not set, docs remain publicly accessible.
_DOCS_USER = os.getenv("DOCS_USERNAME")
_DOCS_PASS = os.getenv("DOCS_PASSWORD")


@app.middleware("http")
async def _docs_basic_auth_middleware(request, call_next):
    # Only enforce when credentials are configured
    if _DOCS_USER and _DOCS_PASS:
        path = request.url.path or ""
        # Protect docs UI, its assets and the OpenAPI JSON
        if path.startswith("/docs") or path.startswith("/redoc") or path.startswith("/openapi.json"):
            auth = request.headers.get("authorization")
            if not auth or not auth.lower().startswith("basic "):
                return Response(status_code=401, headers={"WWW-Authenticate": "Basic realm=\"Docs\""}, content="Unauthorized")
            try:
                b64 = auth.split(" ", 1)[1]
                decoded = base64.b64decode(b64).decode("utf-8")
                user, pwd = decoded.split(":", 1)
            except Exception:
                return Response(status_code=401, headers={"WWW-Authenticate": "Basic realm=\"Docs\""}, content="Unauthorized")
            if not (secrets.compare_digest(user, _DOCS_USER) and secrets.compare_digest(pwd, _DOCS_PASS)):
                return Response(status_code=401, headers={"WWW-Authenticate": "Basic realm=\"Docs\""}, content="Unauthorized")
    return await call_next(request)

# ✅ Trusted Hosts
app.add_middleware(
    TrustedHostMiddleware,
    allowed_hosts=["vidyaroop.com","api.vidyaroop.com", "localhost", "127.0.0.1"]
)

# ✅ HTTPS Redirection (optional if NGINX handles it)
if os.getenv("ENV") == "Production":
    app.add_middleware(HTTPSRedirectMiddleware)

# ✅ CORS Settings
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
    allow_credentials=True,
)

# ✅ Exception Handlers
app.add_exception_handler(Exception, global_exception_handler)
app.add_exception_handler(StarletteHTTPException, global_exception_handler)
app.add_exception_handler(RequestValidationError, global_exception_handler)

# ✅ Routers
app.include_router(auth_router, prefix="/auth", tags=["Authentication"])
app.include_router(course_router, prefix="/api/course", tags=["Course"])
app.include_router(course_module_router, prefix="/api/courseModule", tags=["CourseModule"])
app.include_router(util_router, prefix="/api/media", tags=["Video"])
app.include_router(category_router, prefix="/api/category", tags=["Category"])
app.include_router(course_progress_router, prefix="/api/courseProgress", tags=["CourseProgress"])
app.include_router(instamojo_router, prefix="/api", tags=["Instamojo"])
app.include_router(cart_router, prefix="/api/cart", tags=["Cart"])
app.include_router(email_router, prefix="/api/email", tags=["Email"])

# Serve uploaded files from the `Uploads` directory at the `/uploads` URL path.
# Use an absolute path to the folder so mounting works regardless of CWD.
uploads_dir = os.path.join(os.path.dirname(__file__), "Uploads")
if not os.path.isdir(uploads_dir):
    try:
        os.makedirs(uploads_dir, exist_ok=True)
    except Exception:
        # If creation fails, continue without mount — app should still run.
        uploads_dir = None

if uploads_dir:
    app.mount("/uploads", StaticFiles(directory=uploads_dir), name="uploads")
    # Also mount capitalized path to support clients requesting `/Uploads/...`
    app.mount("/Uploads", StaticFiles(directory=uploads_dir), name="Uploads")

@app.on_event("startup")
def _start_background_jobs():
    # start cache refresher every 15 minutes
    start_cache_refresh_thread(interval_seconds=15 * 60)
    # start email sender thread (interval from env, default 60s)
    start_email_sender(interval_seconds=int(os.getenv('EMAIL_SENDER_INTERVAL', '60')))


@app.on_event("shutdown")
def _stop_background_jobs():
    stop_cache_refresh_thread()
    stop_email_sender()

# ✅ Root Endpoint
@app.get("/", response_class=HTMLResponse)
def root():
    return """
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>ZapLearn API</title>
        <link rel="icon" href="favicon.ico" type="image/x-icon">
        <style>
            body {
                font-family: Arial, sans-serif;
                margin: 0;
                padding: 0;
                display: flex;
                justify-content: center;
                align-items: center;
                height: 100vh;
                background-color: #f4f4f9;
            }
            .container {
                text-align: center;
                padding: 20px;
                border: 1px solid #ddd;
                border-radius: 10px;
                background: #fff;
                box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
            }
            h1 {
                color: #333;
            }
            p {
                color: #555;
            }
            a {
                text-decoration: none;
                color: #007BFF;
                font-weight: bold;
            }
            a:hover {
                text-decoration: underline;
            }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>Welcome to ZapLearn API</h1>
            <p>Your gateway to learning and development.</p>
            <p>Explore the <a href="/docs">API Documentation</a> to get started.</p>
        </div>
    </body>
    </html>
    """

#uvicorn app:app --host=127.0.0.1 --port=8000 --reload
