from fastapi import APIRouter, UploadFile, File, HTTPException, Request, WebSocket
from fastapi.responses import HTMLResponse, StreamingResponse, JSONResponse, Response
from fastapi.templating import Jinja2Templates
import aiofiles
import uuid
import asyncio
import logging
import hashlib
from datetime import datetime, timedelta
from pathlib import Path
from urllib.parse import quote
from typing import Dict, Any
from config import Config

logger = logging.getLogger(__name__)
router = APIRouter()
templates = Jinja2Templates(directory="templates")

redis_db = None
minio = None
integrated_scan = None

active_connections: Dict[str, WebSocket] = {}

def get_services():
    global redis_db, minio, integrated_scan
    
    if redis_db is None:
        from services.redis_db import RedisDB
        redis_db = RedisDB()
        
    if minio is None:
        from services.storage import MinIOService
        try:
            minio = MinIOService()
        except Exception as e:
            logger.error(f"Failed to initialize MinIO: {e}")
            
    if integrated_scan is None:
        from services.integrated_scan import IntegratedScanService
        integrated_scan = IntegratedScanService()
        integrated_scan.redis_db = redis_db
    
    return redis_db, minio, integrated_scan

@router.post("/api/create_session")
async def create_session(data: dict):
    try:
        redis_db, _, _ = get_services()
        
        token = str(uuid.uuid4())
        session_data = {
            "session_id": str(uuid.uuid4()),
            "discord_server_id": data["discord_server_id"],
            "discord_user_id": data["discord_user_id"],
            "discord_username": data["discord_username"],
            "created_at": datetime.utcnow().isoformat(),
            "expires_at": (datetime.utcnow() + timedelta(days=3,hours=9)).isoformat(),
            "status": "pending",
            "files": []
        }
        
        await redis_db.set_session(token, session_data)
        logger.info(f"Session created: {token} for user {data['discord_username']}")
        
        return {"token": token, "expires_at": session_data["expires_at"]}
    except Exception as e:
        logger.error(f"Error creating session: {e}")
        raise HTTPException(500, "Failed to create session")

@router.get("/upload/{token}")
async def upload_page(token: str, request: Request):
    redis_db, _, _ = get_services()
    
    session = await redis_db.get_session(token)
    if not session:
        return templates.TemplateResponse("error.html", {
            "request": request,
            "error": "Session not found"
        })
    
    return templates.TemplateResponse("upload.html", {
        "request": request,
        "token": token,
        "expires_at": session["expires_at"]
    })

@router.websocket("/ws/upload/{token}")
async def upload_websocket(websocket: WebSocket, token: str):
    await websocket.accept()
    active_connections[token] = websocket
    
    try:
        while True:
            await websocket.receive_text()
    except Exception as e:
        logger.info(f"WebSocket disconnected for {token}: {e}")
    finally:
        if token in active_connections:
            del active_connections[token]

