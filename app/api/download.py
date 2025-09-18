# 文件下载API

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import FileResponse
from pathlib import Path
import os
import logging
from typing import Optional

router = APIRouter()
logger = logging.getLogger(__name__)

@router.get("/{task_id}/{filename}")
async def download_file_by_task_id(
    task_id: str,
    filename: str
):
    """
    通过任务ID下载处理后的文件
    
    使用任务ID和文件名下载处理结果文件，这是PDF/图片处理服务返回的标准下载方式。
    
    **参数说明:**
    - **task_id** (str): 任务ID，例如: `"d9520111-0eb6-4426-9baf-c37afc6fc501"`
    - **filename** (str): 文件名，例如: `"result_20250917_094844.json"`
    
    **支持的下载文件类型:**
    - JSON文件: `.json` - 结构化处理结果
    - 文本文件: `.txt` - 纯文本提取结果
    - 压缩文件: `.zip` - 包含多种格式的压缩包
    
    **使用示例:**
    ```bash
    # 下载JSON格式的处理结果
    curl -X GET "http://localhost:8000/api/v1/download/d9520111-0eb6-4426-9baf-c37afc6fc501/result_20250917_094844.json"
    
    # 下载文本格式的提取结果
    curl -X GET "http://localhost:8000/api/v1/download/d9520111-0eb6-4426-9baf-c37afc6fc501/extracted_text_20250917_094844.txt"
    
    # 下载压缩包格式的结果
    curl -X GET "http://localhost:8000/api/v1/download/d9520111-0eb6-4426-9baf-c37afc6fc501/result_20250917_094844.zip"
    ```
    
    **响应:**
    - 成功: 返回文件下载流
    - 失败: 返回404错误（文件未找到）或500错误（服务器错误）
    
    **错误码:**
    - `404`: 文件未找到或任务ID不存在
    - `500`: 服务器内部错误
    
    **注意事项:**
    - 文件会在处理完成后保存24小时，过期后自动删除
    - 任务ID是唯一的，确保使用正确的ID
    - 支持断点续传和分块下载
    """
    try:
        logger.info(f"开始下载文件: task_id={task_id}, filename={filename}")
        # 构建文件路径 - 使用新的存储结构
        file_path = Path("storage/results") / task_id / filename
        
        # 检查文件是否存在
        if not file_path.exists():
            # 尝试在旧的文件结构中查找
            old_paths = [
                Path("downloads/pdf") / filename,
                Path("downloads/image") / filename,
                Path("downloads/text") / filename,
                Path("storage/results") / filename
            ]
            
            file_path = None
            for old_path in old_paths:
                if old_path.exists():
                    file_path = old_path
                    break
            
            if file_path is None:
                logger.warning(f"文件未找到: task_id={task_id}, filename={filename}")
                raise HTTPException(
                    status_code=404, 
                    detail=f"文件未找到: {filename} (任务ID: {task_id})"
                )
        
        # 确定媒体类型
        media_type = 'application/octet-stream'
        if filename.endswith('.json'):
            media_type = 'application/json'
        elif filename.endswith('.txt'):
            media_type = 'text/plain'
        elif filename.endswith('.zip'):
            media_type = 'application/zip'
        elif filename.endswith('.pdf'):
            media_type = 'application/pdf'
        
        # 返回文件
        logger.info(f"成功找到文件: {file_path}")
        return FileResponse(
            path=str(file_path),
            filename=filename,
            media_type=media_type
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"下载文件时出错: task_id={task_id}, filename={filename}, error={str(e)}")
        raise HTTPException(status_code=500, detail=f"下载文件时出错: {str(e)}")


