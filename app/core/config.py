from pydantic_settings import BaseSettings
from typing import Optional
import logging
import os


class Settings(BaseSettings):
    """应用配置类"""
    
    # 应用配置
    app_name: str = "ConvertToText"
    app_version: str = "1.0.0"
    debug: bool = True
    
    # 服务器配置
    host: str = "0.0.0.0"
    port: int = 8000
    
    # 数据库配置
    database_url: str = "sqlite:///./app.db"
    
    # 安全配置
    secret_key: str = "your-secret-key-here"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    
    # 百炼平台配置
    dashscope_api_key: Optional[str] = None
    dashscope_model: str = "qwen-plus"
    dashscope_temperature: float = 0.7
    dashscope_max_tokens: int = 2000
    
    # Qwen-VL多模态模型配置
    qwen_vl_model: str = "qwen-vl-plus"
    qwen_vl_temperature: float = 0.7
    qwen_vl_max_tokens: int = 2000
    qwen_vl_enabled: bool = True
    
    # 百度OCR配置
    baidu_ocr_api_key: str = "aWctKKuuHsfsB3cecpgoZ8N6"
    baidu_ocr_secret_key: str = "ikpwppZUSggGpJOEvskp1PfDkpRjd54O"
    baidu_ocr_enabled: bool = True
    
    
    # OpenAI配置（备用）
    openai_api_key: Optional[str] = None
    openai_model: str = "gpt-3.5-turbo"
    openai_temperature: float = 0.7
    openai_max_tokens: int = 2000
    
    # 文件存储配置
    storage_path: str = "./storage"
    download_base_url: str = "http://localhost:8000/api/v1/download"
    max_file_size: int = 100 * 1024 * 1024  # 100MB
    
    # 任务管理配置
    task_cleanup_hours: int = 24  # 任务文件保留时间（小时）
    max_concurrent_tasks: int = 10  # 最大并发任务数
    
    # 文件清理配置
    file_retention_days: int = 7  # 文件保留天数（默认7天）
    cleanup_interval_hours: int = 24  # 清理任务执行间隔（小时）
    auto_cleanup_enabled: bool = True  # 是否启用自动清理
    
    # 日志配置
    log_level: str = "INFO"
    log_format: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    log_file: Optional[str] = None  # 如果为None，则只输出到控制台
    
    class Config:
        env_file = ".env"
        case_sensitive = False


# 创建全局配置实例
settings = Settings()


def setup_logging():
    """设置日志配置"""
    # 创建logs目录
    if settings.log_file:
        log_dir = os.path.dirname(settings.log_file)
        if log_dir and not os.path.exists(log_dir):
            os.makedirs(log_dir)
    
    # 配置日志
    handlers = []
    
    # 控制台处理器
    console_handler = logging.StreamHandler()
    console_handler.setLevel(getattr(logging, settings.log_level.upper()))
    console_formatter = logging.Formatter(settings.log_format)
    console_handler.setFormatter(console_formatter)
    handlers.append(console_handler)
    
    # 文件处理器（如果配置了日志文件）
    if settings.log_file:
        file_handler = logging.FileHandler(settings.log_file, encoding='utf-8')
        file_handler.setLevel(getattr(logging, settings.log_level.upper()))
        file_formatter = logging.Formatter(settings.log_format)
        file_handler.setFormatter(file_formatter)
        handlers.append(file_handler)
    
    # 配置根日志器
    logging.basicConfig(
        level=getattr(logging, settings.log_level.upper()),
        handlers=handlers,
        force=True  # 强制重新配置，覆盖之前的配置
    )
    
    # 设置第三方库的日志级别
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    logging.getLogger("urllib3").setLevel(logging.WARNING)
