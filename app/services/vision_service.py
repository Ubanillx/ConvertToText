"""
多模态视觉服务模块
支持Qwen-VL等视觉语言模型的图片理解功能
"""

import os
import base64
import logging
from typing import List, Dict, Any, Optional, Union
from PIL import Image
from io import BytesIO
import dashscope
from dashscope import MultiModalConversation
from pydantic import BaseModel, Field
from app.core.config import settings

# 配置日志
logger = logging.getLogger(__name__)


class VisionService:
    """多模态视觉服务"""
    
    def __init__(self):
        """初始化视觉服务"""
        self.api_key = settings.dashscope_api_key
        if self.api_key:
            dashscope.api_key = self.api_key
        else:
            logger.warning("未设置百炼平台API密钥，无法使用Qwen-VL功能")
        
        # 支持的模型列表
        self.supported_models = {
            "qwen-vl-plus": "qwen-vl-plus",
            "qwen-vl-max": "qwen-vl-max", 
            "qwen-vl": "qwen-vl"
        }
        
        # 默认模型
        self.default_model = "qwen-vl-plus"
    
    def _encode_image_to_base64(self, image: Union[str, Image.Image, bytes]) -> str:
        """
        将图像编码为base64字符串
        
        Args:
            image: 图像（文件路径、PIL图像或字节数据）
            
        Returns:
            base64编码的图像字符串
        """
        try:
            if isinstance(image, str):
                # 文件路径
                with open(image, 'rb') as f:
                    image_data = f.read()
            elif isinstance(image, Image.Image):
                # PIL图像
                buffer = BytesIO()
                image.save(buffer, format='PNG')
                image_data = buffer.getvalue()
            elif isinstance(image, bytes):
                # 字节数据
                image_data = image
            else:
                raise ValueError(f"不支持的图像类型: {type(image)}")
            
            # 编码为base64
            base64_string = base64.b64encode(image_data).decode('utf-8')
            return f"data:image/png;base64,{base64_string}"
            
        except Exception as e:
            logger.error(f"图像编码失败: {str(e)}")
            raise Exception(f"图像编码失败: {str(e)}")
    
    def _preprocess_image(self, image: Union[str, Image.Image, bytes]) -> Image.Image:
        """
        预处理图像，优化识别效果
        
        Args:
            image: 输入图像
            
        Returns:
            预处理后的PIL图像
        """
        try:
            if isinstance(image, str):
                # 文件路径
                img = Image.open(image)
            elif isinstance(image, Image.Image):
                # PIL图像
                img = image.copy()
            elif isinstance(image, bytes):
                # 字节数据
                img = Image.open(BytesIO(image))
            else:
                raise ValueError(f"不支持的图像类型: {type(image)}")
            
            # 转换为RGB模式（如果不是的话）
            if img.mode != 'RGB':
                img = img.convert('RGB')
            
            # 调整图像大小（如果太大）
            max_size = 2048
            if max(img.size) > max_size:
                ratio = max_size / max(img.size)
                new_size = (int(img.size[0] * ratio), int(img.size[1] * ratio))
                img = img.resize(new_size, Image.Resampling.LANCZOS)
            
            return img
            
        except Exception as e:
            logger.error(f"图像预处理失败: {str(e)}")
            raise Exception(f"图像预处理失败: {str(e)}")
    
    def extract_text_from_image(
        self, 
        image: Union[str, Image.Image, bytes], 
        model: str = None,
        prompt: str = None,
        **kwargs
    ) -> Dict[str, Any]:
        """
        从图像中提取文字内容
        
        Args:
            image: 输入图像
            model: 使用的模型名称
            prompt: 自定义提示词
            **kwargs: 其他参数
            
        Returns:
            提取结果
        """
        try:
            if not self.api_key:
                return {
                    "text": "",
                    "error": "未配置百炼平台API密钥",
                    "success": False
                }
            
            # 使用默认模型
            if not model:
                model = self.default_model
            
            if model not in self.supported_models:
                logger.warning(f"不支持的模型: {model}，使用默认模型: {self.default_model}")
                model = self.default_model
            
            # 预处理图像
            processed_image = self._preprocess_image(image)
            
            # 编码图像
            image_base64 = self._encode_image_to_base64(processed_image)
            
            # 默认提示词
            if not prompt:
                prompt = """请仔细观察这张图片，提取其中所有可见的文字内容。
请按照从上到下、从左到右的阅读顺序组织成段落。
如果有表格，请用Markdown格式表示。
注意数字、金额、日期的准确性。
请直接输出提取的文字内容，不要添加额外的解释。"""
            
            # 构建消息
            messages = [
                {
                    "role": "user",
                    "content": [
                        {"image": image_base64},
                        {"text": prompt}
                    ]
                }
            ]
            
            # 调用Qwen-VL API
            response = MultiModalConversation.call(
                model=model,
                messages=messages,
                **kwargs
            )
            
            if response.status_code == 200:
                content = response.output.choices[0].message.content
                
                # 处理content可能是列表或字符串的情况
                if isinstance(content, list):
                    # 如果是列表，提取文本内容
                    result_text = ""
                    for item in content:
                        if isinstance(item, dict) and 'text' in item:
                            result_text += item['text']
                        elif isinstance(item, str):
                            result_text += item
                else:
                    result_text = str(content)
                
                return {
                    "text": result_text,
                    "model": model,
                    "success": True,
                    "confidence": 1.0,  # Qwen-VL不提供置信度，设为1.0
                    "image_size": processed_image.size,
                    "processing_info": {
                        "model_used": model,
                        "image_processed": True,
                        "base64_length": len(image_base64)
                    }
                }
            else:
                error_msg = f"API调用失败: {response.message}"
                logger.error(error_msg)
                return {
                    "text": "",
                    "error": error_msg,
                    "success": False
                }
                
        except Exception as e:
            error_msg = f"图像文字提取失败: {str(e)}"
            logger.error(error_msg)
            return {
                "text": "",
                "error": error_msg,
                "success": False
            }
    
    
    
    
    
    
    def is_available(self) -> bool:
        """检查服务是否可用"""
        try:
            if not self.api_key or len(self.api_key.strip()) == 0:
                logger.warning("Qwen-VL API密钥未配置")
                return False
            
            # 可以添加一个简单的测试调用
            logger.info("Qwen-VL服务可用性检查通过")
            return True
            
        except Exception as e:
            logger.error(f"Qwen-VL服务可用性检查失败: {str(e)}")
            return False


# 创建全局实例
vision_service = VisionService()
