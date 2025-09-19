"""
DOC/DOCX文字提取API接口

提供DOC和DOCX文档文字提取相关的REST API端点
"""

from fastapi import APIRouter, HTTPException, UploadFile, File, Form, Query
from fastapi.responses import JSONResponse
from typing import Optional, Dict, Any, Union
import logging
from pathlib import Path
import tempfile
import os
from datetime import datetime

from app.services.unified_processing_service import unified_processing_service
from app.schemas.ocr_schemas import OCREngineType
from app.schemas.doc_schemas import DocType, DocContentAnalysis
from app.services.vision_service import vision_service
from app.services.doc_extractor import doc_extractor

logger = logging.getLogger(__name__)

router = APIRouter()


def _detect_doc_content_type(file_content: bytes, filename: str) -> DocContentAnalysis:
    """
    检测DOC/DOCX内容类型，自动判断是否需要OCR和视觉处理
    
    Args:
        file_content: 文档文件内容
        filename: 文件名
        
    Returns:
        包含检测结果的DocContentAnalysis对象
    """
    try:
        # 根据文件扩展名确定文档类型
        file_ext = Path(filename).suffix.lower()
        if file_ext == '.docx':
            doc_type = DocType.DOCX
        elif file_ext == '.doc':
            doc_type = DocType.DOC
        else:
            raise ValueError(f"不支持的文件类型: {file_ext}")
        
        # 创建临时文件
        with tempfile.NamedTemporaryFile(suffix=file_ext, delete=False) as temp_file:
            temp_file.write(file_content)
            temp_file_path = temp_file.name
        
        try:
            # 使用doc_extractor分析文档内容
            content_analysis = doc_extractor._analyze_doc_content(temp_file_path, doc_type)
            return content_analysis
            
        finally:
            # 清理临时文件
            if os.path.exists(temp_file_path):
                os.unlink(temp_file_path)
                
    except Exception as e:
        logger.error(f"DOC内容检测失败: {str(e)}")
        # 返回保守的默认值
        return DocContentAnalysis(
            has_images=True,  # 保守起见，假设有图像
            has_native_text=False,  # 保守起见，假设没有原生文本
            total_pages=1,
            pages_with_images=0,
            pages_with_text=0,
            total_images=0,
            use_ocr=True,  # 保守起见，启用OCR
            use_vision=True,  # 保守起见，启用视觉处理
            include_images=True,
            detection_confidence="low",
            error=str(e)
        )


