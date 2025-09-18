"""
图片处理服务
封装图片文字提取功能
"""

import logging
from typing import Dict, Any
from app.services.tesseract_ocr_service import tesseract_ocr_service
from app.services.baidu_ocr_service import baidu_ocr_service
from app.schemas.ocr_schemas import OCREngineType
from app.services.vision_service import vision_service

logger = logging.getLogger(__name__)


class ImageProcessingService:
    """图片处理服务"""
    
    def __init__(self):
        self.vision_service = vision_service
    
    async def extract_text_from_image(self, file_path: str, **kwargs) -> Dict[str, Any]:
        """
        从图片文件提取文字
        
        Args:
            file_path: 图片文件路径
            **kwargs: 其他参数 (ocr_engine, use_vision, vision_model)
            
        Returns:
            提取结果
        """
        try:
            # 提取参数
            ocr_engine = kwargs.get('ocr_engine', 'baidu')
            use_vision = kwargs.get('use_vision', False)
            vision_model = kwargs.get('vision_model', 'qwen-vl-plus')
            
            # 转换OCR引擎类型
            try:
                ocr_engine_enum = OCREngineType(ocr_engine.lower())
            except ValueError:
                ocr_engine_enum = OCREngineType.BAIDU
            
            # 使用OCR提取文字
            if ocr_engine_enum == OCREngineType.TESSERACT:
                ocr_result = tesseract_ocr_service.extract_text(file_path)
            elif ocr_engine_enum == OCREngineType.BAIDU:
                ocr_result = baidu_ocr_service.extract_text(file_path)
            else:
                raise ValueError(f"不支持的OCR引擎: {ocr_engine_enum}")
            
            # 如果启用视觉模型，也使用Qwen-VL处理
            vision_result = None
            if use_vision and self.vision_service.is_available():
                try:
                    vision_result = self.vision_service.extract_text_from_image(
                        file_path, model=vision_model
                    )
                except Exception as e:
                    logger.warning(f"Qwen-VL处理失败: {str(e)}")
            
            # 合并结果
            result = {
                'extracted_text': ocr_result.get('text', ''),
                'ocr_result': ocr_result,
                'vision_result': vision_result,
                'success': ocr_result.get('success', True)
            }
            
            # 如果有视觉模型结果，优先使用
            if vision_result and vision_result.get('success'):
                result['extracted_text'] = vision_result.get('text', result['extracted_text'])
                result['processing_method'] = 'vision'
            else:
                result['processing_method'] = 'ocr'
            
            return result
            
        except Exception as e:
            logger.error(f"图片文字提取失败: {str(e)}")
            raise


# 创建全局实例
image_processing_service = ImageProcessingService()
