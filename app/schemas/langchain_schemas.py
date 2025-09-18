"""
LangChain相关的数据模型
"""

from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional, Union
from enum import Enum


class DocumentType(str, Enum):
    """文档类型枚举"""
    GENERAL = "general"
    CONTRACT = "contract"
    REPORT = "report"
    INVOICE = "invoice"
    EMAIL = "email"
    ARTICLE = "article"


class TextProcessingRequest(BaseModel):
    """文本处理请求"""
    text: str = Field(..., description="要处理的文本内容")
    operation: str = Field(..., description="处理操作类型")
    max_keywords: Optional[int] = Field(default=10, description="最大关键词数量")
    max_length: Optional[int] = Field(default=200, description="摘要最大长度")
    target_language: Optional[str] = Field(default="英文", description="目标语言")


class TextProcessingResponse(BaseModel):
    """文本处理响应"""
    success: bool = Field(..., description="处理是否成功")
    result: Union[str, Dict[str, Any]] = Field(..., description="处理结果")
    error_message: Optional[str] = Field(default=None, description="错误信息")


class DocumentProcessingRequest(BaseModel):
    """文档处理请求"""
    content: str = Field(..., description="文档内容")
    doc_type: DocumentType = Field(default=DocumentType.GENERAL, description="文档类型")
    extract_keywords: bool = Field(default=True, description="是否提取关键词")
    generate_summary: bool = Field(default=True, description="是否生成摘要")
    analyze_structure: bool = Field(default=True, description="是否分析结构")


class DocumentProcessingResponse(BaseModel):
    """文档处理响应"""
    success: bool = Field(..., description="处理是否成功")
    original_text: str = Field(..., description="原始文本")
    cleaned_text: str = Field(..., description="清理后的文本")
    chunks: List[str] = Field(..., description="文本分块")
    keywords: List[str] = Field(..., description="关键词列表")
    summary: str = Field(..., description="文本摘要")
    word_count: int = Field(..., description="字数统计")
    chunk_count: int = Field(..., description="分块数量")
    analysis: Optional[str] = Field(default=None, description="专业分析结果")
    error_message: Optional[str] = Field(default=None, description="错误信息")


class QuestionAnswerRequest(BaseModel):
    """问答请求"""
    text: str = Field(..., description="参考文本")
    question: str = Field(..., description="问题")
    context: Optional[str] = Field(default=None, description="额外上下文")


class QuestionAnswerResponse(BaseModel):
    """问答响应"""
    success: bool = Field(..., description="处理是否成功")
    question: str = Field(..., description="问题")
    answer: str = Field(..., description="答案")
    confidence: Optional[float] = Field(default=None, description="置信度")
    error_message: Optional[str] = Field(default=None, description="错误信息")


class TranslationRequest(BaseModel):
    """翻译请求"""
    text: str = Field(..., description="要翻译的文本")
    target_language: str = Field(default="英文", description="目标语言")
    source_language: Optional[str] = Field(default=None, description="源语言")


class TranslationResponse(BaseModel):
    """翻译响应"""
    success: bool = Field(..., description="翻译是否成功")
    original_text: str = Field(..., description="原文")
    translated_text: str = Field(..., description="译文")
    source_language: Optional[str] = Field(default=None, description="源语言")
    target_language: str = Field(..., description="目标语言")
    error_message: Optional[str] = Field(default=None, description="错误信息")


class ConversationRequest(BaseModel):
    """对话请求"""
    message: str = Field(..., description="用户消息")
    context: Optional[str] = Field(default=None, description="上下文信息")
    clear_history: bool = Field(default=False, description="是否清空历史")


class ConversationResponse(BaseModel):
    """对话响应"""
    success: bool = Field(..., description="处理是否成功")
    user_message: str = Field(..., description="用户消息")
    bot_response: str = Field(..., description="机器人回复")
    conversation_id: Optional[str] = Field(default=None, description="对话ID")
    error_message: Optional[str] = Field(default=None, description="错误信息")


class LLMHealthResponse(BaseModel):
    """LLM健康检查响应"""
    dashscope_available: bool = Field(..., description="百炼平台是否可用")
    openai_available: bool = Field(..., description="OpenAI是否可用")
    dashscope_model: str = Field(..., description="百炼平台模型")
    openai_model: str = Field(..., description="OpenAI模型")
    last_check: str = Field(..., description="最后检查时间")


class BatchProcessingRequest(BaseModel):
    """批量处理请求"""
    texts: List[str] = Field(..., description="文本列表")
    operation: str = Field(..., description="处理操作")
    doc_type: Optional[DocumentType] = Field(default=DocumentType.GENERAL, description="文档类型")
    max_workers: int = Field(default=3, description="最大并发数")


class BatchProcessingResponse(BaseModel):
    """批量处理响应"""
    success: bool = Field(..., description="处理是否成功")
    total_count: int = Field(..., description="总数量")
    success_count: int = Field(..., description="成功数量")
    failed_count: int = Field(..., description="失败数量")
    results: List[Dict[str, Any]] = Field(..., description="处理结果列表")
    error_message: Optional[str] = Field(default=None, description="错误信息")
