import asyncio
import logging
import struct
from typing import Tuple, Optional, Dict
from config import Config

logger = logging.getLogger(__name__)

class ClamAVService:
    def __init__(self):
        self.host = Config.CLAMAV_HOST if hasattr(Config, 'CLAMAV_HOST') else 'clamav'
        self.port = int(Config.CLAMAV_PORT) if hasattr(Config, 'CLAMAV_PORT') else 3310
        self.timeout = int(Config.CLAMAV_TIMEOUT) if hasattr(Config, 'CLAMAV_TIMEOUT') else 300
        self.chunk_size = 32768  # 32KB
        self.max_retries = 3
        
    async def scan_file_content(self, file_content: bytes, 
                                progress_callback=None) -> Tuple[str, str]:
        for attempt in range(self.max_retries):
            try:
                result = await self._scan_with_instream(file_content, progress_callback)
                if result[0] != 'error' or attempt == self.max_retries - 1:
                    return result
                    
                logger.warning(f"ClamAV scan attempt {attempt + 1} failed, retrying...")
                await asyncio.sleep(2)
                
            except Exception as e:
                if attempt == self.max_retries - 1:
                    logger.error(f"ClamAV scan failed after {self.max_retries} attempts: {e}")
                    return 'error', f'Scan failed after {self.max_retries} attempts'
                    
        return 'error', 'Maximum retries exceeded'
    
    async def _scan_with_instream(self, file_content: bytes, 
                                  progress_callback=None) -> Tuple[str, str]:

        reader = None
        writer = None
        
        try:
            reader, writer = await asyncio.wait_for(
                asyncio.open_connection(self.host, self.port),
                timeout=10
            )
            
            logger.info(f"Connected to ClamAV at {self.host}:{self.port}")

            writer.write(b'zINSTREAM\0')
            await writer.drain()
            
            logger.info(f"INSTREAM command sent, starting to send file data ({len(file_content)} bytes)")

            total_size = len(file_content)
            sent = 0
            
            for i in range(0, total_size, self.chunk_size):
                chunk = file_content[i:i + self.chunk_size]
                chunk_size = len(chunk)

                size_header = struct.pack('>I', chunk_size)

                writer.write(size_header)
                writer.write(chunk)
                
                sent += chunk_size

                if progress_callback:
                    progress = (sent / total_size) * 100
                    await progress_callback(
                        progress, 
                        f"スキャン中: {sent:,}/{total_size:,} bytes ({progress:.1f}%)"
                    )

                if sent % (self.chunk_size * 10) == 0:
                    await writer.drain()

            await writer.drain()

            writer.write(struct.pack('>I', 0))
            await writer.drain()
            
            logger.info("All data sent, waiting for scan result...")

            response_data = b''
            while True:
                try:
                    chunk = await asyncio.wait_for(
                        reader.read(1024),
                        timeout=30
                    )
                    if not chunk:
                        break
                    response_data += chunk
                    if b'\0' in response_data:
                        break
                except asyncio.TimeoutError:
                    if response_data:
                        break
                    raise
            
            response_str = response_data.decode('utf-8', errors='ignore').strip('\0').strip()
            logger.info(f"ClamAV response: {response_str}")
            
            if 'OK' in response_str:
                return 'clean', 'No threats detected'
            elif 'FOUND' in response_str:
                virus_name = response_str.replace('stream: ', '').replace(' FOUND', '').strip()
                logger.warning(f"ClamAV detected virus: {virus_name}")
                return 'infected', virus_name
            elif 'ERROR' in response_str:
                error_msg = response_str.replace('stream: ', '').replace(' ERROR', '').strip()
                logger.error(f"ClamAV error: {error_msg}")
                return 'error', error_msg
            else:
                logger.error(f"Unexpected ClamAV response: {response_str}")
                return 'error', f'Unexpected response: {response_str}'
                
        except asyncio.TimeoutError:
            logger.error(f"ClamAV scan timeout after {self.timeout} seconds")
            return 'error', 'Scan timeout'
        except ConnectionRefusedError:
            logger.error(f"Cannot connect to ClamAV at {self.host}:{self.port}")
            return 'error', 'ClamAV service unavailable'
        except BrokenPipeError:
            logger.error("Connection to ClamAV was lost (broken pipe)")
            return 'error', 'Connection lost during scan'
        except Exception as e:
            logger.error(f"ClamAV scan error: {type(e).__name__}: {e}")
            return 'error', str(e)
        finally:
            if writer:
                try:
                    writer.close()
                    await writer.wait_closed()
                except:
                    pass
    
    async def ping(self) -> bool:
        try:
            reader, writer = await asyncio.wait_for(
                asyncio.open_connection(self.host, self.port),
                timeout=5
            )
            
            writer.write(b'zPING\0')
            await writer.drain()
            
            response = await asyncio.wait_for(
                reader.read(1024),
                timeout=5
            )
            
            writer.close()
            await writer.wait_closed()
            
            return b'PONG' in response
            
        except Exception as e:
            logger.error(f"ClamAV ping failed: {e}")
            return False
    
    async def get_version(self) -> Optional[str]:
        try:
            reader, writer = await asyncio.wait_for(
                asyncio.open_connection(self.host, self.port),
                timeout=5
            )
            
            writer.write(b'zVERSION\0')
            await writer.drain()
            
            response = await asyncio.wait_for(
                reader.read(1024),
                timeout=5
            )
            
            writer.close()
            await writer.wait_closed()
            
            version_info = response.decode('utf-8', errors='ignore').strip()
            logger.info(f"ClamAV version: {version_info}")
            return version_info
            
        except Exception as e:
            logger.error(f"Failed to get ClamAV version: {e}")
            return None
    
    async def test_configuration(self) -> Dict[str, any]:
        result = {
            "ping": False,
            "version": None,
            "status": "unknown"
        }
        
        try:
            result["ping"] = await self.ping()
            
            if result["ping"]:
                result["version"] = await self.get_version()
                result["status"] = "healthy"
            else:
                result["status"] = "unreachable"
                
        except Exception as e:
            logger.error(f"ClamAV configuration test failed: {e}")
            result["status"] = "error"
            result["error"] = str(e)
        
        return result