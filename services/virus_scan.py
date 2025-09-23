import aiohttp
import hashlib
import logging
from typing import Optional, Dict, Any
from config import Config

logger = logging.getLogger(__name__)

class VirusScan:
    def __init__(self):
        self.api_key = Config.VIRUSTOTAL_API_KEY
        self.base_url = "https://www.virustotal.com/api/v3"
        self.redis_db = None
        self.minio = None
    
    def _get_services(self):
        if self.redis_db is None:
            from services.redis_db import RedisDB
            self.redis_db = RedisDB()
        if self.minio is None:
            from services.storage import MinIOService
            try:
                self.minio = MinIOService()
            except Exception as e:
                logger.error(f"Failed to initialize MinIO in VirusScan: {e}")
        return self.redis_db, self.minio
    
    async def scan_async(self, file_path: str, file_id: str, session_id: str = None):
        if not self.api_key:
            logger.info("VirusTotal API key not configured, skipping scan")
            return "skipped"
        
        redis_db, minio = self._get_services()
        
        try:
            file_content = await self._get_file_content(file_path)
            if not file_content:
                logger.error(f"Failed to get file content for scanning: {file_path}")
                return "error"
            
            file_hash = self.calculate_sha256(file_content)
            logger.info(f"Calculated hash for {file_id}: {file_hash}")
            

            scan_result = await self.check_file_hash(file_hash)
            logger.info(f"Virus scan result for {file_id}: {scan_result}")
            
            if scan_result == "unknown" and len(file_content) <= 32 * 1024 * 1024:
                logger.info(f"File {file_id} is unknown, submitting for scan...")
                scan_id = await self.submit_file_for_scan(file_content)
                
                if scan_id:
                    logger.info(f"File {file_id} submitted for scan, ID: {scan_id}")
                    await asyncio.sleep(15)
                    report = await self.get_scan_report(scan_id)
                    if report and report.get('status') == 'completed':
                        stats = report.get('stats', {})
                        if stats.get('malicious', 0) > 0:
                            scan_result = "infected"
                        elif stats.get('suspicious', 0) > 0:
                            scan_result = "suspicious"
                        else:
                            scan_result = "clean"
                        logger.info(f"Scan completed for {file_id}: {scan_result}")
                    else:
                        scan_result = "pending"
                        logger.info(f"Scan still pending for {file_id}")
            
            if session_id and redis_db:
                file_info = await redis_db.get_file(session_id, file_id)
                if file_info:
                    file_info["virus_scan"] = scan_result
                    file_info["virus_scan_hash"] = file_hash
                    await redis_db.set_file(session_id, file_id, file_info)
                    logger.info(f"Updated virus scan status for {file_id}: {scan_result}")
            
            return scan_result
            
        except Exception as e:
            logger.error(f"Virus scan error for {file_id}: {e}")
            return "error"
    
    async def _get_file_content(self, file_path: str) -> Optional[bytes]:
        _, minio = self._get_services()
        if not minio:
            return None
        
        try:
            file_stream = await minio.get_file_stream(file_path)
            if file_stream:
                chunks = []
                async for chunk in file_stream:
                    chunks.append(chunk)
                return b''.join(chunks)
            return None
        except Exception as e:
            logger.error(f"Failed to get file from MinIO: {e}")
            return None
    
    async def check_file_hash(self, file_hash: str) -> str:
        if not self.api_key:
            return "skipped"
        
        headers = {"x-apikey": self.api_key}
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    f"{self.base_url}/files/{file_hash}",
                    headers=headers
                ) as response:
                    if response.status == 200:
                        data = await response.json()
                        stats = data['data']['attributes']['last_analysis_stats']
                        
                        if stats['malicious'] > 0:
                            return "infected"
                        elif stats['suspicious'] > 0:
                            return "suspicious"
                        else:
                            return "clean"
                    elif response.status == 404:
                        return "unknown"
                    else:
                        logger.warning(f"VirusTotal API returned status {response.status}")
                        return "error"
                        
        except Exception as e:
            logger.error(f"VirusTotal API error: {e}")
            return "error"
    
    async def submit_file_for_scan(self, file_content: bytes) -> Optional[str]:
        if not self.api_key or len(file_content) > 32 * 1024 * 1024:
            return None
        
        headers = {"x-apikey": self.api_key}
        
        try:
            async with aiohttp.ClientSession() as session:
                data = aiohttp.FormData()
                data.add_field('file', file_content, filename='file')
                
                async with session.post(
                    f"{self.base_url}/files",
                    headers=headers,
                    data=data
                ) as response:
                    if response.status == 200:
                        result = await response.json()
                        return result['data']['id']
                    return None
                    
        except Exception as e:
            logger.error(f"Failed to submit file to VirusTotal: {e}")
            return None
    
    async def get_scan_report(self, scan_id: str) -> Dict[str, Any]:
        if not self.api_key:
            return {"status": "skipped"}
        
        headers = {"x-apikey": self.api_key}
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    f"{self.base_url}/analyses/{scan_id}",
                    headers=headers
                ) as response:
                    if response.status == 200:
                        data = await response.json()
                        return data['data']['attributes']
                    return {"status": "error"}
                    
        except Exception as e:
            logger.error(f"Failed to get scan report: {e}")
            return {"status": "error"}
    
    def calculate_sha256(self, file_content: bytes) -> str:
        return hashlib.sha256(file_content).hexdigest()