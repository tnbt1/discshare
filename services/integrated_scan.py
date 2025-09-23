import hashlib
import logging
import asyncio
from datetime import datetime
from typing import Dict, Tuple, Optional, Any
from pathlib import Path
import pytz

from services.clamav_scan import ClamAVService
from services.virus_scan import VirusScan
from services.database import ScanLogDatabase
from config import Config

logger = logging.getLogger(__name__)

class IntegratedScanService:
    def __init__(self):
        self.clamav = ClamAVService()
        self.virustotal = VirusScan()
        self.db = ScanLogDatabase(Config.SCAN_LOG_DB_PATH if hasattr(Config, 'SCAN_LOG_DB_PATH') else "db/scan_logs.db")
        self.jst = pytz.timezone('Asia/Tokyo')
        
    async def scan_file(self, 
                        file_content: bytes, 
                        file_info: Dict[str, Any],
                        session_info: Dict[str, Any],
                        progress_callback=None) -> Dict[str, Any]:
        result = {
            'file_uuid': file_info['uuid'],
            'file_name': file_info['name'],
            'file_size': file_info['size'],
            'file_extension': file_info.get('extension', ''),
            'upload_time_jst': datetime.now(self.jst).strftime('%Y-%m-%d %H:%M:%S'),
            'clamav_result': 'pending',
            'virustotal_result': 'pending',
            'file_hash': None,
            'upload_status': 'pending',
            'rejection_reason': None,
            'overall_status': 'pending',
            'allow_upload': False
        }
        
        try:
            if progress_callback:
                await progress_callback(10, "ハッシュ計算中...")
            
            file_hash = hashlib.sha256(file_content).hexdigest()
            result['file_hash'] = file_hash
            logger.info(f"File hash calculated: {file_hash}")
            if progress_callback:
                await progress_callback(20, "ブラックリストチェック中...")
            
            blacklist_info = await self.db.is_blacklisted(file_hash)
            if blacklist_info:
                logger.warning(f"File {file_info['name']} is blacklisted: {blacklist_info}")
                result['upload_status'] = 'rejected'
                result['rejection_reason'] = f"既知の感染ファイル（過去の検出: {blacklist_info['detection_source']}）"
                result['overall_status'] = 'infected'
                result['clamav_result'] = 'blacklisted'
                result['virustotal_result'] = 'blacklisted'

                await self._save_log(result, session_info)
                return result

            if progress_callback:
                await progress_callback(30, "ClamAVスキャン中...")

            async def clamav_progress(percent, message):
                actual_progress = 30 + (percent * 0.3)
                await progress_callback(actual_progress, f"ClamAV: {message}")
            
            clamav_status, clamav_details = await self.clamav.scan_file_content(
                file_content, 
                clamav_progress if progress_callback else None
            )
            
            result['clamav_result'] = clamav_status
            logger.info(f"ClamAV scan result: {clamav_status} - {clamav_details}")

            if clamav_status == 'infected':
                result['upload_status'] = 'rejected'
                result['rejection_reason'] = f"ClamAV: {clamav_details}"
                result['overall_status'] = 'infected'

                await self.db.add_to_blacklist(file_hash, 'clamav', clamav_details)

                await self._save_log(result, session_info)
                return result

            if progress_callback:
                await progress_callback(70, "VirusTotalチェック中...")
            
            if Config.VIRUSTOTAL_API_KEY:
                try:
                    vt_result = await self.virustotal.check_file_hash(file_hash)
                    result['virustotal_result'] = vt_result
                    logger.info(f"VirusTotal hash check: {vt_result}")

                    if vt_result == 'infected':
                        result['upload_status'] = 'rejected'
                        result['rejection_reason'] = 'VirusTotal: マルウェア検出'
                        result['overall_status'] = 'infected'

                        await self.db.add_to_blacklist(file_hash, 'virustotal', 'Malware detected')

                        await self._save_log(result, session_info)
                        return result

                    elif vt_result == 'unknown' and file_info['size'] <= 32 * 1024 * 1024:
                        if progress_callback:
                            await progress_callback(75, "VirusTotalに送信中...")
                        
                        logger.info(f"Submitting file to VirusTotal: {file_info['name']} ({file_info['size']} bytes)")

                        scan_id = await self.virustotal.submit_file_for_scan(file_content)
                        
                        if scan_id:
                            logger.info(f"VirusTotal submission successful, scan ID: {scan_id}")

                            if progress_callback:
                                await progress_callback(80, "VirusTotalスキャン結果待機中...")

                            for wait_count in range(5):
                                await asyncio.sleep(20)
                                
                                if progress_callback:
                                    await progress_callback(
                                        80 + (wait_count + 1) * 3, 
                                        f"VirusTotalスキャン待機中...({(wait_count + 1) * 20}秒経過)"
                                    )

                                report = await self.virustotal.get_scan_report(scan_id)
                                
                                if report and report.get('status') == 'completed':
                                    stats = report.get('stats', {})
                                    if stats.get('malicious', 0) > 0:
                                        result['virustotal_result'] = 'infected'
                                        result['upload_status'] = 'rejected'
                                        result['rejection_reason'] = f"VirusTotal: {stats.get('malicious', 0)}個のエンジンで検出"
                                        result['overall_status'] = 'infected'

                                        await self.db.add_to_blacklist(
                                            file_hash, 
                                            'virustotal', 
                                            f"Detected by {stats.get('malicious', 0)} engines"
                                        )

                                        await self._save_log(result, session_info)
                                        return result
                                        
                                    elif stats.get('suspicious', 0) > 0:
                                        result['virustotal_result'] = 'suspicious'
                                        result['overall_status'] = 'suspicious'
                                    else:
                                        result['virustotal_result'] = 'clean'
                                    
                                    logger.info(f"VirusTotal scan completed after {(wait_count + 1) * 20} seconds: {result['virustotal_result']}")
                                    break
                            else:
                                result['virustotal_result'] = 'pending'
                                logger.info(f"VirusTotal scan still pending after 60 seconds for {file_info['uuid']}")
                        else:
                            logger.warning(f"Failed to submit file to VirusTotal")
                            result['virustotal_result'] = 'error'
                    
                    elif vt_result == 'suspicious':
                        result['overall_status'] = 'suspicious'
                        
                except Exception as e:
                    logger.error(f"VirusTotal check failed: {e}")
                    result['virustotal_result'] = 'error'
                    if result['clamav_result'] == 'clean':
                        result['virustotal_result'] = 'error'
            else:
                result['virustotal_result'] = 'skipped'
            
            if progress_callback:
                await progress_callback(90, "最終判定中...")
            
            if clamav_status == 'clean':
                if result['virustotal_result'] in ['clean', 'unknown', 'skipped', 'error', 'pending']:
                    result['upload_status'] = 'success'
                    result['overall_status'] = 'clean'
                    result['allow_upload'] = True
                    if result['virustotal_result'] == 'error':
                        logger.info("VirusTotal check failed but ClamAV clean, allowing upload")
                elif result['virustotal_result'] == 'suspicious':
                    result['upload_status'] = 'success'
                    result['overall_status'] = 'suspicious'
                    result['allow_upload'] = True
                else:
                    result['upload_status'] = 'rejected'
                    result['overall_status'] = 'infected'
                    result['allow_upload'] = False
            else:
                result['upload_status'] = 'error'
                result['overall_status'] = 'error'
                result['rejection_reason'] = 'スキャンエラー'
                result['allow_upload'] = False

            if progress_callback:
                await progress_callback(100, "完了")
            
            await self._save_log(result, session_info)
            
            return result
            
        except Exception as e:
            logger.error(f"Integrated scan error: {e}")
            result['upload_status'] = 'error'
            result['overall_status'] = 'error'
            result['rejection_reason'] = str(e)

            await self._save_log(result, session_info)
            
            return result
    
    async def _save_log(self, scan_result: Dict, session_info: Dict):
        try:
            log_data = {
                'upload_time_jst': scan_result['upload_time_jst'],
                'file_name': scan_result['file_name'],
                'file_uuid': scan_result['file_uuid'],
                'file_extension': scan_result['file_extension'],
                'file_size': scan_result['file_size'],
                'file_hash': scan_result['file_hash'],
                'clamav_result': scan_result['clamav_result'],
                'virustotal_result': scan_result['virustotal_result'],
                'upload_status': scan_result['upload_status'],
                'rejection_reason': scan_result.get('rejection_reason'),
                'session_token': session_info.get('token'),
                'discord_user_id': session_info.get('discord_user_id'),
                'discord_username': session_info.get('discord_username')
            }

            await self.db.add_scan_log(log_data)

            if self.redis_db:
                await self.redis_db.set(
                    f"scan_result:{scan_result['file_uuid']}", 
                    log_data,
                    expire=86400
                )
            
            logger.info(f"Scan log saved for file {scan_result['file_uuid']}")
            
        except Exception as e:
            logger.error(f"Failed to save scan log: {e}")
    
    async def get_scan_status(self, file_uuid: str) -> Optional[Dict]:
        if self.redis_db:
            result = await self.redis_db.get(f"scan_result:{file_uuid}")
            if result:
                return result

        logs = await self.db.get_recent_logs(100)
        for log in logs:
            if log['file_uuid'] == file_uuid:
                return log
        
        return None
    
    async def update_virustotal_result(self, file_uuid: str, vt_result: str):
        await self.db.update_scan_result(file_uuid, virustotal_result=vt_result)
        
        if self.redis_db:
            existing = await self.redis_db.get(f"scan_result:{file_uuid}")
            if existing:
                existing['virustotal_result'] = vt_result
                await self.redis_db.set(f"scan_result:{file_uuid}", existing, expire=86400)