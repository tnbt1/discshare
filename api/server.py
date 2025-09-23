from fastapi import FastAPI, Request
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from starlette.exceptions import HTTPException as StarletteHTTPException
import logging
from api.routes import router

logger = logging.getLogger(__name__)

app = FastAPI(
    title="File Share Service",
    description="Discord連携ファイル共有サービス",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

@app.exception_handler(404)
async def not_found_handler(request: Request, exc):
    return templates.TemplateResponse("error.html", {
        "request": request,
        "error": "ページが見つかりません"
    })

app.include_router(router)

@app.on_event("startup")
async def startup_event():
    logger.info("FastAPI server started")

@app.on_event("shutdown")
async def shutdown_event():
    logger.info("FastAPI server shutting down")