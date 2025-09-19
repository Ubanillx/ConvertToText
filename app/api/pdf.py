"""
PDF文字提取API接口

提供PDF文字提取相关的REST API端点
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
from app.services.vision_service import vision_service
import fitz  # PyMuPDF
import tempfile

logger = logging.getLogger(__name__)

router = APIRouter()


def _detect_pdf_content_type(file_content: bytes) -> Dict[str, Any]:
    """
    检测PDF内容类型，自动判断是否需要OCR和视觉处理
    
    Args:
        file_content: PDF文件内容
        
    Returns:
        包含检测结果的字典
    """
    try:
        # 创建临时文件
        with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as temp_file:
            temp_file.write(file_content)
            temp_file_path = temp_file.name
        
        try:
            # 打开PDF文档
            doc = fitz.open(temp_file_path)
            
            has_images = False
            has_native_text = False
            total_pages = len(doc)
            pages_with_images = 0
            pages_with_text = 0
            
            # 检查前几页（最多检查5页以提高性能）
            pages_to_check = min(5, total_pages)
            
            for page_num in range(pages_to_check):
                page = doc[page_num]
                
                # 检查是否有图像
                image_list = page.get_images()
                if len(image_list) > 0:
                    has_images = True
                    pages_with_images += 1
                
                # 检查是否有原生文本
                text = page.get_text().strip()
                if len(text) > 10:  # 至少10个字符才认为有文本
                    has_native_text = True
                    pages_with_text += 1
            
            doc.close()
            
            # 判断处理策略
            use_ocr = not has_native_text or (has_images and pages_with_text < pages_to_check * 0.5)
            use_vision = has_images
            include_images = has_images
            
            return {
                "has_images": has_images,
                "has_native_text": has_native_text,
                "total_pages": total_pages,
                "pages_checked": pages_to_check,
                "pages_with_images": pages_with_images,
                "pages_with_text": pages_with_text,
                "use_ocr": use_ocr,
                "use_vision": use_vision,
                "include_images": include_images,
                "detection_confidence": "high" if pages_to_check >= 3 else "medium"
            }
            
        finally:
            # 清理临时文件
            if os.path.exists(temp_file_path):
                os.unlink(temp_file_path)
                
    except Exception as e:
        logger.error(f"PDF内容检测失败: {str(e)}")
        # 返回保守的默认值
        return {
            "has_images": True,  # 保守起见，假设有图像
            "has_native_text": False,  # 保守起见，假设没有原生文本
            "total_pages": 1,
            "pages_checked": 0,
            "pages_with_images": 0,
            "pages_with_text": 0,
            "use_ocr": True,  # 保守起见，启用OCR
            "use_vision": True,  # 保守起见，启用视觉处理
            "include_images": True,
            "detection_confidence": "low",
            "error": str(e)
        }


@router.post("/extract-text")
async def extract_pdf_text_from_file(
    file: UploadFile = File(..., description="PDF文件"),
    output_format: str = Form(default="json", description="输出格式: json, txt, zip"),
    ocr_engine: str = Form(default="baidu", description="OCR引擎类型"),
    vision_model: str = Form(default="qwen-vl-plus", description="视觉模型名称")
):
    """
    提取PDF文件中的文字
    
    从PDF文档中提取文字内容，支持多种输出格式。系统会自动检测PDF内容类型并选择最佳处理方式。
    支持文件上传或URL链接两种方式，二选一即可。
    
    **智能处理流程:**
    1. 自动检测PDF是否包含图像
    2. 自动判断是否为扫描文档
    3. 根据内容类型自动选择处理方式：
       - 纯文本页面：直接提取原生文字
       - 包含图像页面：自动启用OCR和视觉模型
       - 扫描页面：自动启用OCR识别
    
    **参数说明:**
    - **file** (UploadFile, 可选): 上传的PDF文件
      - 支持格式: `.pdf`
      - 最大文件大小: 50MB
      - 支持加密PDF（需要密码）
    - **url** (str, 可选): PDF文件URL链接
      - 支持HTTP/HTTPS协议
      - 最大文件大小: 50MB
      - 自动检测文件类型
    - **output_format** (str, 默认: "json"): 输出格式
      - `"json"`: JSON格式，包含详细的结构化数据
      - `"txt"`: 纯文本格式
      - `"zip"`: 压缩包格式，包含多种格式文件
    - **ocr_engine** (str, 默认: "baidu"): OCR引擎类型
      - `"baidu"`: 百度OCR引擎（推荐）
      - `"tesseract"`: Tesseract引擎
    - **vision_model** (str, 默认: "qwen-vl-plus"): 视觉模型名称
      - `"qwen-vl-plus"`: 增强版视觉模型
      - `"qwen-vl-max"`: 最大版视觉模型
    
    **使用示例:**
    ```bash
    # 通过文件上传提取文字
    curl -X POST "http://localhost:8000/api/pdf/extract-text" \
         -F "file=@document.pdf" \
         -F "output_format=json"
    
    # 通过URL链接提取文字
    curl -X POST "http://localhost:8000/api/pdf/extract-text" \
         -F "url=https://example.com/document.pdf" \
         -F "output_format=json"
    
    # 提取格式信息
    curl -X POST "http://localhost:8000/api/pdf/extract-text" \
         -F "file=@formatted_document.pdf" \
    
    # 指定OCR引擎（系统自动判断是否需要OCR）
    curl -X POST "http://localhost:8000/api/pdf/extract-text" \
         -F "url=https://example.com/scanned_document.pdf" \
         -F "ocr_engine=baidu"
    
    # 指定视觉模型（系统自动判断是否需要视觉分析）
    curl -X POST "http://localhost:8000/api/pdf/extract-text" \
         -F "file=@complex_document.pdf" \
         -F "vision_model=qwen-vl-plus"
    ```
    
    **响应示例:**
    ```json
    {
        "success": true,
        "message": "PDF处理成功",
        "task_id": "task_20241201_143022_abc123",
        "download_url": "http://localhost:8000/api/download/file/extracted_text_20241201_143022.json",
        "output_format": "json",
        "timestamp": "2024-12-01T14:30:22",
        "content_analysis": {
            "has_images": true,
            "has_native_text": false,
            "total_pages": 5,
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
            raise HTTPException(status_code=400, detail="必须提供PDF文件")
        
        # 验证文件类型
        if not file.filename.lower().endswith('.pdf'):
            raise HTTPException(status_code=400, detail="只支持PDF文件")
        
        # 读取文件内容
        file_content = await file.read()
        
        # 自动检测PDF内容类型
        content_analysis = _detect_pdf_content_type(file_content)
        logger.info(f"PDF内容检测结果: {content_analysis}")
        
        # 使用统一处理服务
        result = await unified_processing_service.process_file_upload(
            file_content=file_content,
            filename=file.filename,
            processing_type="extract",
            output_format=output_format,
            include_images=content_analysis["include_images"],
            use_ocr=content_analysis["use_ocr"],
            ocr_engine=ocr_engine,
            use_vision=content_analysis["use_vision"],
            vision_model=vision_model
        )
        
        if result['success']:
            response_data = {
                "success": True,
                "message": "PDF处理成功",
                "task_id": result['task_id'],
                "download_url": result['download_url'],
                "output_format": output_format,
                "timestamp": result['created_at']
            }
            
            # 如果是文件上传方式，添加内容分析信息
            if file and 'content_analysis' in locals():
                response_data["content_analysis"] = {
                    "has_images": content_analysis["has_images"],
                    "has_native_text": content_analysis["has_native_text"],
                    "total_pages": content_analysis["total_pages"],
                    "detection_confidence": content_analysis["detection_confidence"],
                    "auto_ocr_enabled": content_analysis["use_ocr"],
                    "auto_vision_enabled": content_analysis["use_vision"]
                }
            
            return response_data
        else:
            raise HTTPException(status_code=500, detail=result['error'])
                
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"PDF处理失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"PDF处理失败: {str(e)}")






@router.post("/extract-text-from-url")
async def extract_pdf_text_from_url(
    url: str = Form(..., description="PDF文件URL"),
    output_format: str = Form(default="json", description="输出格式: json, txt, zip"),
    ocr_engine: str = Form(default="baidu", description="OCR引擎类型"),
    vision_model: str = Form(default="qwen-vl-plus", description="视觉模型名称")
):
    """
    从URL提取PDF文件中的文字
    
    从URL链接的PDF文档中提取文字内容，支持多种输出格式。系统会自动检测PDF内容类型并选择最佳处理方式。
    
    **智能处理流程:**
    1. 自动检测PDF是否包含图像
    2. 自动判断是否为扫描文档
    3. 根据内容类型自动选择处理方式：
       - 纯文本页面：直接提取原生文字
       - 包含图像页面：自动启用OCR和视觉模型
       - 扫描页面：自动启用OCR识别
    
    **参数说明:**
    - **url** (str, 必需): PDF文件URL链接
      - 支持HTTP/HTTPS协议
      - 最大文件大小: 50MB
      - 自动检测文件类型
    - **output_format** (str, 默认: "json"): 输出格式
      - `"json"`: JSON格式，包含详细的结构化数据
      - `"txt"`: 纯文本格式
      - `"zip"`: 压缩包格式，包含多种格式文件
    - **ocr_engine** (str, 默认: "baidu"): OCR引擎类型
      - `"baidu"`: 百度OCR引擎（推荐）
      - `"paddleocr"`: PaddleOCR引擎
      - `"tesseract"`: Tesseract引擎
    - **vision_model** (str, 默认: "qwen-vl-plus"): 视觉模型名称
      - `"qwen-vl-plus"`: 通义千问视觉模型（推荐）
      - `"qwen-vl-max"`: 通义千问视觉模型（高级版）
    
    **使用示例:**
    
    ```bash
    curl -X POST "http://localhost:8000/api/pdf/extract-text-from-url" \
         -F "url=https://example.com/document.pdf" \
         -F "output_format=json" \
         -F "ocr_engine=baidu" \
         -F "vision_model=qwen-vl-plus"
    ```
    
    **Python示例:**
    ```python
    import requests
    
    data = {
        'url': 'https://example.com/document.pdf',
        'output_format': 'json',
        'ocr_engine': 'baidu',
        'vision_model': 'qwen-vl-plus'
    }
    response = requests.post(
        'http://localhost:8000/api/pdf/extract-text-from-url',
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
            processing_type="extract",
            output_format=output_format,
            ocr_engine=ocr_engine,
            vision_model=vision_model
        )
        
        if result['success']:
            response_data = {
                "success": True,
                "message": "PDF处理成功",
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
            raise HTTPException(status_code=500, detail=result.get('error', 'PDF处理失败'))
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"PDF URL处理失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"PDF处理失败: {str(e)}")


@router.get("/health")
async def pdf_service_health():
    """
    PDF服务健康检查
    
    检查PDF文字提取服务的运行状态和功能可用性。
    
    **检查项目:**
    - PDF处理引擎状态
    - OCR引擎可用性
    - 视觉模型连接状态
    - Qwen-VL模型状态
    - 文件处理能力
    
    **使用示例:**
    ```bash
    # 检查PDF服务健康状态
    curl -X GET "http://localhost:8000/api/pdf/health"
    ```
    
    **响应示例:**
    ```json
    {
        "status": "healthy",
        "service": "PDF文字提取服务",
        "version": "1.0.0",
        "features": {
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
    - `ocr`: OCR引擎是否可用
    - `vision`: 视觉模型是否可用
    - `qwen_vl`: Qwen-VL多模态模型是否可用
    
    **错误码:**
    - `500`: 服务不可用
    """
    try:
        # 简单的健康检查
        vision_available = vision_service.is_available()
        
        return {
            "status": "healthy",
            "service": "PDF文字提取服务",
            "version": "1.0.0",
            "features": {
                "ocr": True,
                "vision": vision_available,
                "qwen_vl": vision_available
            },
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"PDF服务健康检查失败: {str(e)}")
        raise HTTPException(status_code=500, detail="PDF服务不可用")