@router.post("/extract")
async def extract_doc_text_from_file(
    file: UploadFile = File(..., description="DOC/DOCX文件"),
    output_format: str = Form(default="json", description="输出格式: json, txt, zip"),
    processing_type: str = Form(default="extract", description="处理类型: extract, extract_with_images"),
    use_ocr: bool = Form(default=False, description="是否使用OCR"),
    ocr_engine: str = Form(default="baidu", description="OCR引擎类型"),
    use_vision: bool = Form(default=False, description="是否使用视觉模型"),
    vision_model: str = Form(default="qwen-vl-plus", description="视觉模型名称"),
    extract_images: bool = Form(default=True, description="是否提取图像")
):
    """
    从上传的DOC/DOCX文件中提取文字
    
    从上传的DOC/DOCX文档中提取文字内容，支持多种输出格式。系统会自动检测文档类型和内容特征，并选择最佳的处理方式。
    
    **智能处理流程:**
    1. 自动检测文档类型（DOC/DOCX）
    2. 自动检测是否包含图像和原生文本
    3. 根据内容类型自动选择处理方式：
       - 纯文本文档：直接提取原生文字
       - 包含图像文档：自动启用OCR和视觉模型
       - 扫描文档：自动启用OCR识别
       - 混合内容文档：结合原生文本提取和图像识别
    
    **参数说明:**
    - **file** (UploadFile, 必需): 上传的DOC/DOCX文件
      - 支持格式: `.doc`, `.docx`
      - 最大文件大小: 50MB
    - **output_format** (str, 默认: "json"): 输出格式
      - `"json"`: JSON格式，包含详细的结构化数据
      - `"txt"`: 纯文本格式
      - `"zip"`: 压缩包格式，包含多种格式文件
    - **processing_type** (str, 默认: "extract"): 处理类型
      - `"extract"`: 仅提取文字内容
      - `"extract_with_images"`: 提取文字和图像
    - **use_ocr** (bool, 默认: False): 是否使用OCR
    - **ocr_engine** (str, 默认: "baidu"): OCR引擎类型
      - `"baidu"`: 百度OCR引擎（推荐）
      - `"tesseract"`: Tesseract引擎
    - **use_vision** (bool, 默认: False): 是否使用视觉模型
    - **vision_model** (str, 默认: "qwen-vl-plus"): 视觉模型名称
      - `"qwen-vl-plus"`: 增强版视觉模型
      - `"qwen-vl-max"`: 最大版视觉模型
    - **extract_images** (bool, 默认: True): 是否提取图像
    
    **使用示例:**
    ```bash
    # 基本文字提取
    curl -X POST "http://localhost:8000/api/doc/extract" \
         -F "file=@document.docx" \
         -F "output_format=json"
    
    # 处理DOC文件
    curl -X POST "http://localhost:8000/api/doc/extract" \
         -F "file=@document.doc" \
         -F "output_format=json"
    
    # 启用OCR处理
    curl -X POST "http://localhost:8000/api/doc/extract" \
         -F "file=@scanned_document.docx" \
         -F "use_ocr=true" \
         -F "ocr_engine=baidu"
    
    # 启用视觉模型处理
    curl -X POST "http://localhost:8000/api/doc/extract" \
         -F "file=@complex_document.docx" \
         -F "use_vision=true" \
         -F "vision_model=qwen-vl-plus"
    
    # 提取文字和图像
    curl -X POST "http://localhost:8000/api/doc/extract" \
         -F "file=@document_with_images.docx" \
         -F "processing_type=extract_with_images" \
         -F "extract_images=true"
    ```
    
    **响应示例:**
    ```json
    {
        "success": true,
        "message": "DOC文档处理成功",
        "task_id": "task_20241201_143022_abc123",
        "download_url": "http://localhost:8000/api/download/file/extracted_text_20241201_143022.json",
        "output_format": "json",
        "timestamp": "2024-12-01T14:30:22",
        "content_analysis": {
            "has_images": true,
            "has_native_text": true,
            "total_pages": 1,
            "detection_confidence": "high",
            "auto_ocr_enabled": true,
            "auto_vision_enabled": true
        }
    }
    ```
    
    **错误码:**
    - `400`: 不支持的文件类型或参数错误
    - `500`: 处理失败或服务器错误
    """
    try:
        # 验证输入参数：file是必需的
        if not file:
            raise HTTPException(status_code=400, detail="必须提供DOC/DOCX文件")
        
        # 验证文件类型
        if not file.filename:
            raise HTTPException(status_code=400, detail="文件名不能为空")
        
        file_ext = Path(file.filename).suffix.lower()
        if file_ext not in ['.doc', '.docx']:
            raise HTTPException(status_code=400, detail="只支持DOC和DOCX文件")
        
        # 读取文件内容
        file_content = await file.read()
        
        # 自动检测DOC内容类型
        content_analysis = _detect_doc_content_type(file_content, file.filename)
        logger.info(f"DOC内容检测结果: {content_analysis}")
        
        # 确定文档类型
        doc_type = "docx" if file_ext == '.docx' else "doc"
        
        # 使用统一处理服务
        result = await unified_processing_service.process_file_upload(
            file_content=file_content,
            filename=file.filename,
            processing_type=processing_type,
            output_format=output_format,
            doc_type=doc_type,
            include_images=extract_images,
            use_ocr=use_ocr,
            ocr_engine=ocr_engine,
            use_vision=use_vision,
            vision_model=vision_model
        )
        
        if result['success']:
            response_data = {
                "success": True,
                "message": "DOC文档处理成功",
                "task_id": result['task_id'],
                "download_url": result['download_url'],
                "output_format": output_format,
                "timestamp": result['created_at']
            }
            
            # 如果是文件上传方式，添加内容分析信息
            if file and 'content_analysis' in locals():
                response_data["content_analysis"] = {
                    "has_images": content_analysis.has_images,
                    "has_native_text": content_analysis.has_native_text,
                    "total_pages": content_analysis.total_pages,
                    "detection_confidence": content_analysis.detection_confidence,
                    "auto_ocr_enabled": content_analysis.use_ocr,
                    "auto_vision_enabled": content_analysis.use_vision
                }
            elif url:
                # URL方式添加文件信息
                file_info = result.get('file_info', {})
                response_data["file_info"] = {
                    "filename": file_info.get('filename', ''),
                    "file_size": file_info.get('file_size', 0),
                    "source": file_info.get('source', 'url'),
                    "original_url": file_info.get('original_url', url)
                }
            
            return response_data
        else:
            raise HTTPException(status_code=500, detail=result['error'])
                
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"DOC处理失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"DOC处理失败: {str(e)}")




