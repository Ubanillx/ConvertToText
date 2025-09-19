"""
统一处理服务
整合所有业务逻辑，提供统一的处理接口
"""

import logging
import asyncio
from typing import Dict, Any, Optional, List, Union
from datetime import datetime
import json

from app.services.file_storage_service import file_storage_service
from app.services.pdf_extractor import pdf_extractor
from app.services.doc_extractor import doc_extractor
from app.services.image_processing_service import image_processing_service
from app.services.url_download_service import url_download_service
from app.core.config import settings

logger = logging.getLogger(__name__)


class UnifiedProcessingService:
    """统一处理服务"""
    
    def __init__(self):
        self.file_storage = file_storage_service
        self.pdf_processor = pdf_extractor
        self.doc_processor = doc_extractor
        self.image_processor = image_processing_service
        self.url_downloader = url_download_service
    
    async def process_file_upload(
        self,
        file_content: bytes,
        filename: str,
        processing_type: str = "extract",
        output_format: str = "json",
        **kwargs
    ) -> Dict[str, Any]:
        """
        处理文件上传
        
        Args:
            file_content: 文件内容
            filename: 文件名
            processing_type: 处理类型 (仅支持extract)
            output_format: 输出格式 (json, txt, zip)
            **kwargs: 其他参数
            
        Returns:
            处理结果，包含下载URL
        """
        try:
            # 生成任务ID
            task_id = self.file_storage.generate_task_id()
            
            # 保存上传文件
            file_info = self.file_storage.save_uploaded_file(file_content, filename, task_id)
            
            # 根据文件类型选择处理方式
            file_type = file_info['file_type']
            
            if file_type == 'pdf':
                result = await self._process_pdf_file(file_info, processing_type, **kwargs)
            elif file_type in ['doc', 'docx']:
                result = await self._process_doc_file(file_info, processing_type, **kwargs)
            elif file_type == 'image':
                result = await self._process_image_file(file_info, processing_type, **kwargs)
            elif file_type == 'text':
                result = await self._process_text_file(file_info, processing_type, **kwargs)
            else:
                raise ValueError(f"不支持的文件类型: {file_type}")
            
            # 保存处理结果并生成下载URL
            download_url = self.file_storage.save_processing_result(
                task_id, result, output_format
            )
            
            # 返回统一格式的结果
            return {
                'success': True,
                'task_id': task_id,
                'file_info': file_info,
                'processing_type': processing_type,
                'result': result,
                'download_url': download_url,
                'created_at': datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"处理文件上传失败: {str(e)}")
            return {
                'success': False,
                'error': str(e),
                'created_at': datetime.now().isoformat()
            }
    
    async def process_url_upload(
        self,
        url: str,
        processing_type: str = "extract",
        output_format: str = "json",
        **kwargs
    ) -> Dict[str, Any]:
        """
        处理URL文件上传
        
        Args:
            url: 文件URL
            processing_type: 处理类型 (仅支持extract)
            output_format: 输出格式 (json, txt, zip)
            **kwargs: 其他参数
            
        Returns:
            处理结果，包含下载URL
        """
        try:
            # 生成任务ID
            task_id = self.file_storage.generate_task_id()
            
            # 从URL下载文件
            file_info = await self.url_downloader.download_file_from_url(url, task_id)
            
            # 根据文件类型选择处理方式
            file_type = file_info['file_type']
            
            if file_type == 'pdf':
                result = await self._process_pdf_file(file_info, processing_type, **kwargs)
            elif file_type in ['doc', 'docx']:
                result = await self._process_doc_file(file_info, processing_type, **kwargs)
            elif file_type == 'image':
                result = await self._process_image_file(file_info, processing_type, **kwargs)
            elif file_type == 'text':
                result = await self._process_text_file(file_info, processing_type, **kwargs)
            else:
                raise ValueError(f"不支持的文件类型: {file_type}")
            
            # 保存处理结果并生成下载URL
            download_url = self.file_storage.save_processing_result(
                task_id, result, output_format
            )
            
            # 返回统一格式的结果
            return {
                'success': True,
                'task_id': task_id,
                'file_info': file_info,
                'processing_type': processing_type,
                'result': result,
                'download_url': download_url,
                'created_at': datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"处理URL文件上传失败: {str(e)}")
            return {
                'success': False,
                'error': str(e),
                'created_at': datetime.now().isoformat()
            }
    
    
    async def _process_pdf_file(
        self,
        file_info: Dict[str, Any],
        processing_type: str,
        **kwargs
    ) -> Dict[str, Any]:
        """处理PDF文件"""
        try:
            file_path = file_info['file_path']
            
            if processing_type == "extract":
                # 提取文本
                result = await self.pdf_processor.extract_text_from_pdf_async(file_path, **kwargs)
            else:
                raise ValueError(f"不支持的PDF处理类型: {processing_type}")
            
            return result
            
        except Exception as e:
            logger.error(f"处理PDF文件失败: {str(e)}")
            raise
    
    async def _process_doc_file(
        self,
        file_info: Dict[str, Any],
        processing_type: str,
        **kwargs
    ) -> Dict[str, Any]:
        """处理DOC/DOCX文件"""
        try:
            file_path = file_info['file_path']
            
            if processing_type == "extract":
                # 提取文本
                result = await self.doc_processor.extract_text_from_doc_async(file_path, **kwargs)
            else:
                raise ValueError(f"不支持的DOC处理类型: {processing_type}")
            
            return result
            
        except Exception as e:
            logger.error(f"处理DOC文件失败: {str(e)}")
            raise
    
    async def _process_image_file(
        self,
        file_info: Dict[str, Any],
        processing_type: str,
        **kwargs
    ) -> Dict[str, Any]:
        """处理图片文件"""
        try:
            file_path = file_info['file_path']
            
            if processing_type == "extract":
                # OCR提取文本
                result = await self.image_processor.extract_text_from_image(file_path)
            else:
                raise ValueError(f"不支持的图片处理类型: {processing_type}")
            
            return result
            
        except Exception as e:
            logger.error(f"处理图片文件失败: {str(e)}")
            raise
    
    async def _process_text_file(
        self,
        file_info: Dict[str, Any],
        processing_type: str,
        **kwargs
    ) -> Dict[str, Any]:
        """处理文本文件"""
        try:
            file_path = file_info['file_path']
            
            # 读取文本内容
            with open(file_path, 'r', encoding='utf-8') as f:
                text_content = f.read()
            
            if processing_type == "extract":
                # 直接返回文本内容
                result = {'extracted_text': text_content}
            else:
                raise ValueError(f"不支持的文本处理类型: {processing_type}")
            
            return result
            
        except Exception as e:
            logger.error(f"处理文本文件失败: {str(e)}")
            raise
    
    


# 创建全局实例
unified_processing_service = UnifiedProcessingService()