@router.post("/api/upload/{token}")
async def upload_file(token: str, file: UploadFile = File(...)):
    try:
        redis_db, minio, scan_service = get_services()
        
        if minio is None:
            raise HTTPException(503, "Storage service is unavailable")
        
        session = await redis_db.get_session(token)
        if not session:
            raise HTTPException(404, "Invalid session")
        
        contents = await file.read()
        file_size = len(contents)
        
        if file_size > Config.MAX_FILE_SIZE:
            raise HTTPException(413, f"File size exceeds {Config.MAX_FILE_SIZE // (1024**3)}GB limit")
        
        file_ext = Path(file.filename).suffix.lower()
        if file_ext not in Config.ALLOWED_EXTENSIONS:
            raise HTTPException(415, f"File type not allowed: {file_ext}")
        
        file_id = str(uuid.uuid4())
        
        async def progress_callback(percent: float, message: str):
            if token in active_connections:
                try:
                    await active_connections[token].send_json({
                        "type": "progress",
                        "percent": percent,
                        "message": message
                    })
                except:
                    pass
        
        await progress_callback(5, "スキャン準備中...")
        
        file_info = {
            "uuid": file_id,
            "name": file.filename,
            "size": file_size,
            "extension": file_ext
        }
        
        session_info = {
            "token": token,
            "discord_user_id": session.get("discord_user_id"),
            "discord_username": session.get("discord_username")
        }
        
        scan_result = await scan_service.scan_file(
            contents,
            file_info,
            session_info,
            progress_callback
        )
        
        if not scan_result['allow_upload']:
            logger.warning(f"File rejected: {file.filename} - {scan_result['rejection_reason']}")
            
            if token in active_connections:
                await active_connections[token].send_json({
                    "type": "error",
                    "message": scan_result['rejection_reason']
                })
            
            raise HTTPException(400, scan_result['rejection_reason'])
        
        await progress_callback(95, "ファイル保存中...")
        
        await file.seek(0)
        
        safe_filename = file.filename.encode('utf-8', 'ignore').decode('utf-8')
        file_path = f"uploads/{datetime.utcnow().strftime('%Y-%m-%d')}/{file_id}_{safe_filename}"
        
        success = await minio.upload_file(file, file_path)
        if not success:
            raise HTTPException(500, "Failed to save file")

        configured_tz = Config.get_timezone()
        upload_time_local = datetime.now(configured_tz)
        
        file_info_data = {
            "original_name": file.filename,
            "stored_name": file_path,
            "size": file_size,
            "mime_type": file.content_type,
            "uploaded_at": datetime.utcnow().isoformat(),
            "uploaded_at_local": upload_time_local.strftime('%Y-%m-%d %H:%M:%S'),
            "virus_scan": scan_result['overall_status'],
            "clamav_result": scan_result['clamav_result'],
            "virustotal_result": scan_result['virustotal_result'],
            "virus_scan_hash": scan_result['file_hash'],
            "minio_path": file_path,
            "download_enabled": True
        }
        
        await redis_db.set_file(session["session_id"], file_id, file_info_data)
        
        session["files"].append(file_id)
        session["status"] = "uploaded"
        await redis_db.set_session(token, session)
        
        await progress_callback(100, "完了！")
        
        logger.info(f"File uploaded successfully: {file.filename} ({file_size} bytes)")
        
        warning = None
        if scan_result['overall_status'] == 'suspicious':
            warning = "File was flagged as suspicious but upload was allowed"
        elif scan_result['virustotal_result'] == 'unknown':
            warning = "VirusTotal verification not available, but ClamAV marked file as safe"
        
        return JSONResponse({
            "success": True,
            "file_id": file_id,
            "filename": file.filename,
            "size": file_size,
            "virus_scan": scan_result['overall_status'],
            "clamav_result": scan_result['clamav_result'],
            "virustotal_result": scan_result['virustotal_result'],
            "download_url": f"/file/{token}/{file_id}",
            "warning": warning
        })
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Upload error: {e}")
        raise HTTPException(500, f"Error occurred during upload: {str(e)}")

@router.get("/file/{token}/{file_id}")
async def file_info_page(token: str, file_id: str, request: Request):
    try:
        redis_db, _, scan_service = get_services()
        
        session = await redis_db.get_session(token)
        if not session or file_id not in session["files"]:
            return templates.TemplateResponse("error.html", {
                "request": request,
                "error": "File not found"
            })
        
        file_info = await redis_db.get_file(session["session_id"], file_id)
        if not file_info:
            return templates.TemplateResponse("error.html", {
                "request": request,
                "error": "File information not found"
            })
        
        scan_status = await scan_service.get_scan_status(file_id)
        
        size = file_info['size']
        if size < 1024:
            size_str = f"{size} B"
        elif size < 1024 * 1024:
            size_str = f"{size / 1024:.2f} KB"
        elif size < 1024 * 1024 * 1024:
            size_str = f"{size / (1024 * 1024):.2f} MB"
        else:
            size_str = f"{size / (1024 * 1024 * 1024):.2f} GB"
        
        mime_type = file_info.get('mime_type', '')
        is_video = mime_type.startswith('video/')
        is_image = mime_type.startswith('image/')
        is_audio = mime_type.startswith('audio/')
        is_pdf = mime_type == 'application/pdf'
        
        allow_download = True
        if file_info.get('virus_scan') == 'infected':
            allow_download = False
        elif file_info.get('virus_scan') == 'pending' and not Config.ALLOW_PENDING_DOWNLOAD:
            allow_download = False
        
        return templates.TemplateResponse("download.html", {
            "request": request,
            "token": token,
            "file_id": file_id,
            "file_info": file_info,
            "size_str": size_str,
            "uploaded_at": file_info.get('uploaded_at_local', file_info.get('uploaded_at', 'Unknown')),
            "virus_scan_status": file_info.get('virus_scan', 'unknown'),
            "clamav_status": file_info.get('clamav_result', 'unknown'),
            "virustotal_status": file_info.get('virustotal_result', 'unknown'),
            "is_video": is_video,
            "is_image": is_image,
            "is_audio": is_audio,
            "is_pdf": is_pdf,
            "mime_type": mime_type,
            "session": session,
            "allow_download": allow_download,
            "scan_details": scan_status
        })
        
    except Exception as e:
        logger.error(f"Error displaying file info: {e}")
        return templates.TemplateResponse("error.html", {
            "request": request,
            "error": "Failed to retrieve file information"
        })

