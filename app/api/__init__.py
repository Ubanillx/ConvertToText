# API路由模块

from fastapi import APIRouter
from . import pdf, doc, image, download, cleanup

# 创建主路由器
api_router = APIRouter()

# 包含所有子路由
api_router.include_router(pdf.router, prefix="/pdf", tags=["PDF处理"])
api_router.include_router(doc.router, prefix="/doc", tags=["DOC/DOCX处理"])
api_router.include_router(image.router, prefix="/image", tags=["图片处理"])
api_router.include_router(download.router, prefix="/download", tags=["文件下载"])
api_router.include_router(cleanup.router, prefix="/cleanup", tags=["文件清理"])
