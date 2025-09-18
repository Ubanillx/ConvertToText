"""
DOC/DOCX文档处理相关的数据模式定义

包含DOC和DOCX文档处理过程中使用的数据结构和类型定义
"""

from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional, Union
from enum import Enum


class DocType(str, Enum):
    """文档类型枚举"""
    DOC = "doc"
    DOCX = "docx"


class DocProcessingType(str, Enum):
    """DOC处理类型枚举"""
    EXTRACT = "extract"
    EXTRACT_WITH_IMAGES = "extract_with_images"
    EXTRACT_WITH_FORMATTING = "extract_with_formatting"


class DocExtractionMethod(str, Enum):
    """DOC提取方法枚举"""
    NATIVE_TEXT = "native_text"
    OCR_PROCESSED = "ocr_processed"
    VISION_PROCESSED = "vision_processed"
    OCR_VISION_FUSION = "ocr_vision_fusion"
    MIXED_CONTENT = "mixed_content"
    IMAGE_ONLY = "image_only"
    ERROR = "error"


class DocImageInfo(BaseModel):
    """DOC文档中的图像信息"""
    image_id: str = Field(..., description="图像唯一标识")
    image_name: Optional[str] = Field(None, description="图像名称")
    image_type: str = Field(..., description="图像类型 (png, jpeg, etc.)")
    image_size: int = Field(..., description="图像大小（字节）")
    width: Optional[int] = Field(None, description="图像宽度")
    height: Optional[int] = Field(None, description="图像高度")
    has_ocr_text: bool = Field(False, description="是否包含OCR识别的文字")
    has_vision_text: bool = Field(False, description="是否包含视觉模型识别的文字")


class DocParagraphInfo(BaseModel):
    """DOC文档段落信息"""
    paragraph_id: str = Field(..., description="段落唯一标识")
    text: str = Field(..., description="段落文本内容")
    text_length: int = Field(..., description="文本长度")
    font_name: Optional[str] = Field(None, description="字体名称")
    font_size: Optional[float] = Field(None, description="字体大小")
    is_bold: bool = Field(False, description="是否粗体")
    is_italic: bool = Field(False, description="是否斜体")
    is_underlined: bool = Field(False, description="是否下划线")
    alignment: Optional[str] = Field(None, description="对齐方式")
    has_images: bool = Field(False, description="是否包含图像")
    image_ids: List[str] = Field(default_factory=list, description="关联的图像ID列表")


class DocPageInfo(BaseModel):
    """DOC文档页面信息"""
    page_number: int = Field(..., description="页码")
    text: str = Field(..., description="页面文本内容")
    text_length: int = Field(..., description="文本长度")
    paragraphs: List[DocParagraphInfo] = Field(default_factory=list, description="段落列表")
    images: List[DocImageInfo] = Field(default_factory=list, description="图像列表")
    processing_type: DocExtractionMethod = Field(..., description="处理类型")
    extraction_method: str = Field(..., description="提取方法")
    has_images: bool = Field(False, description="是否包含图像")
    ocr_confidence: Optional[float] = Field(None, description="OCR置信度")
    vision_confidence: Optional[float] = Field(None, description="视觉模型置信度")
    error: Optional[str] = Field(None, description="错误信息")


class DocProcessingStats(BaseModel):
    """DOC处理统计信息"""
    total_pages: int = Field(0, description="总页数")
    native_text_pages: int = Field(0, description="原生文本页面数")
    ocr_processed_pages: int = Field(0, description="OCR处理页面数")
    vision_processed_pages: int = Field(0, description="视觉模型处理页面数")
    image_only_pages: int = Field(0, description="纯图像页面数")
    mixed_content_pages: int = Field(0, description="混合内容页面数")
    error_pages: int = Field(0, description="错误页面数")
    total_images: int = Field(0, description="总图像数")
    processed_images: int = Field(0, description="已处理图像数")


class DocExtractionResult(BaseModel):
    """DOC文档提取结果"""
    file_path: str = Field(..., description="文件路径")
    file_type: DocType = Field(..., description="文件类型")
    total_pages: int = Field(..., description="总页数")
    pages: List[DocPageInfo] = Field(default_factory=list, description="页面列表")
    full_text: str = Field(..., description="完整文本内容")
    has_text_layer: bool = Field(False, description="是否有文本层")
    is_scanned: bool = Field(False, description="是否为扫描文档")
    extraction_method: str = Field(..., description="提取方法")
    processing_stats: DocProcessingStats = Field(..., description="处理统计信息")
    document_properties: Optional[Dict[str, Any]] = Field(None, description="文档属性")
    created_at: str = Field(..., description="创建时间")
    processing_time: Optional[float] = Field(None, description="处理时间（秒）")


class DocProcessingRequest(BaseModel):
    """DOC处理请求"""
    file_path: str = Field(..., description="文件路径")
    doc_type: DocType = Field(..., description="文档类型")
    processing_type: DocProcessingType = Field(DocProcessingType.EXTRACT, description="处理类型")
    use_ocr: bool = Field(False, description="是否使用OCR")
    ocr_engine: str = Field("baidu", description="OCR引擎")
    use_vision: bool = Field(False, description="是否使用视觉模型")
    vision_model: str = Field("qwen-vl-plus", description="视觉模型")
    extract_formatting: bool = Field(False, description="是否提取格式信息")
    extract_images: bool = Field(True, description="是否提取图像")


class DocProcessingResponse(BaseModel):
    """DOC处理响应"""
    success: bool = Field(..., description="是否成功")
    task_id: str = Field(..., description="任务ID")
    result: Optional[DocExtractionResult] = Field(None, description="提取结果")
    download_url: Optional[str] = Field(None, description="下载URL")
    error: Optional[str] = Field(None, description="错误信息")
    created_at: str = Field(..., description="创建时间")


class DocContentAnalysis(BaseModel):
    """DOC内容分析结果"""
    has_images: bool = Field(False, description="是否包含图像")
    has_native_text: bool = Field(False, description="是否有原生文本")
    total_pages: int = Field(0, description="总页数")
    pages_with_images: int = Field(0, description="包含图像的页面数")
    pages_with_text: int = Field(0, description="包含文本的页面数")
    total_images: int = Field(0, description="总图像数")
    use_ocr: bool = Field(False, description="是否使用OCR")
    use_vision: bool = Field(False, description="是否使用视觉模型")
    include_images: bool = Field(False, description="是否包含图像处理")
    detection_confidence: str = Field("low", description="检测置信度")
    error: Optional[str] = Field(None, description="错误信息")


class DocImageExtractionResult(BaseModel):
    """DOC图像提取结果"""
    image_id: str = Field(..., description="图像ID")
    image_data: bytes = Field(..., description="图像数据")
    image_type: str = Field(..., description="图像类型")
    ocr_text: Optional[str] = Field(None, description="OCR识别文本")
    vision_text: Optional[str] = Field(None, description="视觉模型识别文本")
    ocr_confidence: Optional[float] = Field(None, description="OCR置信度")
    vision_confidence: Optional[float] = Field(None, description="视觉模型置信度")
    success: bool = Field(True, description="是否成功")
    error: Optional[str] = Field(None, description="错误信息")


class DocFusionResult(BaseModel):
    """DOC融合结果"""
    final_text: str = Field(..., description="最终文本")
    fusion_method: str = Field(..., description="融合方法")
    ocr_contribution: float = Field(0.0, description="OCR贡献度")
    vision_contribution: float = Field(0.0, description="视觉模型贡献度")
    confidence: float = Field(0.0, description="整体置信度")
