"""
PDF处理相关的数据模型

定义PDF文字提取相关的Pydantic模型
"""

from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional
from datetime import datetime


class PageInfo(BaseModel):
    """页面基本信息"""
    page_number: int = Field(..., description="页码（从1开始）")
    width: float = Field(..., description="页面宽度")
    height: float = Field(..., description="页面高度")
    rotation: int = Field(0, description="页面旋转角度")


class SpanInfo(BaseModel):
    """文本片段信息"""
    text: str = Field(..., description="文本内容")
    font: str = Field(..., description="字体名称")
    size: float = Field(..., description="字体大小")
    flags: int = Field(..., description="字体标志")
    color: int = Field(..., description="颜色值")
    bbox: List[float] = Field(..., description="边界框坐标 [x0, y0, x1, y1]")


class LineInfo(BaseModel):
    """文本行信息"""
    text: str = Field(..., description="行文本内容")
    bbox: List[float] = Field(..., description="行边界框坐标")
    spans: List[SpanInfo] = Field(..., description="文本片段列表")


class TextBlock(BaseModel):
    """文本块信息"""
    type: str = Field(..., description="块类型：text 或 image")
    text: Optional[str] = Field(None, description="文本内容（仅文本块）")
    bbox: List[float] = Field(..., description="边界框坐标")
    lines: Optional[List[LineInfo]] = Field(None, description="文本行列表（仅文本块）")
    image_info: Optional[Dict[str, Any]] = Field(None, description="图像信息（仅图像块）")


class ImageInfo(BaseModel):
    """图像信息"""
    index: int = Field(..., description="图像索引")
    xref: int = Field(..., description="交叉引用")
    smask: int = Field(..., description="软遮罩")
    width: int = Field(..., description="图像宽度")
    height: int = Field(..., description="图像高度")
    bpc: int = Field(..., description="每通道位数")
    colorspace: int = Field(..., description="颜色空间")
    alt: str = Field(..., description="替代文本")
    name: str = Field(..., description="图像名称")


class PageResult(BaseModel):
    """页面提取结果"""
    page_info: PageInfo = Field(..., description="页面基本信息")
    text: str = Field(..., description="页面文本内容")
    text_length: int = Field(..., description="文本长度")
    text_blocks: List[TextBlock] = Field(..., description="文本块列表")
    images_count: int = Field(..., description="图像数量")
    images_info: List[ImageInfo] = Field(..., description="图像信息列表")
    is_text_page: bool = Field(..., description="是否为文本页面")
    has_images: bool = Field(..., description="是否包含图像")
    error: Optional[str] = Field(None, description="错误信息")


class PDFExtractionResult(BaseModel):
    """PDF文字提取结果"""
    file_path: str = Field(..., description="PDF文件路径")
    total_pages: int = Field(..., description="总页数")
    pages: List[PageResult] = Field(..., description="页面提取结果列表")
    full_text: str = Field(..., description="完整文本内容")
    has_text_layer: bool = Field(..., description="是否有文本层")
    is_scanned: bool = Field(..., description="是否为扫描文档")
    extraction_method: str = Field(..., description="提取方法")
    extraction_time: Optional[datetime] = Field(None, description="提取时间")


class PDFInfo(BaseModel):
    """PDF文件基本信息"""
    file_path: str = Field(..., description="文件路径")
    file_size: int = Field(..., description="文件大小（字节）")
    total_pages: int = Field(..., description="总页数")
    title: str = Field("", description="文档标题")
    author: str = Field("", description="作者")
    subject: str = Field("", description="主题")
    creator: str = Field("", description="创建者")
    producer: str = Field("", description="生产者")
    creation_date: str = Field("", description="创建日期")
    modification_date: str = Field("", description="修改日期")
    is_encrypted: bool = Field(False, description="是否加密")
    needs_pass: bool = Field(False, description="是否需要密码")
    page_count: int = Field(..., description="页面数量")


class PDFUploadRequest(BaseModel):
    """PDF上传请求"""
    file_path: str = Field(..., description="PDF文件路径")
    extract_formatting: bool = Field(False, description="是否提取格式信息")
    include_images: bool = Field(True, description="是否包含图像信息")


class PDFExtractionResponse(BaseModel):
    """PDF提取响应"""
    success: bool = Field(..., description="是否成功")
    message: str = Field(..., description="响应消息")
    data: Optional[PDFExtractionResult] = Field(None, description="提取结果")
    error: Optional[str] = Field(None, description="错误信息")


class PDFInfoResponse(BaseModel):
    """PDF信息响应"""
    success: bool = Field(..., description="是否成功")
    message: str = Field(..., description="响应消息")
    data: Optional[PDFInfo] = Field(None, description="PDF信息")
    error: Optional[str] = Field(None, description="错误信息")


class ScannedDetectionResponse(BaseModel):
    """扫描文档检测响应"""
    success: bool = Field(..., description="是否成功")
    message: str = Field(..., description="响应消息")
    is_scanned: bool = Field(..., description="是否为扫描文档")
    confidence: float = Field(..., description="置信度")
    error: Optional[str] = Field(None, description="错误信息")

