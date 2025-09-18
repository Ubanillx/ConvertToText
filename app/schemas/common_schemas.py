"""
通用数据模型和响应格式
"""

from pydantic import BaseModel, Field, HttpUrl
from typing import List, Dict, Any, Optional, Union
from datetime import datetime
from enum import Enum


class ProcessingStatus(str, Enum):
    """处理状态枚举"""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class FileType(str, Enum):
    """支持的文件类型"""
    PDF = "pdf"
    IMAGE = "image"
    TEXT = "text"
    DOCUMENT = "document"


class InputSource(str, Enum):
    """输入源类型"""
    UPLOAD = "upload"
    URL = "url"
    PATH = "path"


class UnifiedRequest(BaseModel):
    """统一请求模型"""
    # 文件上传相关
    file: Optional[Any] = Field(None, description="上传的文件")
    
    # URL相关
    url: Optional[HttpUrl] = Field(None, description="文件URL地址")
    
    # 文件路径相关
    file_path: Optional[str] = Field(None, description="本地文件路径")
    
    # 处理参数
    processing_options: Dict[str, Any] = Field(default_factory=dict, description="处理选项")
    
    # 输出选项
    output_format: str = Field(default="text", description="输出格式")
    include_metadata: bool = Field(default=True, description="是否包含元数据")
    
    # 回调选项
    callback_url: Optional[HttpUrl] = Field(None, description="处理完成后的回调URL")


class ProcessingResult(BaseModel):
    """处理结果"""
    task_id: str = Field(..., description="任务ID")
    status: ProcessingStatus = Field(..., description="处理状态")
    input_source: InputSource = Field(..., description="输入源类型")
    file_type: FileType = Field(..., description="文件类型")
    
    # 处理结果
    extracted_text: Optional[str] = Field(None, description="提取的文本内容")
    processed_data: Optional[Dict[str, Any]] = Field(None, description="处理后的数据")
    
    # 元数据
    metadata: Dict[str, Any] = Field(default_factory=dict, description="元数据信息")
    
    # 文件信息
    original_filename: Optional[str] = Field(None, description="原始文件名")
    file_size: Optional[int] = Field(None, description="文件大小（字节）")
    page_count: Optional[int] = Field(None, description="页面数量")
    
    # 处理信息
    processing_time: Optional[float] = Field(None, description="处理时间（秒）")
    processing_method: Optional[str] = Field(None, description="处理方法")
    
    # 错误信息
    error_message: Optional[str] = Field(None, description="错误信息")
    
    # 时间戳
    created_at: datetime = Field(default_factory=datetime.now, description="创建时间")
    updated_at: datetime = Field(default_factory=datetime.now, description="更新时间")


class UnifiedResponse(BaseModel):
    """统一响应模型"""
    success: bool = Field(..., description="是否成功")
    message: str = Field(..., description="响应消息")
    
    # 下载地址
    download_url: Optional[HttpUrl] = Field(None, description="结果文件下载地址")
    
    # 处理结果
    result: Optional[ProcessingResult] = Field(None, description="处理结果")
    
    # 错误信息
    error: Optional[str] = Field(None, description="错误信息")
    
    # 时间戳
    timestamp: datetime = Field(default_factory=datetime.now, description="响应时间戳")


class BatchProcessingRequest(BaseModel):
    """批量处理请求"""
    files: Optional[List[Any]] = Field(None, description="上传的文件列表")
    urls: Optional[List[HttpUrl]] = Field(None, description="文件URL列表")
    file_paths: Optional[List[str]] = Field(None, description="本地文件路径列表")
    
    # 处理参数
    processing_options: Dict[str, Any] = Field(default_factory=dict, description="处理选项")
    output_format: str = Field(default="text", description="输出格式")
    
    # 并发控制
    max_workers: int = Field(default=3, description="最大并发数")


class BatchProcessingResult(BaseModel):
    """批量处理结果"""
    task_id: str = Field(..., description="批量任务ID")
    total_count: int = Field(..., description="总文件数")
    success_count: int = Field(..., description="成功处理数")
    failed_count: int = Field(..., description="失败数")
    
    # 结果列表
    results: List[ProcessingResult] = Field(default=[], description="处理结果列表")
    
    # 下载地址
    download_url: Optional[HttpUrl] = Field(None, description="批量结果下载地址")
    
    # 处理信息
    total_processing_time: Optional[float] = Field(None, description="总处理时间")
    
    # 时间戳
    created_at: datetime = Field(default_factory=datetime.now, description="创建时间")
    completed_at: Optional[datetime] = Field(None, description="完成时间")


class BatchProcessingResponse(BaseModel):
    """批量处理响应"""
    success: bool = Field(..., description="是否成功")
    message: str = Field(..., description="响应消息")
    
    # 批量结果
    result: Optional[BatchProcessingResult] = Field(None, description="批量处理结果")
    
    # 错误信息
    error: Optional[str] = Field(None, description="错误信息")
    
    # 时间戳
    timestamp: datetime = Field(default_factory=datetime.now, description="响应时间戳")


class TaskStatusResponse(BaseModel):
    """任务状态响应"""
    task_id: str = Field(..., description="任务ID")
    status: ProcessingStatus = Field(..., description="任务状态")
    progress: float = Field(default=0.0, description="处理进度（0-100）")
    
    # 结果信息
    download_url: Optional[HttpUrl] = Field(None, description="结果下载地址")
    result: Optional[ProcessingResult] = Field(None, description="处理结果")
    
    # 错误信息
    error_message: Optional[str] = Field(None, description="错误信息")
    
    # 时间戳
    created_at: datetime = Field(..., description="创建时间")
    updated_at: datetime = Field(..., description="更新时间")


class HealthResponse(BaseModel):
    """健康检查响应"""
    status: str = Field(..., description="服务状态")
    service_name: str = Field(..., description="服务名称")
    version: str = Field(..., description="版本号")
    
    # 功能支持
    supported_features: Dict[str, bool] = Field(..., description="支持的功能")
    
    # 服务信息
    uptime: Optional[float] = Field(None, description="运行时间（秒）")
    memory_usage: Optional[float] = Field(None, description="内存使用率")
    
    # 时间戳
    timestamp: datetime = Field(default_factory=datetime.now, description="检查时间")
