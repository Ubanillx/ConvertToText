"""
文件清理服务
定时删除超过保留期限的文件，默认保留1周
"""

import os
import shutil
import logging
from pathlib import Path
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
import threading
import time

from app.core.config import settings

logger = logging.getLogger(__name__)


class FileCleanupService:
    """文件清理服务"""
    
    def __init__(self):
        self.base_storage_path = Path(settings.storage_path) if hasattr(settings, 'storage_path') else Path("./storage")
        # 默认保留7天，可通过配置修改
        self.retention_days = getattr(settings, 'file_retention_days', 7)
        self.cleanup_interval_hours = getattr(settings, 'cleanup_interval_hours', 24)  # 每24小时清理一次
        self.is_running = False
        self.cleanup_thread = None
        
        # 确保存储目录存在
        self.base_storage_path.mkdir(parents=True, exist_ok=True)
        
        logger.info(f"文件清理服务初始化完成，保留期限: {self.retention_days}天，清理间隔: {self.cleanup_interval_hours}小时")
    
    def start_cleanup_scheduler(self):
        """启动定时清理任务"""
        if self.is_running:
            logger.warning("文件清理服务已在运行中")
            return
        
        self.is_running = True
        self.cleanup_thread = threading.Thread(target=self._cleanup_scheduler, daemon=True)
        self.cleanup_thread.start()
        logger.info("文件清理定时任务已启动")
    
    def stop_cleanup_scheduler(self):
        """停止定时清理任务"""
        self.is_running = False
        if self.cleanup_thread and self.cleanup_thread.is_alive():
            self.cleanup_thread.join(timeout=5)
        logger.info("文件清理定时任务已停止")
    
    def _cleanup_scheduler(self):
        """清理任务调度器"""
        while self.is_running:
            try:
                logger.info("开始执行定时文件清理任务")
                cleanup_result = self.cleanup_old_files()
                logger.info(f"定时清理任务完成: {cleanup_result}")
                
                # 等待下次清理时间
                sleep_seconds = self.cleanup_interval_hours * 3600
                for _ in range(sleep_seconds):
                    if not self.is_running:
                        break
                    time.sleep(1)
                    
            except Exception as e:
                logger.error(f"定时清理任务执行失败: {str(e)}")
                # 出错后等待1小时再重试
                for _ in range(3600):
                    if not self.is_running:
                        break
                    time.sleep(1)
    
    def cleanup_old_files(self) -> Dict[str, Any]:
        """
        清理超过保留期限的文件
        
        Returns:
            清理结果统计
        """
        try:
            cutoff_time = datetime.now() - timedelta(days=self.retention_days)
            cleanup_result = {
                'cutoff_time': cutoff_time.isoformat(),
                'retention_days': self.retention_days,
                'cleaned_directories': [],
                'total_files_removed': 0,
                'total_size_freed': 0,
                'errors': []
            }
            
            # 清理各个存储目录
            directories_to_clean = [
                ('uploads', '上传文件'),
                ('results', '处理结果'),
                ('temp', '临时文件')
            ]
            
            for dir_name, description in directories_to_clean:
                try:
                    dir_result = self._cleanup_directory(
                        self.base_storage_path / dir_name, 
                        cutoff_time,
                        description
                    )
                    cleanup_result['cleaned_directories'].append(dir_result)
                    cleanup_result['total_files_removed'] += dir_result['files_removed']
                    cleanup_result['total_size_freed'] += dir_result['size_freed']
                    
                except Exception as e:
                    error_msg = f"清理{description}目录失败: {str(e)}"
                    logger.error(error_msg)
                    cleanup_result['errors'].append(error_msg)
            
            logger.info(f"文件清理完成: 删除{cleanup_result['total_files_removed']}个文件，"
                       f"释放{self._format_size(cleanup_result['total_size_freed'])}空间")
            
            return cleanup_result
            
        except Exception as e:
            logger.error(f"文件清理失败: {str(e)}")
            raise
    
    def _cleanup_directory(self, directory_path: Path, cutoff_time: datetime, description: str) -> Dict[str, Any]:
        """
        清理指定目录中的旧文件
        
        Args:
            directory_path: 目录路径
            cutoff_time: 截止时间
            description: 目录描述
            
        Returns:
            清理结果
        """
        if not directory_path.exists():
            return {
                'directory': str(directory_path),
                'description': description,
                'files_removed': 0,
                'size_freed': 0,
                'status': 'directory_not_exists'
            }
        
        files_removed = 0
        size_freed = 0
        removed_files = []
        
        try:
            # 遍历目录中的所有文件和子目录
            for item in directory_path.rglob('*'):
                if item.is_file():
                    try:
                        # 获取文件修改时间
                        file_mtime = datetime.fromtimestamp(item.stat().st_mtime)
                        
                        if file_mtime < cutoff_time:
                            file_size = item.stat().st_size
                            item.unlink()  # 删除文件
                            
                            files_removed += 1
                            size_freed += file_size
                            removed_files.append({
                                'path': str(item),
                                'size': file_size,
                                'modified_time': file_mtime.isoformat()
                            })
                            
                            logger.debug(f"删除过期文件: {item} (修改时间: {file_mtime})")
                            
                    except Exception as e:
                        logger.warning(f"删除文件失败 {item}: {str(e)}")
                
                elif item.is_dir() and item != directory_path:
                    # 检查空目录并删除
                    try:
                        if not any(item.iterdir()):
                            item.rmdir()
                            logger.debug(f"删除空目录: {item}")
                    except Exception as e:
                        logger.debug(f"删除目录失败 {item}: {str(e)}")
            
            logger.info(f"{description}目录清理完成: 删除{files_removed}个文件，"
                       f"释放{self._format_size(size_freed)}空间")
            
            return {
                'directory': str(directory_path),
                'description': description,
                'files_removed': files_removed,
                'size_freed': size_freed,
                'removed_files': removed_files,
                'status': 'success'
            }
            
        except Exception as e:
            logger.error(f"清理{description}目录失败: {str(e)}")
            return {
                'directory': str(directory_path),
                'description': description,
                'files_removed': files_removed,
                'size_freed': size_freed,
                'status': 'error',
                'error': str(e)
            }
    
    def get_storage_stats(self) -> Dict[str, Any]:
        """
        获取存储统计信息
        
        Returns:
            存储统计信息
        """
        try:
            stats = {
                'total_size': 0,
                'total_files': 0,
                'directories': {},
                'oldest_file': None,
                'newest_file': None
            }
            
            directories_to_check = ['uploads', 'results', 'temp']
            
            for dir_name in directories_to_check:
                dir_path = self.base_storage_path / dir_name
                if dir_path.exists():
                    dir_stats = self._get_directory_stats(dir_path)
                    stats['directories'][dir_name] = dir_stats
                    stats['total_size'] += dir_stats['size']
                    stats['total_files'] += dir_stats['files']
                    
                    # 更新最旧和最新文件信息
                    if dir_stats['oldest_file']:
                        if not stats['oldest_file'] or dir_stats['oldest_file']['modified_time'] < stats['oldest_file']['modified_time']:
                            stats['oldest_file'] = dir_stats['oldest_file']
                    
                    if dir_stats['newest_file']:
                        if not stats['newest_file'] or dir_stats['newest_file']['modified_time'] > stats['newest_file']['modified_time']:
                            stats['newest_file'] = dir_stats['newest_file']
            
            return stats
            
        except Exception as e:
            logger.error(f"获取存储统计信息失败: {str(e)}")
            raise
    
    def _get_directory_stats(self, directory_path: Path) -> Dict[str, Any]:
        """获取目录统计信息"""
        stats = {
            'size': 0,
            'files': 0,
            'oldest_file': None,
            'newest_file': None
        }
        
        try:
            for item in directory_path.rglob('*'):
                if item.is_file():
                    try:
                        file_size = item.stat().st_size
                        file_mtime = datetime.fromtimestamp(item.stat().st_mtime)
                        
                        stats['size'] += file_size
                        stats['files'] += 1
                        
                        file_info = {
                            'path': str(item),
                            'size': file_size,
                            'modified_time': file_mtime
                        }
                        
                        # 更新最旧文件
                        if not stats['oldest_file'] or file_mtime < stats['oldest_file']['modified_time']:
                            stats['oldest_file'] = file_info
                        
                        # 更新最新文件
                        if not stats['newest_file'] or file_mtime > stats['newest_file']['modified_time']:
                            stats['newest_file'] = file_info
                            
                    except Exception as e:
                        logger.debug(f"获取文件信息失败 {item}: {str(e)}")
                        
        except Exception as e:
            logger.error(f"获取目录统计信息失败 {directory_path}: {str(e)}")
        
        return stats
    
    def manual_cleanup(self, retention_days: Optional[int] = None) -> Dict[str, Any]:
        """
        手动执行清理任务
        
        Args:
            retention_days: 保留天数，如果不指定则使用默认值
            
        Returns:
            清理结果
        """
        if retention_days is not None:
            original_retention = self.retention_days
            self.retention_days = retention_days
            logger.info(f"临时修改保留期限为{retention_days}天")
        
        try:
            result = self.cleanup_old_files()
            return result
        finally:
            if retention_days is not None:
                self.retention_days = original_retention
                logger.info(f"恢复保留期限为{original_retention}天")
    
    def _format_size(self, size_bytes: int) -> str:
        """格式化文件大小"""
        if size_bytes == 0:
            return "0 B"
        
        size_names = ["B", "KB", "MB", "GB", "TB"]
        i = 0
        while size_bytes >= 1024 and i < len(size_names) - 1:
            size_bytes /= 1024.0
            i += 1
        
        return f"{size_bytes:.2f} {size_names[i]}"


# 创建全局实例
file_cleanup_service = FileCleanupService()
