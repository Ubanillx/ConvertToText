"""
文件清理管理API
提供文件清理相关的接口
"""

from fastapi import APIRouter, HTTPException, Query
from typing import Optional
import logging

from app.services.file_cleanup_service import file_cleanup_service
from app.core.config import settings

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/cleanup", tags=["文件清理"])


@router.get("/stats")
async def get_storage_stats():
    """
    获取存储统计信息
    
    Returns:
        存储统计信息，包括总大小、文件数量、各目录详情等
    """
    try:
        stats = file_cleanup_service.get_storage_stats()
        
        # 格式化时间信息
        if stats.get('oldest_file'):
            stats['oldest_file']['modified_time'] = stats['oldest_file']['modified_time'].isoformat()
        if stats.get('newest_file'):
            stats['newest_file']['modified_time'] = stats['newest_file']['modified_time'].isoformat()
        
        # 格式化各目录的时间信息
        for dir_name, dir_stats in stats.get('directories', {}).items():
            if dir_stats.get('oldest_file'):
                dir_stats['oldest_file']['modified_time'] = dir_stats['oldest_file']['modified_time'].isoformat()
            if dir_stats.get('newest_file'):
                dir_stats['newest_file']['modified_time'] = dir_stats['newest_file']['modified_time'].isoformat()
        
        return {
            "success": True,
            "data": stats,
            "config": {
                "retention_days": settings.file_retention_days,
                "cleanup_interval_hours": settings.cleanup_interval_hours,
                "auto_cleanup_enabled": settings.auto_cleanup_enabled
            }
        }
        
    except Exception as e:
        logger.error(f"获取存储统计信息失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"获取存储统计信息失败: {str(e)}")


@router.post("/manual")
async def manual_cleanup(
    retention_days: Optional[int] = Query(None, description="保留天数，不指定则使用默认配置")
):
    """
    手动执行文件清理
    
    Args:
        retention_days: 保留天数，如果不指定则使用默认值
        
    Returns:
        清理结果统计
    """
    try:
        logger.info(f"手动触发文件清理，保留天数: {retention_days or settings.file_retention_days}")
        
        result = file_cleanup_service.manual_cleanup(retention_days)
        
        return {
            "success": True,
            "message": f"清理完成，删除了{result['total_files_removed']}个文件，释放了{file_cleanup_service._format_size(result['total_size_freed'])}空间",
            "data": result
        }
        
    except Exception as e:
        logger.error(f"手动清理失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"手动清理失败: {str(e)}")


@router.get("/config")
async def get_cleanup_config():
    """
    获取清理配置信息
    
    Returns:
        当前清理配置
    """
    return {
        "success": True,
        "data": {
            "retention_days": settings.file_retention_days,
            "cleanup_interval_hours": settings.cleanup_interval_hours,
            "auto_cleanup_enabled": settings.auto_cleanup_enabled,
            "storage_path": settings.storage_path
        }
    }


@router.post("/test")
async def test_cleanup():
    """
    测试清理功能（仅清理1天前的文件）
    
    Returns:
        测试清理结果
    """
    try:
        logger.info("执行测试清理（保留1天）")
        
        result = file_cleanup_service.manual_cleanup(retention_days=1)
        
        return {
            "success": True,
            "message": f"测试清理完成，删除了{result['total_files_removed']}个文件，释放了{file_cleanup_service._format_size(result['total_size_freed'])}空间",
            "data": result
        }
        
    except Exception as e:
        logger.error(f"测试清理失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"测试清理失败: {str(e)}")
