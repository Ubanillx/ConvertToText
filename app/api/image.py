"""
图片文字提取API接口

提供图片文字提取相关的REST API端点
"""

from fastapi import APIRouter, HTTPException, UploadFile, File, Form
from fastapi.responses import JSONResponse
from typing import Optional
import logging
from datetime import datetime

from app.services.unified_processing_service import unified_processing_service
from app.services.tesseract_ocr_service import tesseract_ocr_service
from app.services.baidu_ocr_service import baidu_ocr_service

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/extract-text")
async def extract_image_text(
    file: UploadFile = File(..., description="图片文件"),
    processing_type: str = Form(default="extract", description="处理类型: extract, analyze"),
    output_format: str = Form(default="json", description="输出格式: json, txt, zip"),
    ocr_engine: str = Form(default="baidu", description="OCR引擎类型"),
    use_vision: bool = Form(False, description="是否使用Qwen-VL多模态模型"),
    vision_model: str = Form(default="qwen-vl-plus", description="视觉模型名称")
):
    """
    提取图片文件中的文字
    
    支持多种图片格式的文字提取，包括OCR识别和智能分析功能。
    
    **参数说明:**
    - **file** (UploadFile, 必需): 上传的图片文件
      - 支持格式: `.jpg`, `.jpeg`, `.png`, `.bmp`, `.tiff`, `.webp`, `.gif`
      - 最大文件大小: 10MB
    - **processing_type** (str, 默认: "extract"): 处理类型
      - `"extract"`: 仅提取文字
      - `"analyze"`: 提取文字并进行智能分析
    - **output_format** (str, 默认: "json"): 输出格式
      - `"json"`: JSON格式，包含详细的结构化数据
      - `"txt"`: 纯文本格式
      - `"zip"`: 压缩包格式，包含多种格式文件
    - **ocr_engine** (str, 默认: "baidu"): OCR引擎类型
      - `"baidu"`: 百度OCR引擎（推荐，支持中英文）
      - `"tesseract"`: Tesseract引擎
    - **use_vision** (bool, 默认: False): 是否使用Qwen-VL多模态模型
      - `True`: 使用AI视觉模型进行智能理解
      - `False`: 仅使用传统OCR识别
    - **vision_model** (str, 默认: "qwen-vl-plus"): 视觉模型名称
      - `"qwen-vl-plus"`: 增强版视觉模型
      - `"qwen-vl-max"`: 最大版视觉模型
    
    **使用示例:**
    ```bash
    # 基本文字提取
    curl -X POST "http://localhost:8000/api/image/extract-text" \
         -F "file=@document.png" \
         -F "processing_type=extract" \
         -F "output_format=json"
    
    # 使用AI视觉模型进行智能分析
    curl -X POST "http://localhost:8000/api/image/extract-text" \
         -F "file=@complex_diagram.png" \
         -F "processing_type=analyze" \
         -F "use_vision=true" \
         -F "vision_model=qwen-vl-plus"
    
    # 使用百度OCR引擎提取文字
    curl -X POST "http://localhost:8000/api/image/extract-text" \
         -F "file=@chinese_text.png" \
         -F "processing_type=extract" \
         -F "ocr_engine=baidu" \
         -F "output_format=txt"
    ```
    
    **响应示例:**
    ```json
    {
        "success": true,
        "message": "图片处理成功",
        "task_id": "task_20241201_143022_abc123",
        "download_url": "http://localhost:8000/api/download/file/extracted_text_20241201_143022.json",
        "processing_type": "extract",
        "output_format": "json",
        "timestamp": "2024-12-01T14:30:22"
    }
    ```
    
    **错误码:**
    - `400`: 不支持的文件类型或参数错误
    - `500`: 处理失败或服务器错误
    """
    try:
        # 验证文件类型
        allowed_extensions = ['.jpg', '.jpeg', '.png', '.bmp', '.tiff', '.webp', '.gif']
        if not any(file.filename.lower().endswith(ext) for ext in allowed_extensions):
            raise HTTPException(status_code=400, detail="只支持图片文件")
        
        # 读取文件内容
        file_content = await file.read()
        
        # 使用统一处理服务
        result = await unified_processing_service.process_file_upload(
            file_content=file_content,
            filename=file.filename,
            processing_type=processing_type,
            output_format=output_format,
            ocr_engine=ocr_engine,
            use_vision=use_vision,
            vision_model=vision_model
        )
        
        if result['success']:
            return {
                "success": True,
                "message": "图片处理成功",
                "task_id": result['task_id'],
                "download_url": result['download_url'],
                "processing_type": processing_type,
                "output_format": output_format,
                "timestamp": result['created_at']
            }
        else:
            raise HTTPException(status_code=500, detail=result['error'])
                
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"图片处理失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"图片处理失败: {str(e)}")




@router.get("/health")
async def image_service_health():
    """
    图片服务健康检查
    
    检查图片文字提取服务的运行状态和功能可用性，包括OCR引擎状态。
    
    **功能检查:**
    - OCR引擎状态（Tesseract和百度OCR）
    - 视觉模型可用性
    - Qwen-VL模型连接状态
    - 支持的语言列表
    
    **使用示例:**
    ```bash
    # 检查服务健康状态
    curl -X GET "http://localhost:8000/api/image/health"
    ```
    
    **响应示例:**
    ```json
    {
        "status": "healthy",
        "service": "图片文字提取服务",
        "version": "1.0.0",
        "features": {
            "ocr": true,
            "vision": true,
            "qwen_vl": true
        },
        "engines": {
            "tesseract": {
                "available": true,
                "version": "5.0.0",
                "languages": ["chi_sim", "eng", "jpn", "kor"]
            },
            "baidu": {
                "available": true,
                "version": "4.16.14",
                "methods": ["basic_general", "basic_accurate", "general", "accurate", "doc_office", "table", "handwriting", "web_image"]
            }
        },
        "timestamp": "2024-12-01T14:30:22"
    }
    ```
    
    **状态说明:**
    - `"healthy"`: 服务正常运行
    - `"unhealthy"`: 服务异常
    - `"degraded"`: 部分功能不可用
    
    **错误码:**
    - `500`: 服务不可用
    """
    try:
        # 检查OCR引擎健康状态
        tesseract_health = tesseract_ocr_service.health_check()
        baidu_health = baidu_ocr_service.health_check()
        
        # 确定整体状态
        ocr_available = tesseract_health.get('tesseract_available', False) or baidu_health.get('baidu_ocr_available', False)
        overall_status = 'healthy' if ocr_available else 'degraded'
        
        return {
            "status": overall_status,
            "service": "图片文字提取服务",
            "version": "1.0.0",
            "features": {
                "ocr": ocr_available,
                "vision": True,
                "qwen_vl": True
            },
            "engines": {
                "tesseract": {
                    "available": tesseract_health.get('tesseract_available', False),
                    "version": tesseract_health.get('version', '未知'),
                    "languages": tesseract_health.get('supported_languages', [])
                },
                "baidu": {
                    "available": baidu_health.get('baidu_ocr_available', False),
                    "version": baidu_health.get('version', '未知'),
                    "methods": ["basic_general", "basic_accurate", "general", "accurate", "doc_office", "table", "handwriting", "web_image"]
                }
            },
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"图片服务健康检查失败: {str(e)}")
        raise HTTPException(status_code=500, detail="图片服务不可用")
