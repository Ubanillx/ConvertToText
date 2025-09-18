"""
OCR文字识别相关的数据模型和响应格式
"""

from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any, Union
from datetime import datetime
from enum import Enum


class OCREngineType(str, Enum):
    """OCR引擎类型"""
    TESSERACT = "tesseract"
    BAIDU = "baidu"


class OCRWordInfo(BaseModel):
    """OCR识别的单词信息"""
    text: str = Field(..., description="识别的文字内容")
    confidence: float = Field(..., description="识别置信度", ge=0, le=1)
    bbox: List[float] = Field(..., description="边界框坐标 [x1, y1, x2, y2] 或 [x1, y1, x2, y2, x3, y3, x4, y4]")


class OCRResult(BaseModel):
    """OCR识别结果"""
    engine: str = Field(..., description="使用的OCR引擎")
    text: str = Field(..., description="识别的完整文字")
    words: List[OCRWordInfo] = Field(default=[], description="识别的单词列表")
    total_words: int = Field(default=0, description="识别的单词总数")
    average_confidence: float = Field(default=0.0, description="平均置信度")
    processing_time: Optional[float] = Field(None, description="处理时间（秒）")
    image_index: Optional[int] = Field(None, description="图片索引（批量处理时使用）")
    page_number: Optional[int] = Field(None, description="页码（PDF处理时使用）")
    pdf_path: Optional[str] = Field(None, description="PDF文件路径（PDF处理时使用）")


class OCRRequest(BaseModel):
    """OCR识别请求"""
    engine: OCREngineType = Field(default=OCREngineType.TESSERACT, description="OCR引擎类型")
    preprocess: bool = Field(default=True, description="是否进行图片预处理")
    language: Optional[str] = Field(None, description="识别语言")
    method: Optional[str] = Field(default="basic_accurate", description="百度OCR识别方法")
    options: Optional[Dict[str, Any]] = Field(None, description="百度OCR可选参数")


class OCRResponse(BaseModel):
    """OCR识别响应"""
    success: bool = Field(..., description="是否成功")
    message: str = Field(..., description="响应消息")
    data: Optional[OCRResult] = Field(None, description="识别结果")
    error: Optional[str] = Field(None, description="错误信息")
    timestamp: datetime = Field(default_factory=datetime.now, description="响应时间戳")


class BatchOCRRequest(BaseModel):
    """批量OCR识别请求"""
    engine: OCREngineType = Field(default=OCREngineType.TESSERACT, description="OCR引擎类型")
    preprocess: bool = Field(default=True, description="是否进行图片预处理")
    language: Optional[str] = Field(None, description="识别语言")
    method: Optional[str] = Field(default="basic_accurate", description="百度OCR识别方法")
    options: Optional[Dict[str, Any]] = Field(None, description="百度OCR可选参数")


class BatchOCRResponse(BaseModel):
    """批量OCR识别响应"""
    success: bool = Field(..., description="是否成功")
    message: str = Field(..., description="响应消息")
    data: List[OCRResult] = Field(default=[], description="识别结果列表")
    total_images: int = Field(default=0, description="总图片数量")
    success_count: int = Field(default=0, description="成功识别数量")
    error_count: int = Field(default=0, description="失败数量")
    error: Optional[str] = Field(None, description="错误信息")
    timestamp: datetime = Field(default_factory=datetime.now, description="响应时间戳")


class PDFOCRRequest(BaseModel):
    """PDF OCR识别请求"""
    file_path: str = Field(..., description="PDF文件路径")
    page_number: Optional[int] = Field(None, description="页码（从1开始，None表示所有页面）")
    engine: OCREngineType = Field(default=OCREngineType.TESSERACT, description="OCR引擎类型")
    preprocess: bool = Field(default=True, description="是否进行图片预处理")
    method: Optional[str] = Field(default="basic_accurate", description="百度OCR识别方法")
    options: Optional[Dict[str, Any]] = Field(None, description="百度OCR可选参数")


class PDFOCRResult(BaseModel):
    """PDF OCR识别结果"""
    file_path: str = Field(..., description="PDF文件路径")
    total_pages: int = Field(..., description="总页数")
    pages: List[OCRResult] = Field(default=[], description="各页面识别结果")
    full_text: str = Field(default="", description="合并后的完整文字")
    extraction_method: str = Field(default="ocr", description="提取方法")
    processing_time: Optional[float] = Field(None, description="总处理时间（秒）")


class PDFOCRResponse(BaseModel):
    """PDF OCR识别响应"""
    success: bool = Field(..., description="是否成功")
    message: str = Field(..., description="响应消息")
    data: Optional[PDFOCRResult] = Field(None, description="识别结果")
    error: Optional[str] = Field(None, description="错误信息")
    timestamp: datetime = Field(default_factory=datetime.now, description="响应时间戳")


class OCRHealthResponse(BaseModel):
    """OCR服务健康检查响应"""
    success: bool = Field(..., description="是否成功")
    message: str = Field(..., description="响应消息")
    data: Dict[str, Any] = Field(..., description="服务状态信息")
    timestamp: datetime = Field(default_factory=datetime.now, description="响应时间戳")


class SupportedLanguagesResponse(BaseModel):
    """支持的语言列表响应"""
    success: bool = Field(..., description="是否成功")
    message: str = Field(..., description="响应消息")
    data: Dict[str, List[str]] = Field(..., description="各引擎支持的语言列表")
    timestamp: datetime = Field(default_factory=datetime.now, description="响应时间戳")
