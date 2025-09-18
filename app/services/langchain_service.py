"""
LangChain服务模块
提供基于LangChain的文本处理功能，集成百炼平台LLM
"""

import os
import logging
from typing import List, Dict, Any, Optional, Union
from langchain.llms.base import LLM
from langchain.callbacks.manager import CallbackManagerForLLMRun
from langchain.schema import BaseMessage, HumanMessage, AIMessage, SystemMessage
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.chains import LLMChain
from langchain.prompts import PromptTemplate
from langchain.memory import ConversationBufferMemory
from langchain.chains.conversation.memory import ConversationBufferWindowMemory
from langchain.schema.output_parser import StrOutputParser
from langchain.schema.runnable import RunnablePassthrough
from langchain.schema.runnable.utils import Input, Output
import dashscope
from dashscope import Generation
from pydantic import BaseModel, Field
from app.core.config import settings

# 配置日志
logger = logging.getLogger(__name__)


class DashScopeLLM(LLM):
    """百炼平台LLM包装器"""
    
    model_name: str = Field(default="qwen-plus")
    temperature: float = Field(default=0.7)
    max_tokens: int = Field(default=2000)
    api_key: Optional[str] = Field(default=None)
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        if self.api_key:
            dashscope.api_key = self.api_key
        elif settings.dashscope_api_key:
            dashscope.api_key = settings.dashscope_api_key
        else:
            logger.warning("未设置百炼平台API密钥")
    
    @property
    def _llm_type(self) -> str:
        return "dashscope"
    
    def _call(
        self,
        prompt: str,
        stop: Optional[List[str]] = None,
        run_manager: Optional[CallbackManagerForLLMRun] = None,
        **kwargs: Any,
    ) -> str:
        """调用百炼平台API"""
        try:
            response = Generation.call(
                model=self.model_name,
                prompt=prompt,
                temperature=self.temperature,
                max_tokens=self.max_tokens,
                **kwargs
            )
            
            if response.status_code == 200:
                return response.output.text
            else:
                logger.error(f"百炼平台API调用失败: {response.message}")
                return f"API调用失败: {response.message}"
                
        except Exception as e:
            logger.error(f"百炼平台API调用异常: {str(e)}")
            return f"API调用异常: {str(e)}"


class TextProcessor:
    """文本处理器"""
    
    def __init__(self):
        self.llm = DashScopeLLM(
            model_name=settings.dashscope_model,
            temperature=settings.dashscope_temperature,
            max_tokens=settings.dashscope_max_tokens,
            api_key=settings.dashscope_api_key
        )
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000,
            chunk_overlap=200,
            length_function=len,
        )
    
    def clean_text(self, text: str) -> str:
        """清理文本"""
        # 移除多余的空白字符
        text = " ".join(text.split())
        
        # 移除特殊字符（保留中文、英文、数字、标点）
        import re
        text = re.sub(r'[^\u4e00-\u9fff\w\s.,!?;:()（）【】""''""''，。！？；：]', '', text)
        
        return text.strip()
    
    def extract_keywords(self, text: str, max_keywords: int = 10) -> List[str]:
        """提取关键词"""
        prompt = f"""
        请从以下文本中提取{max_keywords}个最重要的关键词，用逗号分隔：
        
        文本：{text}
        
        关键词：
        """
        
        try:
            response = self.llm(prompt)
            keywords = [kw.strip() for kw in response.split(',')]
            return keywords[:max_keywords]
        except Exception as e:
            logger.error(f"关键词提取失败: {str(e)}")
            return []
    
    def summarize_text(self, text: str, max_length: int = 200) -> str:
        """文本摘要"""
        prompt = f"""
        请为以下文本生成一个简洁的摘要，不超过{max_length}字：
        
        文本：{text}
        
        摘要：
        """
        
        try:
            return self.llm(prompt)
        except Exception as e:
            logger.error(f"文本摘要失败: {str(e)}")
            return "摘要生成失败"
    
    def structure_text(self, text: str) -> Dict[str, Any]:
        """结构化文本处理"""
        # 清理文本
        cleaned_text = self.clean_text(text)
        
        # 分块处理
        chunks = self.text_splitter.split_text(cleaned_text)
        
        # 提取关键词
        keywords = self.extract_keywords(cleaned_text)
        
        # 生成摘要
        summary = self.summarize_text(cleaned_text)
        
        return {
            "original_text": text,
            "cleaned_text": cleaned_text,
            "chunks": chunks,
            "keywords": keywords,
            "summary": summary,
            "word_count": len(cleaned_text),
            "chunk_count": len(chunks)
        }
    
    def translate_text(self, text: str, target_language: str = "英文") -> str:
        """翻译文本"""
        prompt = f"""
        请将以下文本翻译成{target_language}：
        
        原文：{text}
        
        译文：
        """
        
        try:
            return self.llm(prompt)
        except Exception as e:
            logger.error(f"文本翻译失败: {str(e)}")
            return "翻译失败"


# 全局实例
text_processor = TextProcessor()
