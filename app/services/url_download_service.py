"""
URL下载服务
用于从URL下载文件并处理
"""

import logging
import aiohttp
import aiofiles
import tempfile
import os
from typing import Dict, Any, Optional, Tuple
from pathlib import Path
from urllib.parse import urlparse
import mimetypes

logger = logging.getLogger(__name__)


class URLDownloadService:
    """URL下载服务"""
    
    def __init__(self):
        self.max_file_size = 50 * 1024 * 1024  # 50MB
        self.timeout = 30  # 30秒超时
        self.allowed_schemes = ['http', 'https']
    
    async def download_file_from_url(
        self, 
        url: str, 
        task_id: str
    ) -> Dict[str, Any]:
        """
        从URL下载文件
        
        Args:
            url: 文件URL
            task_id: 任务ID
            
        Returns:
            包含文件信息的字典
        """
        try:
            # 验证URL
            parsed_url = urlparse(url)
            if parsed_url.scheme not in self.allowed_schemes:
                raise ValueError(f"不支持的URL协议: {parsed_url.scheme}")
            
            # 创建临时文件
            temp_file = tempfile.NamedTemporaryFile(delete=False)
            temp_file_path = temp_file.name
            temp_file.close()
            
            # 下载文件
            async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=self.timeout)) as session:
                async with session.get(url) as response:
                    if response.status != 200:
                        raise ValueError(f"下载失败，HTTP状态码: {response.status}")
                    
                    # 检查文件大小
                    content_length = response.headers.get('content-length')
                    if content_length and int(content_length) > self.max_file_size:
                        raise ValueError(f"文件过大，最大支持: {self.max_file_size / 1024 / 1024:.1f}MB")
                    
                    # 下载文件内容
                    file_content = b''
                    async for chunk in response.content.iter_chunked(8192):
                        file_content += chunk
                        if len(file_content) > self.max_file_size:
                            raise ValueError(f"文件过大，最大支持: {self.max_file_size / 1024 / 1024:.1f}MB")
                    
                    # 保存到临时文件
                    async with aiofiles.open(temp_file_path, 'wb') as f:
                        await f.write(file_content)
            
            # 获取文件名和类型
            filename = self._extract_filename_from_url(url, response.headers)
            file_type = self._detect_file_type(filename, file_content)
            
            return {
                'file_path': temp_file_path,
                'filename': filename,
                'file_type': file_type,
                'file_size': len(file_content),
                'content_type': response.headers.get('content-type', ''),
                'source': 'url',
                'original_url': url
            }
            
        except Exception as e:
            # 清理临时文件
            if 'temp_file_path' in locals() and os.path.exists(temp_file_path):
                os.unlink(temp_file_path)
            logger.error(f"从URL下载文件失败: {str(e)}")
            raise
    
    def _extract_filename_from_url(self, url: str, headers: Dict[str, str]) -> str:
        """从URL或响应头中提取文件名"""
        # 尝试从Content-Disposition头获取文件名
        content_disposition = headers.get('content-disposition', '')
        if 'filename=' in content_disposition:
            try:
                filename = content_disposition.split('filename=')[1].strip('"\'')
                return filename
            except:
                pass
        
        # 从URL路径中提取文件名
        parsed_url = urlparse(url)
        path = parsed_url.path
        if path and '/' in path:
            filename = path.split('/')[-1]
            if filename and '.' in filename:
                return filename
        
        # 根据Content-Type生成默认文件名
        content_type = headers.get('content-type', '')
        if 'pdf' in content_type:
            return 'document.pdf'
        elif 'image' in content_type:
            return 'image.jpg'
        elif 'msword' in content_type or 'officedocument' in content_type:
            return 'document.docx'
        else:
            return 'download_file'
    
    def _detect_file_type(self, filename: str, file_content: bytes) -> str:
        """检测文件类型"""
        # 根据文件扩展名判断
        file_ext = Path(filename).suffix.lower()
        
        if file_ext == '.pdf':
            return 'pdf'
        elif file_ext in ['.doc', '.docx']:
            return 'doc' if file_ext == '.doc' else 'docx'
        elif file_ext in ['.jpg', '.jpeg', '.png', '.bmp', '.tiff', '.webp', '.gif']:
            return 'image'
        elif file_ext in ['.txt', '.md']:
            return 'text'
        
        # 根据文件内容判断（检查文件头）
        if file_content.startswith(b'%PDF'):
            return 'pdf'
        elif file_content.startswith(b'PK\x03\x04'):  # ZIP格式（DOCX是ZIP格式）
            # 进一步检查是否为DOCX
            if b'word/' in file_content[:1024]:
                return 'docx'
            else:
                return 'unknown'
        elif file_content.startswith(b'\xd0\xcf\x11\xe0'):  # DOC格式
            return 'doc'
        elif file_content.startswith((b'\xff\xd8\xff', b'\x89PNG', b'GIF8')):
            return 'image'
        
        return 'unknown'


# 创建全局实例
url_download_service = URLDownloadService()