@router.get("/api/file/{token}/{file_id}/status")
async def get_file_status(token: str, file_id: str):
    try:
        redis_db, _, scan_service = get_services()
        
        session = await redis_db.get_session(token)
        if not session or file_id not in session["files"]:
            raise HTTPException(404, "File not found")
        
        file_info = await redis_db.get_file(session["session_id"], file_id)
        if not file_info:
            raise HTTPException(404, "File information not found")
        
        scan_status = await scan_service.get_scan_status(file_id)
        
        return JSONResponse({
            "virus_scan": file_info.get("virus_scan", "unknown"),
            "clamav_result": file_info.get("clamav_result", "unknown"),
            "virustotal_result": file_info.get("virustotal_result", "unknown"),
            "virus_scan_hash": file_info.get("virus_scan_hash", None),
            "scan_details": scan_status
        })
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting file status: {e}")
        raise HTTPException(500, "Failed to retrieve status")

@router.get("/download/{token}/{file_id}")
async def download_file(token: str, file_id: str):
    try:
        redis_db, minio, _ = get_services()
        
        if minio is None:
            raise HTTPException(503, "Storage service is unavailable")
        
        session = await redis_db.get_session(token)
        if not session or file_id not in session["files"]:
            raise HTTPException(404, "File not found")
        
        file_info = await redis_db.get_file(session["session_id"], file_id)
        if not file_info:
            raise HTTPException(404, "File information not found")
        
        if file_info.get("virus_scan") == "infected" or file_info.get("clamav_result") == "infected":
            raise HTTPException(403, "Download blocked: virus detected")
        
        if file_info.get("virus_scan") == "pending" and not Config.ALLOW_PENDING_DOWNLOAD:
            raise HTTPException(403, "Security scan in progress. Please wait for completion")
        
        if file_info.get("virus_scan") == "suspicious":
            logger.warning(f"Suspicious file downloaded: {file_info['original_name']} by session {token}")
        
        file_stream = await minio.get_file_stream(file_info["minio_path"])
        if not file_stream:
            raise HTTPException(404, "File not found")
        
        logger.info(f"File downloaded: {file_info['original_name']} from session {token}")
        
        original_name = file_info['original_name']
        ascii_name = original_name.encode('ascii', 'ignore').decode('ascii')
        if not ascii_name:
            ascii_name = f"file_{file_id}{Path(original_name).suffix}"
        
        encoded_name = quote(original_name.encode('utf-8'))
        content_disposition = f"attachment; filename=\"{ascii_name}\"; filename*=UTF-8''{encoded_name}"
        
        return StreamingResponse(
            file_stream,
            media_type=file_info.get("mime_type", "application/octet-stream"),
            headers={
                "Content-Disposition": content_disposition,
                "Content-Type": file_info.get("mime_type", "application/octet-stream"),
                "X-Virus-Scan-Status": file_info.get("virus_scan", "unknown"),
                "X-ClamAV-Status": file_info.get("clamav_result", "unknown"),
                "X-VirusTotal-Status": file_info.get("virustotal_result", "unknown")
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Download error: {e}")
        raise HTTPException(500, "Error occurred during download")

@router.get("/api/scan/stats")
async def get_scan_statistics():
    try:
        _, _, scan_service = get_services()
        stats = await scan_service.db.get_statistics()
        return JSONResponse(stats)
    except Exception as e:
        logger.error(f"Error getting statistics: {e}")
        raise HTTPException(500, "Failed to retrieve statistics")

@router.get("/api/health")
async def health():
    try:
        redis_db, minio, scan_service = get_services()
        
        health_status = {
            "status": "healthy",
            "timestamp": datetime.utcnow().isoformat(),
            "services": {
                "redis": "unknown",
                "minio": "unknown", 
                "clamav": "unknown"
            }
        }
        
        try:
            await redis_db.ping()
            health_status["services"]["redis"] = "healthy"
        except:
            health_status["services"]["redis"] = "unhealthy"
            health_status["status"] = "degraded"
        
        if minio:
            health_status["services"]["minio"] = "healthy"
        else:
            health_status["services"]["minio"] = "unhealthy"
            health_status["status"] = "degraded"
        
        try:
            if await scan_service.clamav.ping():
                health_status["services"]["clamav"] = "healthy"
            else:
                health_status["services"]["clamav"] = "unhealthy"
                health_status["status"] = "degraded"
        except:
            health_status["services"]["clamav"] = "unhealthy"
            health_status["status"] = "degraded"
        
        return JSONResponse(health_status)
        
    except Exception as e:
        logger.error(f"Health check error: {e}")
        return JSONResponse({
            "status": "unhealthy",
            "error": str(e),
            "timestamp": datetime.utcnow().isoformat()
        })

@router.get("/")
async def root(request: Request):
    return templates.TemplateResponse("index.html", {
        "request": request
    })