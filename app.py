from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.middleware.httpsredirect import HTTPSRedirectMiddleware

# Exception Handler
from Utils.ExceptionHandler import global_exception_handler

# Routers
from Controllers.authController import auth_router
from Controllers.courseController import course_router
from Controllers.courseModuleController import course_module_router
from Controllers.utilController import util_router
from Controllers.categoryController import category_router
from Controllers.courseProgressController import course_progress_router

# ✅ FastAPI app
app = FastAPI(
    title="Vidyaroop API",
    description="API for Vidyaroop Learning Platform",
    version="1.0.0"
)

# ✅ Trusted Hosts
app.add_middleware(
    TrustedHostMiddleware,
    allowed_hosts=["vidyaroop.com","api.vidyaroop.com", "localhost", "127.0.0.1"]
)

# ✅ HTTPS Redirection (optional if NGINX handles it)
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
