# API路由模块

from fastapi import APIRouter
from . import pdf, doc, image, download

# 创建主路由器
api_router = APIRouter()

# 包含所有子路由
api_router.include_router(pdf.router, prefix="/pdf", tags=["PDF处理"])
api_router.include_router(doc.router, prefix="/doc", tags=["DOC/DOCX处理"])
api_router.include_router(image.router, prefix="/image", tags=["图片处理"])
api_router.include_router(download.router, prefix="/download", tags=["文件下载"])
# 文件清理功能已移除API端点暴露，仅保留内部自动清理服务
