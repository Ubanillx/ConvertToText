"""
PDF文字提取服务模块

基于PyMuPDF实现PDF文字提取功能，支持：
1. 原生文本提取
2. 扫描件检测
3. 图文混合文档处理
4. 结构化输出
"""

import fitz  # PyMuPDF
from typing import List, Dict, Any, Optional, Tuple
import logging
from pathlib import Path
import asyncio
import concurrent.futures
from threading import Thread
from .tesseract_ocr_service import tesseract_ocr_service
from .baidu_ocr_service import baidu_ocr_service
from ..schemas.ocr_schemas import OCREngineType
from .vision_service import vision_service

logger = logging.getLogger(__name__)


class PDFTextExtractor:
    """PDF文字提取器"""
    
    def __init__(self):
        """初始化PDF提取器"""
        self.min_text_length = 10  # 最小文本长度阈值，用于判断是否为扫描页
        
    def extract_text_from_pdf(self, pdf_path: str, use_ocr: bool = False, ocr_engine: OCREngineType = OCREngineType.BAIDU, use_vision: bool = False, vision_model: str = "qwen-vl-plus") -> Dict[str, Any]:
        """
        从PDF文件中提取文字 - 实现四步法处理流程
        
        步骤1: 逐页检测内容类型（是否有文本层？）
        步骤2: 有文本 → 提取原生文字
        步骤3: 无文本或含图 → 进入图像处理通道
        步骤4: 并行双轨处理（OCR + Qwen-VL多模态模型）
        
        Args:
            pdf_path: PDF文件路径
            use_ocr: 是否对扫描页面使用OCR
            ocr_engine: OCR引擎类型
            use_vision: 是否使用Qwen-VL多模态模型
            vision_model: 视觉模型名称
            
        Returns:
            包含提取结果的字典
        """
        try:
            # 打开PDF文档
            doc = fitz.open(pdf_path)
            
            result = {
                "file_path": pdf_path,
                "total_pages": len(doc),
                "pages": [],
                "full_text": "",
                "has_text_layer": False,
                "is_scanned": False,
                "extraction_method": "four_step_process",
                "processing_stats": {
                    "native_text_pages": 0,
                    "ocr_processed_pages": 0,
                    "image_only_pages": 0,
                    "mixed_content_pages": 0
                }
            }
            
            all_text = []
            
            # 步骤1: 逐页检测内容类型
            for page_num in range(len(doc)):
                page = doc[page_num]
                page_result = self._process_page_four_step(page, page_num, pdf_path, use_ocr, ocr_engine, use_vision, vision_model)
                
                result["pages"].append(page_result)
                all_text.append(page_result["text"])
                
                # 统计处理方式
                if page_result["processing_type"] == "native_text":
                    result["processing_stats"]["native_text_pages"] += 1
                    result["has_text_layer"] = True
                elif page_result["processing_type"] == "ocr_processed":
                    result["processing_stats"]["ocr_processed_pages"] += 1
                elif page_result["processing_type"] == "image_only":
                    result["processing_stats"]["image_only_pages"] += 1
                elif page_result["processing_type"] == "mixed_content":
                    result["processing_stats"]["mixed_content_pages"] += 1
                    result["has_text_layer"] = True
            
            # 合并所有页面文本
            result["full_text"] = "\n\n".join(all_text)
            
            # 判断是否为扫描文档
            if result["processing_stats"]["native_text_pages"] == 0:
                result["is_scanned"] = True
                logger.warning(f"PDF为扫描文档，所有页面均使用OCR处理: {pdf_path}")
            
            doc.close()
            return result
            
        except Exception as e:
            logger.error(f"PDF文字提取失败: {pdf_path}, 错误: {str(e)}")
            raise Exception(f"PDF文字提取失败: {str(e)}")
    
    def _process_page_four_step(self, page: fitz.Page, page_num: int, pdf_path: str, 
                               use_ocr: bool, ocr_engine: OCREngineType, use_vision: bool = False, vision_model: str = "qwen-vl-plus") -> Dict[str, Any]:
        """
        四步法处理单页内容
        
        步骤1: 检测内容类型（是否有文本层？）
        步骤2: 有文本 → 提取原生文字
        步骤3: 无文本或含图 → 进入图像处理通道
        步骤4: 并行双轨处理（OCR + Qwen-VL多模态模型）
        
        Args:
            page: PyMuPDF页面对象
            page_num: 页码（从0开始）
            pdf_path: PDF文件路径
            use_ocr: 是否使用OCR
            ocr_engine: OCR引擎类型
            use_vision: 是否使用Qwen-VL多模态模型
            vision_model: 视觉模型名称
            
        Returns:
            页面处理结果
        """
        try:
            # 步骤1: 检测内容类型
            content_analysis = self._analyze_page_content(page)
            
            # 获取页面基本信息
            page_info = {
                "page_number": page_num + 1,
                "width": page.rect.width,
                "height": page.rect.height,
                "rotation": page.rotation
            }
            
            # 根据内容类型选择处理方式
            if content_analysis["has_native_text"] and not content_analysis["has_images"]:
                # 步骤2: 纯文本页面 - 提取原生文字
                return self._extract_native_text_only(page, page_num, page_info, content_analysis)
                
            elif content_analysis["has_native_text"] and content_analysis["has_images"]:
                # 混合内容页面 - 原生文字 + 图像处理
                return self._extract_mixed_content(page, page_num, page_info, content_analysis, 
                                                 pdf_path, use_ocr, ocr_engine, use_vision, vision_model)
                
            elif not content_analysis["has_native_text"] and content_analysis["has_images"]:
                # 步骤3: 纯图像页面 - 进入图像处理通道
                return self._process_image_only_page(page, page_num, page_info, content_analysis,
                                                   pdf_path, use_ocr, ocr_engine, use_vision, vision_model)
                
            else:
                # 空白页面
                return self._create_empty_page_result(page_num, page_info)
                
        except Exception as e:
            logger.error(f"页面 {page_num + 1} 四步法处理失败: {str(e)}")
            return self._create_error_page_result(page_num, str(e))
    
    def _analyze_page_content(self, page: fitz.Page) -> Dict[str, Any]:
        """
        分析页面内容类型
        
        Args:
            page: PyMuPDF页面对象
            
        Returns:
            内容分析结果
        """
        try:
            # 获取原生文本
            native_text = page.get_text().strip()
            has_native_text = len(native_text) > self.min_text_length
            
            # 获取图像信息
            image_list = page.get_images()
            has_images = len(image_list) > 0
            
            # 获取文本块信息
            text_blocks = page.get_text("dict")
            structured_blocks = self._analyze_text_blocks(text_blocks)
            
            # 分析文本块结构
            text_blocks_count = len([b for b in structured_blocks if b["type"] == "text"])
            image_blocks_count = len([b for b in structured_blocks if b["type"] == "image"])
            
            return {
                "has_native_text": has_native_text,
                "has_images": has_images,
                "native_text_length": len(native_text),
                "images_count": len(image_list),
                "text_blocks_count": text_blocks_count,
                "image_blocks_count": image_blocks_count,
                "content_type": self._determine_content_type(has_native_text, has_images, len(native_text))
            }
            
        except Exception as e:
            logger.error(f"页面内容分析失败: {str(e)}")
            return {
                "has_native_text": False,
                "has_images": False,
                "native_text_length": 0,
                "images_count": 0,
                "text_blocks_count": 0,
                "image_blocks_count": 0,
                "content_type": "unknown",
                "error": str(e)
            }
    
    def _determine_content_type(self, has_native_text: bool, has_images: bool, text_length: int) -> str:
        """
        确定页面内容类型
        
        Args:
            has_native_text: 是否有原生文本
            has_images: 是否有图像
            text_length: 文本长度
            
        Returns:
            内容类型
        """
        if has_native_text and not has_images:
            return "native_text_only"
        elif has_native_text and has_images:
            return "mixed_content"
        elif not has_native_text and has_images:
            return "image_only"
        else:
            return "empty"
    
    def _extract_native_text_only(self, page: fitz.Page, page_num: int, page_info: Dict, 
                                 content_analysis: Dict) -> Dict[str, Any]:
        """
        步骤2: 提取纯文本页面的原生文字
        
        Args:
            page: PyMuPDF页面对象
            page_num: 页码
            page_info: 页面基本信息
            content_analysis: 内容分析结果
            
        Returns:
            提取结果
        """
        try:
            # 提取原生文本
            text = page.get_text()
            
            return {
                "page_number": page_num + 1,
                "text": text,
                "text_length": len(text.strip()),
                "processing_type": "native_text",
                "extraction_method": "native_text_extraction",
                "has_images": False
            }
            
        except Exception as e:
            logger.error(f"原生文本提取失败: {str(e)}")
            return self._create_error_page_result(page_num, str(e))
    
    def _extract_mixed_content(self, page: fitz.Page, page_num: int, page_info: Dict,
                              content_analysis: Dict, pdf_path: str, use_ocr: bool, 
                              ocr_engine: OCREngineType, use_vision: bool = False, vision_model: str = "qwen-vl-plus") -> Dict[str, Any]:
        """
        处理混合内容页面（原生文字 + 图像）
        
        Args:
            page: PyMuPDF页面对象
            page_num: 页码
            page_info: 页面基本信息
            content_analysis: 内容分析结果
            pdf_path: PDF文件路径
            use_ocr: 是否使用OCR
            ocr_engine: OCR引擎类型
            use_vision: 是否使用Qwen-VL多模态模型
            vision_model: 视觉模型名称
            
        Returns:
            处理结果
        """
        try:
            # 提取原生文本
            text = page.get_text()
            
            # 获取图像信息
            image_list = page.get_images()
            ocr_texts = []
            
            for img_index, img in enumerate(image_list):
                # 如果启用OCR，对图像进行文字识别
                if use_ocr:
                    try:
                        # 提取单个图像进行OCR
                        ocr_result = self._extract_text_from_image_in_page(page, img_index, ocr_engine)
                        if ocr_result["text"].strip():
                            ocr_texts.append(ocr_result["text"])
                            logger.info(f"第{page_num + 1}页图像{img_index + 1}OCR识别成功")
                    except Exception as e:
                        logger.warning(f"第{page_num + 1}页图像{img_index + 1}OCR识别失败: {str(e)}")
                
                # 如果启用Qwen-VL，对图像进行多模态识别
                if use_vision and vision_service.is_available():
                    try:
                        # 提取单个图像进行Qwen-VL识别
                        vision_result = self._extract_text_from_image_with_vision(page, img_index, vision_model)
                        if vision_result["success"] and vision_result["text"].strip():
                            # 与OCR结果进行融合
                            if ocr_texts and img_index < len(ocr_texts):
                                fused_text = self._fuse_ocr_and_vision_results(ocr_texts[img_index], vision_result["text"])
                                ocr_texts[img_index] = fused_text
                            else:
                                ocr_texts.append(vision_result["text"])
                            logger.info(f"第{page_num + 1}页图像{img_index + 1}Qwen-VL识别成功")
                    except Exception as e:
                        logger.warning(f"第{page_num + 1}页图像{img_index + 1}Qwen-VL识别失败: {str(e)}")
            
            # 合并原生文本和OCR文本
            combined_text = text
            if ocr_texts:
                combined_text += "\n\n[图像文字识别结果]\n" + "\n".join(ocr_texts)
            
            # 应用用户友好的文本格式化
            formatted_text = self._format_user_friendly_text(combined_text)
            
            return {
                "page_number": page_num + 1,
                "text": formatted_text,
                "text_length": len(formatted_text.strip()),
                "images_count": len(image_list),
                "processing_type": "mixed_content",
                "extraction_method": "native_text_with_ocr",
                "has_images": True,
                "ocr_texts": ocr_texts
            }
            
        except Exception as e:
            logger.error(f"混合内容处理失败: {str(e)}")
            return self._create_error_page_result(page_num, str(e))
    
    def _process_image_only_page(self, page: fitz.Page, page_num: int, page_info: Dict,
                                content_analysis: Dict, pdf_path: str, use_ocr: bool,
                                ocr_engine: OCREngineType, use_vision: bool = False, vision_model: str = "qwen-vl-plus") -> Dict[str, Any]:
        """
        步骤3: 处理纯图像页面 - 进入图像处理通道
        
        Args:
            page: PyMuPDF页面对象
            page_num: 页码
            page_info: 页面基本信息
            content_analysis: 内容分析结果
            pdf_path: PDF文件路径
            use_ocr: 是否使用OCR
            ocr_engine: OCR引擎类型
            use_vision: 是否使用Qwen-VL多模态模型
            vision_model: 视觉模型名称
            
        Returns:
            处理结果
        """
        try:
            # 获取图像信息
            image_list = page.get_images()
            images_info = []
            
            for img_index, img in enumerate(image_list):
                # 处理colorspace字段，确保它是整数
                colorspace = img[5]
                if isinstance(colorspace, str):
                    # 将字符串colorspace映射为整数
                    colorspace_map = {
                        "DeviceGray": 1,
                        "DeviceRGB": 3,
                        "DeviceCMYK": 4,
                        "CalGray": 1,
                        "CalRGB": 3,
                        "Lab": 3,
                        "ICCBased": 3,
                        "Indexed": 1,
                        "Separation": 1,
                        "DeviceN": 4
                    }
                    colorspace = colorspace_map.get(colorspace, 3)  # 默认为RGB
                elif not isinstance(colorspace, int):
                    colorspace = 3  # 默认为RGB
                
                images_info.append({
                    "index": img_index,
                    "xref": img[0],
                    "smask": img[1],
                    "width": img[2],
                    "height": img[3],
                    "bpc": img[4],
                    "colorspace": colorspace,
                    "alt": img[6],
                    "name": img[7]
                })
            
            text = ""
            extraction_method = "image_only_no_ocr"
            processing_type = "image_only"
            
            # 步骤4: 并行双轨处理（OCR + Qwen-VL多模态模型）
            ocr_result = None
            vision_result = None
            
            logger.info(f"第{page_num + 1}页开始图像处理: use_ocr={use_ocr}, use_vision={use_vision}")
            
            # 使用线程池进行真正的并行处理
            with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
                futures = {}
                
                # 启动OCR处理任务
                if use_ocr:
                    logger.info(f"第{page_num + 1}页启动OCR处理任务")
                    ocr_future = executor.submit(
                        self._process_page_with_ocr, 
                        pdf_path, page_num, ocr_engine
                    )
                    futures['ocr'] = ocr_future
                else:
                    logger.info(f"第{page_num + 1}页OCR未启用")
                
                # 启动Qwen-VL处理任务
                if use_vision and vision_service.is_available():
                    logger.info(f"第{page_num + 1}页启动Qwen-VL处理任务")
                    vision_future = executor.submit(
                        self._process_page_with_vision, 
                        page, page_num, vision_model
                    )
                    futures['vision'] = vision_future
                else:
                    if not use_vision:
                        logger.info(f"第{page_num + 1}页Qwen-VL未启用")
                    else:
                        logger.warning(f"第{page_num + 1}页Qwen-VL服务不可用")
                
                # 等待所有任务完成
                for task_name, future in futures.items():
                    try:
                        if task_name == 'ocr':
                            ocr_result = future.result(timeout=30)  # 30秒超时
                            logger.info(f"第{page_num + 1}页OCR处理完成: {ocr_result.get('success', False)}")
                        elif task_name == 'vision':
                            vision_result = future.result(timeout=60)  # 60秒超时
                            logger.info(f"第{page_num + 1}页Qwen-VL处理完成: {vision_result.get('success', False)}")
                    except concurrent.futures.TimeoutError:
                        logger.warning(f"第{page_num + 1}页{task_name}处理超时")
                    except Exception as e:
                        logger.error(f"第{page_num + 1}页{task_name}处理异常: {str(e)}")
            
            # 融合决策模块：择优/纠错/补全
            text, extraction_method, processing_type = self._fusion_decision_module(
                ocr_result, vision_result, page_num
            )
            
            # 兼容性：保留原有的大模型处理接口
            llm_result = self._process_with_llm_placeholder(page, page_num, pdf_path)
            if llm_result:
                # 如果大模型有结果，可以与OCR结果进行融合
                text = self._fuse_ocr_and_llm_results(text, llm_result)
                extraction_method = "ocr_llm_fusion"
            
            # 应用用户友好的文本格式化
            formatted_text = self._format_user_friendly_text(text)
            
            return {
                "page_number": page_num + 1,
                "text": formatted_text,
                "text_length": len(formatted_text.strip()),
                "images_count": len(image_list),
                "processing_type": processing_type,
                "extraction_method": extraction_method,
                "has_images": True,
                "ocr_confidence": ocr_result.get("average_confidence", 0) if use_ocr and 'ocr_result' in locals() else 0
            }
            
        except Exception as e:
            logger.error(f"图像页面处理失败: {str(e)}")
            return self._create_error_page_result(page_num, str(e))
    
    def _extract_text_from_image_in_page(self, page: fitz.Page, img_index: int, 
                                        ocr_engine: OCREngineType) -> Dict[str, Any]:
        """
        从页面中的单个图像提取文字
        
        Args:
            page: PyMuPDF页面对象
            img_index: 图像索引
            ocr_engine: OCR引擎类型
            
        Returns:
            OCR识别结果
        """
        try:
            # 获取图像列表
            image_list = page.get_images()
            if img_index >= len(image_list):
                raise ValueError(f"图像索引超出范围: {img_index}")
            
            # 获取图像
            img = image_list[img_index]
            xref = img[0]
            
            # 提取图像数据
            base_image = page.parent.extract_image(xref)
            image_bytes = base_image["image"]
            
            # 转换为PIL图像
            from PIL import Image
            from io import BytesIO
            img_pil = Image.open(BytesIO(image_bytes))
            
            # 进行OCR识别
            if ocr_engine == OCREngineType.TESSERACT:
                result = tesseract_ocr_service.extract_text(img_pil)
            elif ocr_engine == OCREngineType.BAIDU:
                result = baidu_ocr_service.extract_text(img_pil)
            else:
                raise ValueError(f"不支持的OCR引擎: {ocr_engine}")
            return result
            
        except Exception as e:
            logger.error(f"图像OCR识别失败: {str(e)}")
            return {"text": "", "error": str(e)}
    
    def _extract_text_from_image_with_vision(self, page: fitz.Page, img_index: int, 
                                           vision_model: str) -> Dict[str, Any]:
        """
        使用Qwen-VL从页面中的单个图像提取文字
        
        Args:
            page: PyMuPDF页面对象
            img_index: 图像索引
            vision_model: 视觉模型名称
            
        Returns:
            Qwen-VL识别结果
        """
        try:
            # 获取图像列表
            image_list = page.get_images()
            if img_index >= len(image_list):
                raise ValueError(f"图像索引超出范围: {img_index}")
            
            # 获取图像
            img = image_list[img_index]
            xref = img[0]
            
            # 提取图像数据
            base_image = page.parent.extract_image(xref)
            image_bytes = base_image["image"]
            
            # 使用Qwen-VL进行识别
            result = vision_service.extract_text_from_image(image_bytes, vision_model)
            return result
            
        except Exception as e:
            logger.error(f"图像Qwen-VL识别失败: {str(e)}")
            return {"text": "", "error": str(e), "success": False}
    
    def _process_page_with_ocr(self, pdf_path: str, page_num: int, 
                              ocr_engine: OCREngineType) -> Dict[str, Any]:
        """
        使用OCR处理PDF页面
        
        Args:
            pdf_path: PDF文件路径
            page_num: 页码
            ocr_engine: OCR引擎类型
            
        Returns:
            OCR处理结果
        """
        try:
            logger.info(f"第{page_num + 1}页开始OCR处理，引擎: {ocr_engine.value}")
            
            # 使用OCR服务处理页面
            if ocr_engine == OCREngineType.TESSERACT:
                result = tesseract_ocr_service.extract_text_from_pdf_page(pdf_path, page_num)
            elif ocr_engine == OCREngineType.BAIDU:
                # 百度OCR需要先将PDF页面转换为图片
                import fitz
                doc = fitz.open(pdf_path)
                page = doc[page_num]
                mat = fitz.Matrix(1.5, 1.5)
                pix = page.get_pixmap(matrix=mat, alpha=False)
                img_data = pix.tobytes("png")
                from PIL import Image
                from io import BytesIO
                img = Image.open(BytesIO(img_data))
                result = baidu_ocr_service.extract_text(img)
                result['page_number'] = page_num + 1
                result['pdf_path'] = pdf_path
                doc.close()
            else:
                raise ValueError(f"不支持的OCR引擎: {ocr_engine}")
            
            logger.info(f"第{page_num + 1}页OCR原始结果: success={result.get('success', False)}, text_length={len(result.get('text', ''))}")
            
            # 标准化结果格式
            if result and result.get("success", False) and result.get("text", "").strip():
                return {
                    "text": result["text"],
                    "success": True,
                    "confidence": result.get("average_confidence", 0.8),
                    "engine": ocr_engine.value,
                    "method": "ocr"
                }
            elif result and "error" in result:
                logger.warning(f"第{page_num + 1}页OCR处理失败: {result['error']}")
                return {
                    "text": "",
                    "error": result["error"],
                    "success": False,
                    "method": "ocr"
                }
            else:
                logger.warning(f"第{page_num + 1}页OCR识别结果为空或失败")
                return {
                    "text": "",
                    "error": "OCR识别结果为空或失败",
                    "success": False,
                    "method": "ocr"
                }
                
        except Exception as e:
            logger.error(f"第{page_num + 1}页OCR处理异常: {str(e)}")
            return {
                "text": "",
                "error": str(e),
                "success": False,
                "method": "ocr"
            }
    
    def _process_page_with_vision(self, page: fitz.Page, page_num: int, 
                                 vision_model: str) -> Dict[str, Any]:
        """
        使用Qwen-VL处理整个页面
        
        Args:
            page: PyMuPDF页面对象
            page_num: 页码
            vision_model: 视觉模型名称
            
        Returns:
            Qwen-VL处理结果
        """
        pix = None
        try:
            import gc  # 垃圾回收
            
            logger.info(f"第{page_num + 1}页开始Qwen-VL处理，模型: {vision_model}")
            
            # 将页面转换为图像 - 使用更保守的设置避免内存问题
            mat = fitz.Matrix(1.5, 1.5)  # 降低缩放比例，减少内存使用
            pix = page.get_pixmap(matrix=mat, alpha=False)  # 禁用alpha通道
            img_data = pix.tobytes("png")
            
            # 立即释放pixmap对象
            pix = None
            
            # 强制垃圾回收
            gc.collect()
            
            logger.info(f"第{page_num + 1}页图像转换完成，大小: {len(img_data)} bytes")
            
            # 使用Qwen-VL进行识别
            result = vision_service.extract_text_from_image(img_data, vision_model)
            
            logger.info(f"第{page_num + 1}页Qwen-VL原始结果: success={result.get('success', False)}, text_length={len(result.get('text', ''))}")
            
            # 标准化结果格式
            if result.get("success", False) and result.get("text", "").strip():
                return {
                    "text": result["text"],
                    "success": True,
                    "confidence": result.get("confidence", 0.9),
                    "model": vision_model,
                    "method": "vision"
                }
            else:
                error_msg = result.get("error", "Qwen-VL识别失败")
                logger.warning(f"第{page_num + 1}页Qwen-VL处理失败: {error_msg}")
                return {
                    "text": "",
                    "error": error_msg,
                    "success": False,
                    "method": "vision"
                }
            
        except Exception as e:
            logger.error(f"第{page_num + 1}页Qwen-VL处理异常: {str(e)}")
            return {
                "text": "",
                "error": str(e),
                "success": False,
                "method": "vision"
            }
        finally:
            # 确保资源被正确释放
            try:
                if pix is not None:
                    pix = None
                import gc
                gc.collect()
            except:
                pass
    
    def _fusion_decision_module(self, ocr_result: Optional[Dict], vision_result: Optional[Dict], 
                               page_num: int) -> Tuple[str, str, str]:
        """
        融合决策模块：择优/纠错/补全
        
        Args:
            ocr_result: OCR处理结果
            vision_result: Qwen-VL处理结果
            page_num: 页码
            
        Returns:
            (最终文本, 提取方法, 处理类型)
        """
        try:
            # 获取结果状态
            ocr_success = ocr_result and ocr_result.get("success", False)
            vision_success = vision_result and vision_result.get("success", False)
            
            ocr_text = ocr_result.get("text", "").strip() if ocr_result else ""
            vision_text = vision_result.get("text", "").strip() if vision_result else ""
            
            ocr_confidence = ocr_result.get("confidence", 0) if ocr_result else 0
            vision_confidence = vision_result.get("confidence", 0) if vision_result else 0
            
            logger.info(f"第{page_num + 1}页融合决策: OCR成功={ocr_success}, Vision成功={vision_success}")
            logger.info(f"第{page_num + 1}页文本长度: OCR={len(ocr_text)}, Vision={len(vision_text)}")
            
            # 决策逻辑
            if ocr_success and vision_success:
                # 两者都成功：智能融合
                logger.info(f"第{page_num + 1}页两者都成功，进行智能融合")
                return self._intelligent_fusion(ocr_text, vision_text, ocr_confidence, vision_confidence, page_num)
            elif ocr_success and not vision_success:
                # 仅OCR成功
                logger.info(f"第{page_num + 1}页使用OCR结果")
                return ocr_text, "ocr_only", "ocr_processed"
            elif not ocr_success and vision_success:
                # 仅Qwen-VL成功
                logger.info(f"第{page_num + 1}页使用Qwen-VL结果")
                return vision_text, "vision_only", "vision_processed"
            else:
                # 两者都失败 - 返回空字符串，让上层过滤机制处理
                ocr_error = ocr_result.get('error', '未执行') if ocr_result else '未执行'
                vision_error = vision_result.get('error', '未执行') if vision_result else '未执行'
                logger.warning(f"第{page_num + 1}页OCR和Qwen-VL都失败 - OCR: {ocr_error}, Vision: {vision_error}")
                return "", "both_failed", "error"
                
        except Exception as e:
            logger.error(f"融合决策模块失败: {str(e)}")
            return "", "fusion_error", "error"
    
    def _intelligent_fusion(self, ocr_text: str, vision_text: str, 
                           ocr_confidence: float, vision_confidence: float, 
                           page_num: int) -> Tuple[str, str, str]:
        """
        智能融合策略
        
        Args:
            ocr_text: OCR识别文本
            vision_text: Qwen-VL识别文本
            ocr_confidence: OCR置信度
            vision_confidence: Qwen-VL置信度
            page_num: 页码
            
        Returns:
            (融合文本, 提取方法, 处理类型)
        """
        try:
            # 计算文本质量指标
            ocr_length = len(ocr_text)
            vision_length = len(vision_text)
            
            # 置信度权重
            confidence_weight = 0.4
            length_weight = 0.3
            quality_weight = 0.3
            
            # 计算综合得分
            ocr_score = (ocr_confidence * confidence_weight + 
                        min(ocr_length / 100, 1.0) * length_weight + 
                        self._calculate_text_quality(ocr_text) * quality_weight)
            
            vision_score = (vision_confidence * confidence_weight + 
                           min(vision_length / 100, 1.0) * length_weight + 
                           self._calculate_text_quality(vision_text) * quality_weight)
            
            # 决策策略
            if abs(ocr_score - vision_score) < 0.1:
                # 得分相近：合并结果
                logger.info(f"第{page_num + 1}页OCR和Qwen-VL得分相近，进行合并")
                merged_text = self._merge_texts(ocr_text, vision_text)
                return merged_text, "intelligent_merge", "ocr_vision_fusion"
            elif ocr_score > vision_score:
                # OCR得分更高：以OCR为主，Qwen-VL补充
                logger.info(f"第{page_num + 1}页OCR得分更高，以OCR为主")
                enhanced_text = self._enhance_with_vision(ocr_text, vision_text)
                return enhanced_text, "ocr_enhanced", "ocr_vision_fusion"
            else:
                # Qwen-VL得分更高：以Qwen-VL为主，OCR补充
                logger.info(f"第{page_num + 1}页Qwen-VL得分更高，以Qwen-VL为主")
                enhanced_text = self._enhance_with_ocr(vision_text, ocr_text)
                return enhanced_text, "vision_enhanced", "ocr_vision_fusion"
                
        except Exception as e:
            logger.error(f"智能融合失败: {str(e)}")
            # 降级到简单合并
            return f"{ocr_text}\n\n[Qwen-VL补充]\n{vision_text}", "simple_merge", "ocr_vision_fusion"
    
    def _calculate_text_quality(self, text: str) -> float:
        """
        计算文本质量得分
        
        Args:
            text: 输入文本
            
        Returns:
            质量得分 (0-1)
        """
        try:
            if not text.strip():
                return 0.0
            
            # 基础指标
            length_score = min(len(text) / 200, 1.0)  # 长度得分
            
            # 字符多样性
            unique_chars = len(set(text))
            diversity_score = min(unique_chars / 50, 1.0)
            
            # 中文字符比例（中文文档质量指标）
            chinese_chars = sum(1 for char in text if '\u4e00' <= char <= '\u9fff')
            chinese_ratio = chinese_chars / len(text) if text else 0
            chinese_score = min(chinese_ratio * 2, 1.0)  # 中文比例得分
            
            # 数字和标点符号（结构化内容指标）
            digit_punct_count = sum(1 for char in text if char.isdigit() or char in '.,;:!?()[]{}')
            structure_score = min(digit_punct_count / 20, 1.0)
            
            # 综合得分
            quality_score = (length_score * 0.3 + 
                           diversity_score * 0.2 + 
                           chinese_score * 0.3 + 
                           structure_score * 0.2)
            
            return min(quality_score, 1.0)
            
        except Exception as e:
            logger.error(f"文本质量计算失败: {str(e)}")
            return 0.5  # 默认中等质量
    
    def _merge_texts(self, ocr_text: str, vision_text: str) -> str:
        """
        合并两个文本结果
        
        Args:
            ocr_text: OCR文本
            vision_text: Qwen-VL文本
            
        Returns:
            合并后的文本
        """
        try:
            # 简单的合并策略：去重并保持顺序
            lines_ocr = [line.strip() for line in ocr_text.split('\n') if line.strip()]
            lines_vision = [line.strip() for line in vision_text.split('\n') if line.strip()]
            
            # 合并并去重
            merged_lines = []
            seen = set()
            
            for line in lines_ocr + lines_vision:
                if line not in seen:
                    merged_lines.append(line)
                    seen.add(line)
            
            return '\n'.join(merged_lines)
            
        except Exception as e:
            logger.error(f"文本合并失败: {str(e)}")
            return f"{ocr_text}\n\n{vision_text}"
    
    def _enhance_with_vision(self, ocr_text: str, vision_text: str) -> str:
        """
        以OCR为主，用Qwen-VL增强
        
        Args:
            ocr_text: 主要文本（OCR）
            vision_text: 增强文本（Qwen-VL）
            
        Returns:
            增强后的文本
        """
        try:
            # 如果OCR文本已经很完整，直接返回
            if len(ocr_text) > len(vision_text) * 1.5:
                return ocr_text
            
            # 否则进行补充
            return f"{ocr_text}\n\n[Qwen-VL补充信息]\n{vision_text}"
            
        except Exception as e:
            logger.error(f"OCR增强失败: {str(e)}")
            return ocr_text
    
    def _enhance_with_ocr(self, vision_text: str, ocr_text: str) -> str:
        """
        以Qwen-VL为主，用OCR增强
        
        Args:
            vision_text: 主要文本（Qwen-VL）
            ocr_text: 增强文本（OCR）
            
        Returns:
            增强后的文本
        """
        try:
            # 如果Qwen-VL文本已经很完整，直接返回
            if len(vision_text) > len(ocr_text) * 1.5:
                return vision_text
            
            # 否则进行补充
            return f"{vision_text}\n\n[OCR补充信息]\n{ocr_text}"
            
        except Exception as e:
            logger.error(f"Qwen-VL增强失败: {str(e)}")
            return vision_text
    
    def _format_user_friendly_text(self, text: str) -> str:
        """
        格式化用户友好的文本，过滤技术细节和失败信息
        
        Args:
            text: 原始文本
            
        Returns:
            格式化后的用户友好文本
        """
        try:
            if not text or not text.strip():
                return ""
            
            # 过滤失败信息和技术细节
            failure_patterns = [
                r'\[处理失败\].*',
                r'\[融合决策失败\].*',
                r'\[.*处理失败.*\].*',
                r'OCR:.*未执行.*',
                r'Qwen-VL:.*未执行.*',
                r'\[.*识别结果.*\].*',
                r'\[.*补充信息.*\].*',
                r'\[.*增强结果.*\].*',
                r'\[.*识别失败.*\].*',
                r'\[.*处理异常.*\].*'
            ]
            
            import re
            filtered_text = text
            for pattern in failure_patterns:
                filtered_text = re.sub(pattern, '', filtered_text, flags=re.IGNORECASE)
            
            # 清理多余的空行和换行符
            lines = [line.strip() for line in filtered_text.split('\n') if line.strip()]
            
            # 过滤无意义的文本
            meaningful_lines = []
            for line in lines:
                # 过滤过短的文本
                if len(line) < 3:
                    continue
                
                # 过滤纯数字或纯符号
                if re.match(r'^[\d\s\-_\.]+$', line):
                    continue
                
                # 过滤重复的文本（如"奖牌"重复很多次）
                if len(set(line.split())) == 1 and len(line.split()) > 2:
                    continue
                
                # 过滤"图中没有可见文字"等无意义内容
                if any(phrase in line for phrase in ['图中没有可见文字', '无', '图中所有可见文字：', '图中所有文字：']):
                    continue
                
                meaningful_lines.append(line)
            
            # 去重并保持顺序
            seen = set()
            unique_lines = []
            for line in meaningful_lines:
                if line not in seen:
                    unique_lines.append(line)
                    seen.add(line)
            
            return '\n'.join(unique_lines)
            
        except Exception as e:
            logger.error(f"文本格式化失败: {str(e)}")
            return text
    
    def _fuse_ocr_and_vision_results(self, ocr_text: str, vision_text: str) -> str:
        """
        融合OCR和Qwen-VL结果（兼容性方法）
        
        Args:
            ocr_text: OCR识别文本
            vision_text: Qwen-VL识别文本
            
        Returns:
            融合后的文本
        """
        try:
            # 简单的融合策略：如果OCR结果为空或很短，优先使用Qwen-VL结果
            if not ocr_text.strip() or len(ocr_text.strip()) < 10:
                return f"[Qwen-VL识别结果]\n{vision_text}"
            
            # 如果Qwen-VL结果为空，使用OCR结果
            if not vision_text.strip():
                return f"[OCR识别结果]\n{ocr_text}"
            
            # 如果两者都有结果，进行智能融合
            # 这里可以实现更复杂的融合逻辑，比如基于置信度、文本相似度等
            return f"[OCR识别结果]\n{ocr_text}\n\n[Qwen-VL增强结果]\n{vision_text}"
            
        except Exception as e:
            logger.error(f"结果融合失败: {str(e)}")
            return f"{ocr_text}\n\n{vision_text}"
    
    def _process_with_llm_placeholder(self, page: fitz.Page, page_num: int, pdf_path: str) -> Optional[Dict[str, Any]]:
        """
        大模型处理占位符（待配置）
        
        Args:
            page: PyMuPDF页面对象
            page_num: 页码
            pdf_path: PDF文件路径
            
        Returns:
            大模型处理结果（目前返回None）
        """
        # TODO: 实现多模态大语言模型处理
        # 这里可以集成Qwen-VL、GPT-4V等模型
        logger.info(f"第{page_num + 1}页大模型处理功能待配置")
        return None
    
    def _fuse_ocr_and_llm_results(self, ocr_text: str, llm_result: Dict[str, Any]) -> str:
        """
        融合OCR和大模型结果
        
        Args:
            ocr_text: OCR识别文本
            llm_result: 大模型处理结果
            
        Returns:
            融合后的文本
        """
        # TODO: 实现智能融合策略
        # 可以根据置信度、文本相似度等进行融合
        if llm_result and llm_result.get("text"):
            return f"{ocr_text}\n\n[大模型增强结果]\n{llm_result['text']}"
        return ocr_text
    
    def _create_empty_page_result(self, page_num: int, page_info: Dict) -> Dict[str, Any]:
        """创建空白页面结果"""
        return {
            "page_number": page_num + 1,
            "text": "",
            "text_length": 0,
            "images_count": 0,
            "processing_type": "empty",
            "extraction_method": "empty_page",
            "has_images": False
        }
    
    def _create_error_page_result(self, page_num: int, error_msg: str) -> Dict[str, Any]:
        """创建错误页面结果"""
        return {
            "page_number": page_num + 1,
            "text": f"[处理失败: {error_msg}]",
            "text_length": 0,
            "images_count": 0,
            "processing_type": "error",
            "extraction_method": "error",
            "has_images": False,
            "error": error_msg
        }

    def _extract_page_text(self, page: fitz.Page, page_num: int) -> Dict[str, Any]:
        """
        提取单页文字
        
        Args:
            page: PyMuPDF页面对象
            page_num: 页码（从0开始）
            
        Returns:
            页面提取结果
        """
        try:
            # 获取页面基本信息
            page_info = {
                "page_number": page_num + 1,  # 页码从1开始显示
                "width": page.rect.width,
                "height": page.rect.height,
                "rotation": page.rotation
            }
            
            # 提取文本内容
            text = page.get_text()
            text_length = len(text.strip())
            
            # 提取简化的文本块信息
            text_blocks = page.get_text("dict")
            simplified_text_dict = self._simplify_text_dict(text_blocks)
            
            # 提取图像信息
            image_list = page.get_images()
            
            return {
                "page_info": page_info,
                "text": text,
                "text_length": text_length,
                "text_dict": simplified_text_dict,
                "images_count": len(image_list),
                "is_text_page": text_length > self.min_text_length,
                "has_images": len(image_list) > 0
            }
            
        except Exception as e:
            logger.error(f"页面 {page_num + 1} 文字提取失败: {str(e)}")
            return {
                "page_info": {"page_number": page_num + 1},
                "text": "",
                "text_length": 0,
                "text_dict": {},
                "images_count": 0,
                "is_text_page": False,
                "has_images": False,
                "error": str(e)
            }
    
    def _simplify_text_dict(self, text_dict: Dict) -> Dict:
        """
        简化文本字典，只保留文字和基本排版信息
        
        Args:
            text_dict: 原始文本字典
            
        Returns:
            简化后的文本字典
        """
        if not text_dict:
            return {}
        
        simplified = {
            "width": text_dict.get("width", 0),
            "height": text_dict.get("height", 0),
            "blocks": []
        }
        
        for block in text_dict.get("blocks", []):
            if block.get("type") == 0:  # 文本块
                simplified_block = {
                    "number": block.get("number", 0),
                    "type": 0,
                    "lines": []
                }
                
                for line in block.get("lines", []):
                    simplified_line = {
                        "spans": []
                    }
                    
                    for span in line.get("spans", []):
                        simplified_span = {
                            "size": span.get("size", 0),
                            "font": span.get("font", ""),
                            "text": span.get("text", ""),
                            "flags": span.get("flags", 0)
                        }
                        simplified_line["spans"].append(simplified_span)
                    
                    simplified_block["lines"].append(simplified_line)
                
                simplified["blocks"].append(simplified_block)
        
        return simplified
    
    def _analyze_text_blocks(self, text_blocks: Dict) -> List[Dict[str, Any]]:
        """
        分析文本块结构
        
        Args:
            text_blocks: PyMuPDF返回的文本块字典
            
        Returns:
            结构化的文本块列表
        """
        structured_blocks = []
        
        try:
            for block in text_blocks.get("blocks", []):
                if "lines" in block:  # 文本块
                    block_text = ""
                    lines_info = []
                    
                    for line in block["lines"]:
                        line_text = ""
                        spans_info = []
                        
                        for span in line["spans"]:
                            span_text = span["text"]
                            line_text += span_text
                            
                            spans_info.append({
                                "text": span_text,
                                "font": span["font"],
                                "size": span["size"],
                                "flags": span["flags"],
                                "color": span["color"],
                                "bbox": span["bbox"]
                            })
                        
                        block_text += line_text + "\n"
                        lines_info.append({
                            "text": line_text,
                            "bbox": line["bbox"],
                            "spans": spans_info
                        })
                    
                    structured_blocks.append({
                        "type": "text",
                        "text": block_text.strip(),
                        "bbox": block["bbox"],
                        "lines": lines_info
                    })
                
                elif "image" in block:  # 图像块
                    # 将图像字节数据转换为基本信息字典
                    image_data = block["image"]
                    image_info = {
                        "size": len(image_data) if isinstance(image_data, bytes) else 0,
                        "format": "unknown",
                        "has_data": isinstance(image_data, bytes) and len(image_data) > 0
                    }
                    
                    structured_blocks.append({
                        "type": "image",
                        "bbox": block["bbox"],
                        "image_info": image_info
                    })
            
        except Exception as e:
            logger.error(f"文本块分析失败: {str(e)}")
        
        return structured_blocks
    
    def _clean_text_dict_for_json(self, text_dict: Dict) -> Dict:
        """
        清理text_dict中的bytes数据，确保JSON序列化兼容
        
        Args:
            text_dict: PyMuPDF返回的文本字典
            
        Returns:
            清理后的字典，不包含bytes数据
        """
        try:
            if not isinstance(text_dict, dict):
                return text_dict
            
            cleaned_dict = {}
            for key, value in text_dict.items():
                if isinstance(value, bytes):
                    # 将bytes数据转换为基本信息
                    cleaned_dict[key] = {
                        "type": "bytes",
                        "size": len(value),
                        "note": "原始bytes数据已移除以确保JSON序列化兼容性"
                    }
                elif isinstance(value, dict):
                    # 递归清理嵌套字典
                    cleaned_dict[key] = self._clean_text_dict_for_json(value)
                elif isinstance(value, list):
                    # 清理列表中的元素
                    cleaned_list = []
                    for item in value:
                        if isinstance(item, bytes):
                            cleaned_list.append({
                                "type": "bytes",
                                "size": len(item),
                                "note": "原始bytes数据已移除以确保JSON序列化兼容性"
                            })
                        elif isinstance(item, dict):
                            cleaned_list.append(self._clean_text_dict_for_json(item))
                        else:
                            cleaned_list.append(item)
                    cleaned_dict[key] = cleaned_list
                else:
                    cleaned_dict[key] = value
            
            return cleaned_dict
            
        except Exception as e:
            logger.error(f"清理text_dict失败: {str(e)}")
            return {"error": f"清理失败: {str(e)}"}
    
    def extract_text_with_formatting(self, pdf_path: str) -> Dict[str, Any]:
        """
        提取带格式信息的文字
        
        Args:
            pdf_path: PDF文件路径
            
        Returns:
            包含格式信息的提取结果
        """
        try:
            doc = fitz.open(pdf_path)
            result = {
                "file_path": pdf_path,
                "total_pages": len(doc),
                "pages": [],
                "extraction_method": "pymupdf_with_formatting"
            }
            
            for page_num in range(len(doc)):
                page = doc[page_num]
                
                # 获取带格式的文本
                text_dict = page.get_text("dict")
                html_text = page.get_text("html")
                
                # 清理text_dict中的bytes数据，确保JSON序列化兼容
                cleaned_text_dict = self._clean_text_dict_for_json(text_dict)
                
                page_result = {
                    "page_number": page_num + 1,
                    "text_dict": cleaned_text_dict,
                    "html_text": html_text,
                    "plain_text": page.get_text(),
                    "text_length": len(page.get_text().strip())
                }
                
                result["pages"].append(page_result)
            
            doc.close()
            return result
            
        except Exception as e:
            logger.error(f"带格式文字提取失败: {pdf_path}, 错误: {str(e)}")
            raise Exception(f"带格式文字提取失败: {str(e)}")
    
    async def extract_text_from_pdf_async(self, file_path: str, **kwargs) -> Dict[str, Any]:
        """
        异步从PDF文件提取文字 - 替代PDFProcessingService的功能
        
        Args:
            file_path: PDF文件路径
            **kwargs: 其他参数
            
        Returns:
            提取结果
        """
        try:
            # 提取参数
            use_ocr = kwargs.get('use_ocr', False)
            ocr_engine = kwargs.get('ocr_engine', 'baidu')
            use_vision = kwargs.get('use_vision', False)
            vision_model = kwargs.get('vision_model', 'qwen-vl-plus')
            
            logger.info(f"PDF处理参数: use_ocr={use_ocr}, ocr_engine={ocr_engine}, use_vision={use_vision}, vision_model={vision_model}")
            
            # 转换OCR引擎类型
            from app.schemas.ocr_schemas import OCREngineType
            try:
                ocr_engine_enum = OCREngineType(ocr_engine.lower())
                logger.info(f"OCR引擎类型转换成功: {ocr_engine_enum}")
            except ValueError:
                logger.warning(f"不支持的OCR引擎类型: {ocr_engine}，使用默认引擎: baidu")
                ocr_engine_enum = OCREngineType.BAIDU
            
            # 提取文字
            result = self.extract_text_from_pdf(
                file_path, 
                use_ocr=use_ocr, 
                ocr_engine=ocr_engine_enum,
                use_vision=use_vision,
                vision_model=vision_model
            )
            
            return result
            
        except Exception as e:
            logger.error(f"PDF文字提取失败: {str(e)}")
            raise
    


# 创建全局实例
pdf_extractor = PDFTextExtractor()