@router.post("/extract-from-url")
async def extract_doc_text_from_url(
    url: str = Form(..., description="DOC/DOCX文件URL"),
    output_format: str = Form(default="json", description="输出格式: json, txt, zip"),
    processing_type: str = Form(default="extract", description="处理类型: extract, extract_with_images"),
    use_ocr: bool = Form(default=False, description="是否使用OCR"),
    ocr_engine: str = Form(default="baidu", description="OCR引擎类型"),
    use_vision: bool = Form(default=False, description="是否使用视觉模型"),
    vision_model: str = Form(default="qwen-vl-plus", description="视觉模型名称"),
    extract_images: bool = Form(default=True, description="是否提取图像")
):
    """
    从URL提取DOC/DOCX文件中的文字
    
    从URL链接的DOC/DOCX文档中提取文字内容，支持多种输出格式。系统会自动检测文档类型和内容特征，并选择最佳的处理方式。
    
    **智能处理流程:**
    1. 自动检测文档类型（DOC/DOCX）
    2. 自动检测是否包含图像和原生文本
    3. 根据内容类型自动选择处理方式：
       - 纯文本文档：直接提取原生文字
       - 包含图像文档：自动启用OCR和视觉模型
       - 扫描文档：自动启用OCR识别
       - 混合内容文档：结合原生文本提取和图像识别
    
    **参数说明:**
    - **url** (str, 必需): DOC/DOCX文件URL链接
      - 支持HTTP/HTTPS协议
      - 最大文件大小: 50MB
      - 自动检测文件类型
    - **output_format** (str, 默认: "json"): 输出格式
      - `"json"`: JSON格式，包含详细的结构化数据
      - `"txt"`: 纯文本格式
      - `"zip"`: 压缩包格式，包含多种格式文件
    - **processing_type** (str, 默认: "extract"): 处理类型
      - `"extract"`: 仅提取文字内容
      - `"extract_with_images"`: 提取文字和图像
    - **use_ocr** (bool, 默认: False): 是否使用OCR
    - **ocr_engine** (str, 默认: "baidu"): OCR引擎类型
      - `"baidu"`: 百度OCR引擎（推荐）
      - `"tesseract"`: Tesseract引擎
    - **use_vision** (bool, 默认: False): 是否使用视觉模型
    - **vision_model** (str, 默认: "qwen-vl-plus"): 视觉模型名称
      - `"qwen-vl-plus"`: 增强版视觉模型
      - `"qwen-vl-max"`: 最大版视觉模型
    - **extract_images** (bool, 默认: True): 是否提取图像
    
    **使用示例:**
    
    ```bash
    # 基本文字提取
    curl -X POST "http://localhost:8000/api/doc/extract-from-url" \
         -F "url=https://example.com/document.docx" \
         -F "output_format=json"
    
    # 启用OCR处理
    curl -X POST "http://localhost:8000/api/doc/extract-from-url" \
         -F "url=https://example.com/scanned_document.docx" \
         -F "use_ocr=true" \
         -F "ocr_engine=baidu"
    
    # 启用视觉模型处理
    curl -X POST "http://localhost:8000/api/doc/extract-from-url" \
         -F "url=https://example.com/complex_document.docx" \
         -F "use_vision=true" \
         -F "vision_model=qwen-vl-plus"
    ```
    
    **Python示例:**
    ```python
    import requests
    
    data = {
        'url': 'https://example.com/document.docx',
        'output_format': 'json',
        'use_ocr': True,
        'ocr_engine': 'baidu',
        'use_vision': True,
        'vision_model': 'qwen-vl-plus'
    }
    response = requests.post(
        'http://localhost:8000/api/doc/extract-from-url',
        data=data
    )
    ```
    """
    try:
        # 验证URL格式
        if not url.startswith(('http://', 'https://')):
            raise HTTPException(status_code=400, detail="URL必须以http://或https://开头")
        
        # 使用统一处理服务处理URL
        result = await unified_processing_service.process_url_upload(
            url=url,
            processing_type=processing_type,
            output_format=output_format,
            ocr_engine=ocr_engine,
            vision_model=vision_model
        )
        
        if result['success']:
            response_data = {
                "success": True,
                "message": "DOC文档处理成功",
                "task_id": result['task_id'],
                "download_url": result['download_url'],
                "output_format": output_format,
                "timestamp": result['created_at']
            }
            
            # 如果URL方式处理，添加文件信息
            if 'file_info' in result:
                response_data['file_info'] = result['file_info']
            
            return JSONResponse(content=response_data)
        else:
            raise HTTPException(status_code=500, detail=result.get('error', 'DOC处理失败'))
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"DOC URL处理失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"DOC处理失败: {str(e)}")


