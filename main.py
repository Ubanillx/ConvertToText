from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api import api_router
from app.core.config import settings, setup_logging
from app.services.file_cleanup_service import file_cleanup_service
import logging

# 设置日志
setup_logging()
logger = logging.getLogger(__name__)

# 创建FastAPI应用实例
app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="一个工程化的FastAPI项目",
    docs_url="/docs",
    redoc_url="/redoc"
)

logger.info(f"启动 {settings.app_name} v{settings.app_version}")

# 添加CORS中间件
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 生产环境中应该指定具体的域名
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册路由
app.include_router(api_router, prefix="/api/v1")


@app.on_event("startup")
async def startup_event():
    """应用启动事件"""
    logger.info("应用启动中...")
    
    # 启动文件清理服务
    if settings.auto_cleanup_enabled:
        file_cleanup_service.start_cleanup_scheduler()
        logger.info("文件自动清理服务已启动")
    else:
        logger.info("文件自动清理服务已禁用")


@app.on_event("shutdown")
async def shutdown_event():
    """应用关闭事件"""
    logger.info("应用关闭中...")
    
    # 停止文件清理服务
    file_cleanup_service.stop_cleanup_scheduler()
    logger.info("文件清理服务已停止")


@app.get("/")
async def root():
    """根路径接口"""
    return {
        "message": f"欢迎使用 {settings.app_name}",
        "version": settings.app_version,
        "docs": "/docs",
        "apis": {
            "pdf": "/api/v1/pdf",
            "doc": "/api/v1/doc",
            "image": "/api/v1/image", 
            "ocr": "/api/v1/ocr",
            "download": "/api/v1/download",
            "cleanup": "/api/v1/cleanup"
        }
    }


if __name__ == "__main__":
    import uvicorn
    logger.info(f"启动服务器: http://{settings.host}:{settings.port}")
    uvicorn.run(
        "main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug
    )
