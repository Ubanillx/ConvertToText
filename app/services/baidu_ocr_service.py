"""
百度OCR文字识别服务模块

支持百度AI平台的多种OCR识别功能：
1. 通用文字识别（标准版、高精度版）
2. 办公文档识别
3. 表格文字识别
4. 手写文字识别
5. 网络图片文字识别
6. 各种证件识别
7. 财务票据识别
"""

import sys
import os
import logging
from typing import List, Dict, Any, Optional, Union
from pathlib import Path
import base64
from PIL import Image
import io
import time
from threading import Lock

# 添加百度SDK路径
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'sdk', 'aip-python-sdk-4.16.14'))

try:
    from aip import AipOcr
except ImportError as e:
    logging.error(f"无法导入百度OCR SDK: {e}")
    AipOcr = None

from ..core.config import settings

logger = logging.getLogger(__name__)


class BaiduOCRService:
    """百度OCR文字识别服务"""
    
    def __init__(self):
        """初始化百度OCR服务"""
        self.api_key = settings.baidu_ocr_api_key
        self.secret_key = settings.baidu_ocr_secret_key
        self.app_id = "ConvertToText"  # 使用应用名称作为App ID
        self.client = None
        
        # QPS控制相关
        self._last_request_time = 0
        self._request_lock = Lock()
        self._min_interval = 0.2  # 最小请求间隔200ms，即最大5QPS
        
        if AipOcr is None:
            logger.error("百度OCR SDK未正确安装")
            return
            
        try:
            # 初始化百度OCR客户端
            self.client = AipOcr(self.app_id, self.api_key, self.secret_key)
            logger.info("百度OCR服务初始化成功")
        except Exception as e:
            logger.error(f"百度OCR服务初始化失败: {e}")
            self.client = None
    
    def _image_to_bytes(self, image: Union[str, bytes, Image.Image]) -> bytes:
        """
        将图片转换为字节数据
        
        Args:
            image: 图片路径、字节数据或PIL图片对象
            
        Returns:
            图片字节数据
        """
        try:
            if isinstance(image, str):
                # 文件路径
                with open(image, 'rb') as f:
                    image_data = f.read()
            elif isinstance(image, bytes):
                # 字节数据
                image_data = image
            elif isinstance(image, Image.Image):
                # PIL图片对象
                buffer = io.BytesIO()
                image.save(buffer, format='PNG')
                image_data = buffer.getvalue()
            else:
                raise ValueError(f"不支持的图片类型: {type(image)}")
            
            return image_data
            
        except Exception as e:
            logger.error(f"图片转换为字节数据失败: {e}")
            raise
    
    def _rate_limit_control(self):
        """
        QPS限制控制，确保请求频率不超过限制
        """
        with self._request_lock:
            current_time = time.time()
            time_since_last_request = current_time - self._last_request_time
            
            if time_since_last_request < self._min_interval:
                sleep_time = self._min_interval - time_since_last_request
                logger.debug(f"QPS限制控制: 等待 {sleep_time:.3f} 秒")
                time.sleep(sleep_time)
            
            self._last_request_time = time.time()
    
    def _parse_baidu_result(self, result: Dict[str, Any], engine_type: str = "baidu") -> Dict[str, Any]:
        """
        解析百度OCR返回结果
        
        Args:
            result: 百度OCR API返回结果
            engine_type: 引擎类型
            
        Returns:
            标准化的识别结果
        """
        try:
            if 'error_code' in result:
                return {
                    'engine': engine_type,
                    'text': '',
                    'words': [],
                    'total_words': 0,
                    'average_confidence': 0,
                    'success': False,
                    'error': f"百度OCR错误 {result['error_code']}: {result.get('error_msg', '未知错误')}"
                }
            
            words = []
            text_parts = []
            
            # 解析文字结果
            if 'words_result' in result:
                for item in result['words_result']:
                    if isinstance(item, dict):
                        word_text = item.get('words', '')
                        confidence = item.get('probability', {}).get('average', 0.0)
                        
                        # 获取位置信息
                        location = item.get('location', {})
                        bbox = [
                            location.get('left', 0),
                            location.get('top', 0),
                            location.get('left', 0) + location.get('width', 0),
                            location.get('top', 0) + location.get('height', 0)
                        ]
                        
                        words.append({
                            'text': word_text,
                            'confidence': confidence,
                            'bbox': bbox
                        })
                        text_parts.append(word_text)
            
            # 合并文本
            full_text = '\n'.join(text_parts)
            
            # 计算平均置信度
            confidences = [w['confidence'] for w in words if w['confidence'] > 0]
            avg_confidence = sum(confidences) / len(confidences) if confidences else 0.0
            
            return {
                'engine': engine_type,
                'text': full_text,
                'words': words,
                'total_words': len(words),
                'average_confidence': avg_confidence,
                'success': len(full_text.strip()) > 0,
                'raw_result': result
            }
            
        except Exception as e:
            logger.error(f"解析百度OCR结果失败: {e}")
            return {
                'engine': engine_type,
                'text': '',
                'words': [],
                'total_words': 0,
                'average_confidence': 0,
                'success': False,
                'error': str(e)
            }
    
    def basic_general(self, image: Union[str, bytes, Image.Image], 
                     options: Optional[Dict] = None) -> Dict[str, Any]:
        """
        通用文字识别（标准版）
        
        Args:
            image: 输入图片
            options: 可选参数
            
        Returns:
            识别结果字典
        """
        if not self.client:
            return {
                'engine': 'baidu',
                'text': '',
                'words': [],
                'total_words': 0,
                'average_confidence': 0,
                'success': False,
                'error': '百度OCR客户端未初始化'
            }
        
        try:
            # 转换图片为字节数据
            image_data = self._image_to_bytes(image)
            
            # QPS限制控制
            self._rate_limit_control()
            
            # 调用百度OCR API
            result = self.client.basicGeneral(image_data, options or {})
            
            return self._parse_baidu_result(result, "baidu_basic_general")
            
        except Exception as e:
            logger.error(f"百度通用文字识别失败: {e}")
            return {
                'engine': 'baidu_basic_general',
                'text': '',
                'words': [],
                'total_words': 0,
                'average_confidence': 0,
                'success': False,
                'error': str(e)
            }
    
    def basic_accurate(self, image: Union[str, bytes, Image.Image], 
                      options: Optional[Dict] = None) -> Dict[str, Any]:
        """
        通用文字识别（高精度版）
        
        Args:
            image: 输入图片
            options: 可选参数
            
        Returns:
            识别结果字典
        """
        if not self.client:
            return {
                'engine': 'baidu',
                'text': '',
                'words': [],
                'total_words': 0,
                'average_confidence': 0,
                'success': False,
                'error': '百度OCR客户端未初始化'
            }
        
        try:
            # 转换图片为字节数据
            image_data = self._image_to_bytes(image)
            
            # QPS限制控制
            self._rate_limit_control()
            
            # 调用百度OCR API
            result = self.client.basicAccurate(image_data, options or {})
            
            return self._parse_baidu_result(result, "baidu_basic_accurate")
            
        except Exception as e:
            logger.error(f"百度高精度文字识别失败: {e}")
            return {
                'engine': 'baidu_basic_accurate',
                'text': '',
                'words': [],
                'total_words': 0,
                'average_confidence': 0,
                'success': False,
                'error': str(e)
            }
    
    def general_with_location(self, image: Union[str, bytes, Image.Image], 
                             options: Optional[Dict] = None) -> Dict[str, Any]:
        """
        通用文字识别（标准含位置版）
        
        Args:
            image: 输入图片
            options: 可选参数
            
        Returns:
            识别结果字典
        """
        if not self.client:
            return {
                'engine': 'baidu',
                'text': '',
                'words': [],
                'total_words': 0,
                'average_confidence': 0,
                'success': False,
                'error': '百度OCR客户端未初始化'
            }
        
        try:
            # 转换图片为字节数据
            image_data = self._image_to_bytes(image)
            
            # QPS限制控制
            self._rate_limit_control()
            
            # 调用百度OCR API
            result = self.client.general(image_data, options or {})
            
            return self._parse_baidu_result(result, "baidu_general")
            
        except Exception as e:
            logger.error(f"百度通用文字识别（含位置）失败: {e}")
            return {
                'engine': 'baidu_general',
                'text': '',
                'words': [],
                'total_words': 0,
                'average_confidence': 0,
                'success': False,
                'error': str(e)
            }
    
    def accurate_with_location(self, image: Union[str, bytes, Image.Image], 
                              options: Optional[Dict] = None) -> Dict[str, Any]:
        """
        通用文字识别（高精度含位置版）
        
        Args:
            image: 输入图片
            options: 可选参数
            
        Returns:
            识别结果字典
        """
        if not self.client:
            return {
                'engine': 'baidu',
                'text': '',
                'words': [],
                'total_words': 0,
                'average_confidence': 0,
                'success': False,
                'error': '百度OCR客户端未初始化'
            }
        
        try:
            # 转换图片为字节数据
            image_data = self._image_to_bytes(image)
            
            # QPS限制控制
            self._rate_limit_control()
            
            # 调用百度OCR API
            result = self.client.accurate(image_data, options or {})
            
            return self._parse_baidu_result(result, "baidu_accurate")
            
        except Exception as e:
            logger.error(f"百度高精度文字识别（含位置）失败: {e}")
            return {
                'engine': 'baidu_accurate',
                'text': '',
                'words': [],
                'total_words': 0,
                'average_confidence': 0,
                'success': False,
                'error': str(e)
            }
    
    def doc_analysis_office(self, image: Union[str, bytes, Image.Image], 
                           options: Optional[Dict] = None) -> Dict[str, Any]:
        """
        办公文档识别
        
        Args:
            image: 输入图片
            options: 可选参数
            
        Returns:
            识别结果字典
        """
        if not self.client:
            return {
                'engine': 'baidu',
                'text': '',
                'words': [],
                'total_words': 0,
                'average_confidence': 0,
                'success': False,
                'error': '百度OCR客户端未初始化'
            }
        
        try:
            # 转换图片为字节数据
            image_data = self._image_to_bytes(image)
            
            # QPS限制控制
            self._rate_limit_control()
            
            # 调用百度OCR API
            result = self.client.doc_analysis_office(image_data, options or {})
            
            return self._parse_baidu_result(result, "baidu_doc_office")
            
        except Exception as e:
            logger.error(f"百度办公文档识别失败: {e}")
            return {
                'engine': 'baidu_doc_office',
                'text': '',
                'words': [],
                'total_words': 0,
                'average_confidence': 0,
                'success': False,
                'error': str(e)
            }
    
    def table_recognition(self, image: Union[str, bytes, Image.Image], 
                         options: Optional[Dict] = None) -> Dict[str, Any]:
        """
        表格文字识别
        
        Args:
            image: 输入图片
            options: 可选参数
            
        Returns:
            识别结果字典
        """
        if not self.client:
            return {
                'engine': 'baidu',
                'text': '',
                'words': [],
                'total_words': 0,
                'average_confidence': 0,
                'success': False,
                'error': '百度OCR客户端未初始化'
            }
        
        try:
            # 转换图片为字节数据
            image_data = self._image_to_bytes(image)
            
            # QPS限制控制
            self._rate_limit_control()
            
            # 调用百度OCR API
            result = self.client.table(image_data, options or {})
            
            return self._parse_baidu_result(result, "baidu_table")
            
        except Exception as e:
            logger.error(f"百度表格识别失败: {e}")
            return {
                'engine': 'baidu_table',
                'text': '',
                'words': [],
                'total_words': 0,
                'average_confidence': 0,
                'success': False,
                'error': str(e)
            }
    
    def handwriting_recognition(self, image: Union[str, bytes, Image.Image], 
                               options: Optional[Dict] = None) -> Dict[str, Any]:
        """
        手写文字识别
        
        Args:
            image: 输入图片
            options: 可选参数
            
        Returns:
            识别结果字典
        """
        if not self.client:
            return {
                'engine': 'baidu',
                'text': '',
                'words': [],
                'total_words': 0,
                'average_confidence': 0,
                'success': False,
                'error': '百度OCR客户端未初始化'
            }
        
        try:
            # 转换图片为字节数据
            image_data = self._image_to_bytes(image)
            
            # QPS限制控制
            self._rate_limit_control()
            
            # 调用百度OCR API
            result = self.client.handwriting(image_data, options or {})
            
            return self._parse_baidu_result(result, "baidu_handwriting")
            
        except Exception as e:
            logger.error(f"百度手写文字识别失败: {e}")
            return {
                'engine': 'baidu_handwriting',
                'text': '',
                'words': [],
                'total_words': 0,
                'average_confidence': 0,
                'success': False,
                'error': str(e)
            }
    
    def web_image_recognition(self, image: Union[str, bytes, Image.Image], 
                             options: Optional[Dict] = None) -> Dict[str, Any]:
        """
        网络图片文字识别
        
        Args:
            image: 输入图片
            options: 可选参数
            
        Returns:
            识别结果字典
        """
        if not self.client:
            return {
                'engine': 'baidu',
                'text': '',
                'words': [],
                'total_words': 0,
                'average_confidence': 0,
                'success': False,
                'error': '百度OCR客户端未初始化'
            }
        
        try:
            # 转换图片为字节数据
            image_data = self._image_to_bytes(image)
            
            # QPS限制控制
            self._rate_limit_control()
            
            # 调用百度OCR API
            result = self.client.webImage(image_data, options or {})
            
            return self._parse_baidu_result(result, "baidu_web_image")
            
        except Exception as e:
            logger.error(f"百度网络图片识别失败: {e}")
            return {
                'engine': 'baidu_web_image',
                'text': '',
                'words': [],
                'total_words': 0,
                'average_confidence': 0,
                'success': False,
                'error': str(e)
            }
    
    def extract_text(self, image: Union[str, bytes, Image.Image], 
                    method: str = "basic_accurate",
                    options: Optional[Dict] = None) -> Dict[str, Any]:
        """
        通用文字识别接口
        
        Args:
            image: 输入图片
            method: 识别方法
            options: 可选参数
            
        Returns:
            识别结果字典
        """
        method_map = {
            "basic_general": self.basic_general,
            "basic_accurate": self.basic_accurate,
            "general": self.general_with_location,
            "accurate": self.accurate_with_location,
            "doc_office": self.doc_analysis_office,
            "table": self.table_recognition,
            "handwriting": self.handwriting_recognition,
            "web_image": self.web_image_recognition
        }
        
        if method not in method_map:
            return {
                'engine': 'baidu',
                'text': '',
                'words': [],
                'total_words': 0,
                'average_confidence': 0,
                'success': False,
                'error': f'不支持的识别方法: {method}'
            }
        
        return method_map[method](image, options)
    
    def health_check(self) -> Dict[str, Any]:
        """
        百度OCR服务健康检查
        
        Returns:
            服务状态信息
        """
        status = {
            'baidu_ocr_available': False,
            'client_initialized': False,
            'api_key_configured': bool(self.api_key),
            'secret_key_configured': bool(self.secret_key),
            'error': None
        }
        
        try:
            if not self.api_key or not self.secret_key:
                status['error'] = 'API密钥或Secret密钥未配置'
                return status
            
            if not self.client:
                status['error'] = '百度OCR客户端未初始化'
                return status
            
            status['client_initialized'] = True
            status['baidu_ocr_available'] = True
            
            # 可以添加一个简单的测试调用
            logger.info("百度OCR服务健康检查通过")
            
        except Exception as e:
            status['error'] = str(e)
            logger.error(f"百度OCR服务健康检查失败: {str(e)}")
        
        return status


# 创建全局实例
baidu_ocr_service = BaiduOCRService()