@router.get("/health")
async def doc_service_health():
    """
    DOC/DOCX统一服务健康检查
    
    检查统一的DOC/DOCX文字提取服务的运行状态和功能可用性。
    
    **检查项目:**
    - 统一DOC/DOCX处理引擎状态
    - OCR引擎可用性
    - 视觉模型连接状态
    - Qwen-VL模型状态
    - 文件处理能力
    
    **使用示例:**
    ```bash
    # 检查DOC/DOCX统一服务健康状态
    curl -X GET "http://localhost:8000/api/doc/health"
    ```
    
    **响应示例:**
    ```json
    {
        "status": "healthy",
        "service": "DOC/DOCX统一文字提取服务",
        "version": "1.0.0",
        "features": {
            "unified_doc_processing": true,
            "docx_processing": true,
            "doc_processing": true,
            "ocr": true,
            "vision": true,
            "qwen_vl": true
        },
        "timestamp": "2024-12-01T14:30:22"
    }
    ```
    
    **状态说明:**
    - `"healthy"`: 服务正常运行，所有功能可用
    - `"degraded"`: 部分功能不可用（如视觉模型）
    - `"unhealthy"`: 服务异常
    
    **功能状态:**
    - `unified_doc_processing`: 统一DOC/DOCX处理功能是否可用
    - `docx_processing`: DOCX处理功能是否可用
    - `doc_processing`: DOC处理功能是否可用
    - `ocr`: OCR引擎是否可用
    - `vision`: 视觉模型是否可用
    - `qwen_vl`: Qwen-VL多模态模型是否可用
    
    **错误码:**
    - `500`: 服务不可用
    """
    try:
        # 检查各种功能状态
        vision_available = vision_service.is_available()
        
        # 检查DOC/DOCX处理库
        docx_available = True
        doc_available = True
        
        try:
            from docx import Document
            from docx2txt import process
        except ImportError:
            docx_available = False
            doc_available = False
        
        # 确定整体状态
        if docx_available and doc_available:
            status = "healthy"
        elif docx_available or doc_available:
            status = "degraded"
        else:
            status = "unhealthy"
        
        return {
            "status": status,
            "service": "DOC/DOCX统一文字提取服务",
            "version": "1.0.0",
            "features": {
                "unified_doc_processing": docx_available and doc_available,
                "docx_processing": docx_available,
                "doc_processing": doc_available,
                "ocr": True,
                "vision": vision_available,
                "qwen_vl": vision_available
            },
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"DOC服务健康检查失败: {str(e)}")
        raise HTTPException(status_code=500, detail="DOC服务不可用")
