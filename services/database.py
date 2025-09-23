import sqlite3
import json
import asyncio
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Any
import logging
from contextlib import contextmanager

logger = logging.getLogger(__name__)

class ScanLogDatabase:
    def __init__(self, db_path: str = "db/scan_logs.db"):

        self.db_path = db_path
        self._ensure_db_directory()
        self._init_database()
    
    def _ensure_db_directory(self):
        db_dir = Path(self.db_path).parent
        db_dir.mkdir(parents=True, exist_ok=True)
    
    def _init_database(self):
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS scan_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    upload_time_jst TEXT NOT NULL,
                    file_name TEXT NOT NULL,
                    file_uuid TEXT NOT NULL UNIQUE,
                    file_extension TEXT,
                    file_size INTEGER,
                    file_hash TEXT,
                    clamav_result TEXT,
                    virustotal_result TEXT,
                    upload_status TEXT,  -- success, rejected, error
                    rejection_reason TEXT,
                    session_token TEXT,
                    discord_user_id TEXT,
                    discord_username TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_file_uuid 
                ON scan_logs(file_uuid)
            ''')
            
            cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_file_hash 
                ON scan_logs(file_hash)
            ''')
            
            cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_upload_time 
                ON scan_logs(upload_time_jst)
            ''')
            
            cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_discord_user 
                ON scan_logs(discord_user_id)
            ''')

            cursor.execute('''
                CREATE TABLE IF NOT EXISTS hash_blacklist (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    file_hash TEXT NOT NULL UNIQUE,
                    detection_source TEXT,  -- clamav, virustotal
                    detection_details TEXT,
                    first_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    last_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    hit_count INTEGER DEFAULT 1
                )
            ''')
            
            conn.commit()
            logger.info("Database initialized successfully")
    
    @contextmanager
    def _get_connection(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
        finally:
            conn.close()
    
    async def add_scan_log(self, log_data: Dict[str, Any]) -> int:
        def _insert():
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT INTO scan_logs (
                        upload_time_jst, file_name, file_uuid, 
                        file_extension, file_size, file_hash,
                        clamav_result, virustotal_result, 
                        upload_status, rejection_reason,
                        session_token, discord_user_id, discord_username
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    log_data.get('upload_time_jst'),
                    log_data.get('file_name'),
                    log_data.get('file_uuid'),
                    log_data.get('file_extension'),
                    log_data.get('file_size'),
                    log_data.get('file_hash'),
                    log_data.get('clamav_result'),
                    log_data.get('virustotal_result'),
                    log_data.get('upload_status'),
                    log_data.get('rejection_reason'),
                    log_data.get('session_token'),
                    log_data.get('discord_user_id'),
                    log_data.get('discord_username')
                ))
                conn.commit()
                return cursor.lastrowid
        
        return await asyncio.get_event_loop().run_in_executor(None, _insert)
    
    async def update_scan_result(self, file_uuid: str, 
                                 clamav_result: str = None, 
                                 virustotal_result: str = None):
        def _update():
            with self._get_connection() as conn:
                cursor = conn.cursor()
                
                updates = []
                params = []
                
                if clamav_result is not None:
                    updates.append("clamav_result = ?")
                    params.append(clamav_result)
                
                if virustotal_result is not None:
                    updates.append("virustotal_result = ?")
                    params.append(virustotal_result)
                
                if updates:
                    updates.append("updated_at = CURRENT_TIMESTAMP")
                    params.append(file_uuid)
                    
                    query = f'''
                        UPDATE scan_logs 
                        SET {", ".join(updates)}
                        WHERE file_uuid = ?
                    '''
                    
                    cursor.execute(query, params)
                    conn.commit()
        
        await asyncio.get_event_loop().run_in_executor(None, _update)
    
    async def add_to_blacklist(self, file_hash: str, 
                               detection_source: str, 
                               detection_details: str):
        def _add():
            with self._get_connection() as conn:
                cursor = conn.cursor()
                
                cursor.execute('''
                    SELECT id, hit_count FROM hash_blacklist 
                    WHERE file_hash = ?
                ''', (file_hash,))
                
                existing = cursor.fetchone()
                
                if existing:
                    cursor.execute('''
                        UPDATE hash_blacklist 
                        SET hit_count = hit_count + 1,
                            last_seen = CURRENT_TIMESTAMP,
                            detection_details = ?
                        WHERE file_hash = ?
                    ''', (detection_details, file_hash))
                else:
                    cursor.execute('''
                        INSERT INTO hash_blacklist 
                        (file_hash, detection_source, detection_details)
                        VALUES (?, ?, ?)
                    ''', (file_hash, detection_source, detection_details))
                
                conn.commit()
        
        await asyncio.get_event_loop().run_in_executor(None, _add)
    
    async def is_blacklisted(self, file_hash: str) -> Optional[Dict]:
        def _check():
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT * FROM hash_blacklist 
                    WHERE file_hash = ?
                ''', (file_hash,))
                
                row = cursor.fetchone()
                if row:
                    return dict(row)
                return None
        
        return await asyncio.get_event_loop().run_in_executor(None, _check)
    
    async def get_recent_logs(self, limit: int = 100) -> List[Dict]:
        def _get():
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT * FROM scan_logs 
                    ORDER BY created_at DESC 
                    LIMIT ?
                ''', (limit,))
                
                return [dict(row) for row in cursor.fetchall()]
        
        return await asyncio.get_event_loop().run_in_executor(None, _get)
    
    async def get_user_logs(self, discord_user_id: str) -> List[Dict]:
        def _get():
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT * FROM scan_logs 
                    WHERE discord_user_id = ?
                    ORDER BY created_at DESC
                ''', (discord_user_id,))
                
                return [dict(row) for row in cursor.fetchall()]
        
        return await asyncio.get_event_loop().run_in_executor(None, _get)
    
    async def cleanup_old_logs(self, retention_days: int = 365):
        def _cleanup():
            cutoff_date = datetime.now() - timedelta(days=retention_days)
            
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    DELETE FROM scan_logs 
                    WHERE created_at < ?
                ''', (cutoff_date.isoformat(),))
                
                deleted = cursor.rowcount
                conn.commit()
                return deleted
        
        deleted = await asyncio.get_event_loop().run_in_executor(None, _cleanup)
        logger.info(f"Cleaned up {deleted} old log entries")
        return deleted
    
    async def get_statistics(self) -> Dict[str, Any]:
        def _get_stats():
            with self._get_connection() as conn:
                cursor = conn.cursor()
                
                cursor.execute('''
                    SELECT 
                        COUNT(*) as total_uploads,
                        SUM(CASE WHEN upload_status = 'success' THEN 1 ELSE 0 END) as successful,
                        SUM(CASE WHEN upload_status = 'rejected' THEN 1 ELSE 0 END) as rejected,
                        SUM(file_size) as total_size,
                        COUNT(DISTINCT discord_user_id) as unique_users
                    FROM scan_logs
                ''')
                
                overall = dict(cursor.fetchone())

                cursor.execute('''
                    SELECT 
                        SUM(CASE WHEN clamav_result = 'infected' THEN 1 ELSE 0 END) as clamav_detections,
                        SUM(CASE WHEN virustotal_result = 'infected' THEN 1 ELSE 0 END) as vt_detections
                    FROM scan_logs
                ''')
                
                detections = dict(cursor.fetchone())

                cursor.execute('''
                    SELECT COUNT(*) as blacklisted_hashes
                    FROM hash_blacklist
                ''')
                
                blacklist = dict(cursor.fetchone())
                
                return {
                    **overall,
                    **detections,
                    **blacklist,
                    'timestamp': datetime.now().isoformat()
                }
        
        return await asyncio.get_event_loop().run_in_executor(None, _get_stats)