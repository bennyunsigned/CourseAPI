from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
from fastapi.middleware.cors import CORSMiddleware  # Import CORS middleware
from Utils.ExceptionHandler import global_exception_handler
from Controllers.authController import auth_router
from Controllers.courseController import course_router
from Controllers.courseModuleController import course_module_router
from Controllers.utilController import util_router
from Controllers.categoryController import category_router

app = FastAPI(title="Vidyaroop API", description="API for Vidyaroop Learning Platform", version="1.0.0")

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow only the Angular frontend's origin
    allow_credentials=False,
    allow_methods=["*"],  # Allow all HTTP methods
    allow_headers=["*"],  # Allow all headers
)

# Include the routers
app.include_router(auth_router, prefix="/auth", tags=["Authentication"])
app.include_router(course_router, prefix="/course", tags=["Course"])
app.include_router(course_module_router, prefix="/courseModule", tags=["CourseModule"])
app.include_router(util_router, prefix="/media", tags=["Video"])
app.include_router(category_router, prefix="/category", tags=["Category"])

# Register the global exception handler
app.add_exception_handler(Exception, global_exception_handler)
app.add_exception_handler(StarletteHTTPException, global_exception_handler)
app.add_exception_handler(RequestValidationError, global_exception_handler)

@app.get("/", response_class=HTMLResponse)
def root():
    return """
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>ZapLearn API</title>
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