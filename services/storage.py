from minio import Minio
from minio.error import S3Error
import io
import logging
from typing import Optional
from config import Config

logger = logging.getLogger(__name__)

class MinIOService:
    def __init__(self):
        self.client = Minio(
            Config.MINIO_ENDPOINT,
            access_key=Config.MINIO_ACCESS_KEY,
            secret_key=Config.MINIO_SECRET_KEY,
            secure=False
        )
        self.bucket = Config.MINIO_BUCKET
        self._ensure_bucket()
    
    def _ensure_bucket(self):
        try:
            if not self.client.bucket_exists(self.bucket):
                self.client.make_bucket(self.bucket)
                logger.info(f"Created bucket: {self.bucket}")
        except S3Error as e:
            logger.error(f"MinIO bucket error: {e}")
    
    async def upload_file(self, file, object_name: str) -> bool:
        try:
            contents = await file.read()
            file_size = len(contents)
            data = io.BytesIO(contents)
            
            self.client.put_object(
                self.bucket,
                object_name,
                data,
                file_size,
                content_type=file.content_type
            )
            
            logger.info(f"Uploaded to MinIO: {object_name}")
            return True
            
        except Exception as e:
            logger.error(f"MinIO upload error: {e}")
            return False
    
    async def get_file_stream(self, object_name: str):
        try:
            response = self.client.get_object(self.bucket, object_name)

            async def stream_generator():
                try:
                    for data in response.stream(32*1024):
                        yield data
                finally:
                    response.close()
                    response.release_conn()
            
            return stream_generator()
            
        except S3Error as e:
            logger.error(f"MinIO get error: {e}")
            return None
    
    def delete_file(self, object_name: str) -> bool:
        try:
            self.client.remove_object(self.bucket, object_name)
            logger.info(f"Deleted from MinIO: {object_name}")
            return True
        except S3Error as e:
            logger.error(f"MinIO delete error: {e}")
            return False
    
    def get_file_info(self, object_name: str):
        try:
            stat = self.client.stat_object(self.bucket, object_name)
            return {
                "size": stat.size,
                "etag": stat.etag,
                "content_type": stat.content_type,
                "last_modified": stat.last_modified
            }
        except S3Error as e:
            logger.error(f"MinIO stat error: {e}")
            return None
