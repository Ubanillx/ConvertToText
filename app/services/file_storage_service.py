"""
文件存储服务
处理文件上传、存储和下载URL生成
"""

import os
import uuid
import shutil
import tempfile
import mimetypes
from pathlib import Path
from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta
import logging
from urllib.parse import urljoin
import json
import zipfile

from app.core.config import settings

logger = logging.getLogger(__name__)


class FileStorageService:
    """文件存储服务"""
    
    def __init__(self):
        self.base_storage_path = Path(settings.storage_path) if hasattr(settings, 'storage_path') else Path("./storage")
        self.base_download_url = getattr(settings, 'download_base_url', 'http://localhost:8000/api/v1/download')
        self.max_file_size = getattr(settings, 'max_file_size', 100 * 1024 * 1024)  # 100MB
        self.allowed_extensions = {
            'pdf': ['.pdf'],
            'doc': ['.doc'],
            'docx': ['.docx'],
            'image': ['.jpg', '.jpeg', '.png', '.bmp', '.tiff', '.webp', '.gif'],
            'text': ['.txt', '.md'],
            'document': ['.pdf', '.doc', '.docx', '.txt', '.md']
        }
        
        # 确保存储目录存在
        self.base_storage_path.mkdir(parents=True, exist_ok=True)
        (self.base_storage_path / "uploads").mkdir(exist_ok=True)
        (self.base_storage_path / "results").mkdir(exist_ok=True)
        (self.base_storage_path / "temp").mkdir(exist_ok=True)
    
    def generate_task_id(self) -> str:
        """生成任务ID"""
        return str(uuid.uuid4())
    
    def generate_file_id(self) -> str:
        """生成文件ID"""
        return str(uuid.uuid4())
    
    def get_file_type(self, filename: str) -> str:
        """获取文件类型"""
        extension = Path(filename).suffix.lower()
        
        for file_type, extensions in self.allowed_extensions.items():
            if extension in extensions:
                return file_type
        
        return 'unknown'
    
    def validate_file(self, file_content: bytes, filename: str) -> Dict[str, Any]:
        """验证文件"""
        file_size = len(file_content)
        
        if file_size > self.max_file_size:
            raise ValueError(f"文件大小超过限制: {file_size} > {self.max_file_size}")
        
        file_type = self.get_file_type(filename)
        if file_type == 'unknown':
            raise ValueError(f"不支持的文件类型: {filename}")
        
        return {
            'size': file_size,
            'type': file_type,
            'extension': Path(filename).suffix.lower(),
            'mime_type': mimetypes.guess_type(filename)[0]
        }
    
    def save_uploaded_file(self, file_content: bytes, filename: str, task_id: str) -> Dict[str, Any]:
        """保存上传的文件"""
        try:
            # 验证文件
            file_info = self.validate_file(file_content, filename)
            
            # 生成文件ID
            file_id = self.generate_file_id()
            
            # 创建任务目录
            task_dir = self.base_storage_path / "uploads" / task_id
            task_dir.mkdir(parents=True, exist_ok=True)
            
            # 保存文件
            file_path = task_dir / f"{file_id}_{filename}"
            with open(file_path, 'wb') as f:
                f.write(file_content)
            
            # 返回文件信息
            return {
                'file_id': file_id,
                'task_id': task_id,
                'original_filename': filename,
                'file_path': str(file_path),
                'file_size': file_info['size'],
                'file_type': file_info['type'],
                'extension': file_info['extension'],
                'mime_type': file_info['mime_type'],
                'created_at': datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"保存上传文件失败: {str(e)}")
            raise
    
    def save_processing_result(self, task_id: str, result_data: Dict[str, Any], 
                             output_format: str = "json") -> str:
        """保存处理结果并返回下载URL"""
        try:
            # 创建结果目录
            result_dir = self.base_storage_path / "results" / task_id
            result_dir.mkdir(parents=True, exist_ok=True)
            
            # 生成结果文件名
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            
            if output_format == "json":
                filename = f"result_{timestamp}.json"
                file_path = result_dir / filename
                
                # 清理result_data中的bytes数据，确保JSON序列化兼容
                cleaned_data = self._clean_data_for_json(result_data)
                
                with open(file_path, 'w', encoding='utf-8') as f:
                    json.dump(cleaned_data, f, ensure_ascii=False, indent=2)
            
            elif output_format == "txt":
                filename = f"result_{timestamp}.txt"
                file_path = result_dir / filename
                
                # 提取纯文本内容
                text_content = ""
                if 'full_text' in result_data:
                    # PDF提取结果
                    text_content = result_data['full_text']
                elif 'extracted_text' in result_data:
                    # 其他类型的提取结果
                    text_content = result_data['extracted_text']
                elif 'text' in result_data:
                    # 简单文本结果
                    text_content = result_data['text']
                else:
                    # 尝试从pages中提取文本
                    if 'pages' in result_data and isinstance(result_data['pages'], list):
                        page_texts = []
                        for page in result_data['pages']:
                            if isinstance(page, dict):
                                if 'text' in page:
                                    page_texts.append(page['text'])
                                elif 'full_text' in page:
                                    page_texts.append(page['full_text'])
                        text_content = "\n\n".join(page_texts)
                
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(text_content)
            
            elif output_format == "zip":
                filename = f"result_{timestamp}.zip"
                file_path = result_dir / filename
                
                with zipfile.ZipFile(file_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                    # 添加JSON结果
                    cleaned_data = self._clean_data_for_json(result_data)
                    zipf.writestr("result.json", json.dumps(cleaned_data, ensure_ascii=False, indent=2))
                    
                    # 添加文本结果
                    if 'extracted_text' in result_data:
                        zipf.writestr("extracted_text.txt", result_data['extracted_text'])
                    
                    # 添加其他文件
                    if 'additional_files' in result_data:
                        for file_info in result_data['additional_files']:
                            if os.path.exists(file_info['path']):
                                zipf.write(file_info['path'], file_info['name'])
            
            else:
                raise ValueError(f"不支持的输出格式: {output_format}")
            
            # 生成下载URL
            download_url = f"{self.base_download_url}/{task_id}/{filename}"
            
            logger.info(f"处理结果已保存: {file_path}, 下载URL: {download_url}")
            
            return download_url
            
        except Exception as e:
            logger.error(f"保存处理结果失败: {str(e)}")
            raise
    
    def _clean_data_for_json(self, data: Any) -> Any:
        """
        清理数据中的bytes对象，确保JSON序列化兼容
        
        Args:
            data: 需要清理的数据
            
        Returns:
            清理后的数据
        """
        try:
            if isinstance(data, bytes):
                # 将bytes数据转换为基本信息
                return {
                    "type": "bytes",
                    "size": len(data),
                    "note": "原始bytes数据已移除以确保JSON序列化兼容性"
                }
            elif isinstance(data, dict):
                # 递归清理字典
                cleaned_dict = {}
                for key, value in data.items():
                    cleaned_dict[key] = self._clean_data_for_json(value)
                return cleaned_dict
            elif isinstance(data, list):
                # 递归清理列表
                return [self._clean_data_for_json(item) for item in data]
            elif isinstance(data, tuple):
                # 递归清理元组
                return tuple(self._clean_data_for_json(item) for item in data)
            else:
                # 其他类型直接返回
                return data
                
        except Exception as e:
            logger.error(f"清理数据失败: {str(e)}")
            return {"error": f"清理失败: {str(e)}"}
    
    
    
    


# 创建全局实例
file_storage_service = FileStorageService()
