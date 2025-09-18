"""
Tesseract OCR文字识别服务模块

支持Tesseract开源OCR引擎的多种功能：
1. 通用文字识别，支持多语言
2. 图片预处理和优化
3. 批量处理支持
4. 详细的文字位置和置信度信息
"""

import logging
from typing import Dict, Any, Optional, Union

import cv2
import numpy as np
import pytesseract
from PIL import Image

logger = logging.getLogger(__name__)


class TesseractOCRService:
    """Tesseract OCR文字识别服务"""
    
    def __init__(self):
        """初始化Tesseract OCR服务"""
        self.tesseract_config = {
            'lang': 'chi_sim+eng',  # 中英文混合识别
            'config': '--oem 3 --psm 6 -c tessedit_char_whitelist=0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz一二三四五六七八九十百千万亿零壹贰叁肆伍陆柒捌玖拾佰仟萬億'  # 优化的OCR配置
        }
    
    def preprocess_image(self, image: Union[str, np.ndarray, Image.Image]) -> np.ndarray:
        """
        增强的图片预处理，提高OCR识别准确率
        包括：增强对比度、去除背景噪声、优化图像质量
        
        Args:
            image: 输入图片（路径、numpy数组或PIL图片）
            
        Returns:
            预处理后的图片数组
        """
        try:
            # 转换为numpy数组
            if isinstance(image, str):
                img = cv2.imread(image)
            elif isinstance(image, Image.Image):
                img = cv2.cvtColor(np.array(image), cv2.COLOR_RGB2BGR)
            else:
                img = image.copy()
            
            if img is None:
                raise ValueError("无法读取图片")
            
            # 转换为灰度图
            if len(img.shape) == 3:
                gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
            else:
                gray = img
            
            # 1. 增强对比度 - 使用CLAHE (Contrast Limited Adaptive Histogram Equalization)
            clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8, 8))
            enhanced = clahe.apply(gray)
            
            # 2. 去除背景噪声 - 使用高斯模糊和形态学操作
            # 轻微高斯模糊去除细碎噪声
            blurred = cv2.GaussianBlur(enhanced, (3, 3), 0)
            
            # 3. 自适应阈值二值化 - 更好的文本分离
            binary = cv2.adaptiveThreshold(
                blurred, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, 
                cv2.THRESH_BINARY, 15, 3
            )
            
            # 4. 形态学操作 - 去除小噪点，连接断裂的字符
            # 去除小噪点
            kernel_noise = np.ones((2, 2), np.uint8)
            denoised = cv2.morphologyEx(binary, cv2.MORPH_OPEN, kernel_noise)
            
            # 连接断裂的字符
            kernel_connect = np.ones((1, 3), np.uint8)
            connected = cv2.morphologyEx(denoised, cv2.MORPH_CLOSE, kernel_connect)
            
            # 5. 最终优化 - 去除边缘噪声
            # 创建边缘掩码，去除图像边缘的噪声
            h, w = connected.shape
            mask = np.ones((h, w), dtype=np.uint8) * 255
            # 边缘留出10像素的边距
            margin = 10
            mask[:margin, :] = 0
            mask[-margin:, :] = 0
            mask[:, :margin] = 0
            mask[:, -margin:] = 0
            
            # 应用掩码
            final = cv2.bitwise_and(connected, mask)
            
            # 6. 如果图像太暗，进行亮度调整
            mean_brightness = np.mean(final)
            if mean_brightness < 100:  # 图像偏暗
                # 增加亮度
                final = cv2.add(final, 30)
            
            return final
            
        except Exception as e:
            logger.error(f"图片预处理失败: {str(e)}")
            # 如果预处理失败，返回原图
            if isinstance(image, str):
                return cv2.imread(image, cv2.IMREAD_GRAYSCALE)
            elif isinstance(image, Image.Image):
                return np.array(image.convert('L'))
            else:
                return image
    
    def extract_text(self, image: Union[str, np.ndarray, Image.Image], 
                    preprocess: bool = True) -> Dict[str, Any]:
        """
        使用Tesseract进行文字识别
        
        Args:
            image: 输入图片
            preprocess: 是否进行预处理
            
        Returns:
            识别结果字典
        """
        try:
            # 预处理图片
            if preprocess:
                processed_img = self.preprocess_image(image)
            else:
                if isinstance(image, str):
                    processed_img = cv2.imread(image, cv2.IMREAD_GRAYSCALE)
                elif isinstance(image, Image.Image):
                    processed_img = np.array(image.convert('L'))
                else:
                    processed_img = image
            
            # 使用Tesseract进行OCR
            text = pytesseract.image_to_string(
                processed_img, 
                lang=self.tesseract_config['lang'],
                config=self.tesseract_config['config']
            )
            
            # 获取详细信息
            data = pytesseract.image_to_data(
                processed_img,
                lang=self.tesseract_config['lang'],
                config=self.tesseract_config['config'],
                output_type=pytesseract.Output.DICT
            )
            
            # 解析结果
            words = []
            for i in range(len(data['text'])):
                if int(data['conf'][i]) > 20:  # 降低置信度阈值，提高识别率
                    # 将Tesseract的0-100置信度转换为0-1
                    confidence = int(data['conf'][i]) / 100.0
                    words.append({
                        'text': data['text'][i],
                        'confidence': confidence,
                        'bbox': [
                            data['left'][i],
                            data['top'][i],
                            data['left'][i] + data['width'][i],
                            data['top'][i] + data['height'][i]
                        ]
                    })
            
            return {
                'engine': 'tesseract',
                'text': text.strip(),
                'words': words,
                'total_words': len(words),
                'average_confidence': np.mean([w['confidence'] for w in words]) if words else 0,
                'success': len(text.strip()) > 0
            }
            
        except Exception as e:
            logger.error(f"Tesseract OCR识别失败: {str(e)}")
            return {
                'engine': 'tesseract',
                'text': '',
                'words': [],
                'total_words': 0,
                'average_confidence': 0,
                'success': False,
                'error': str(e)
            }
    
    def extract_text_from_pdf_page(self, pdf_path: str, page_num: int = 0) -> Dict[str, Any]:
        """
        从PDF页面提取文字（OCR方式）
        
        Args:
            pdf_path: PDF文件路径
            page_num: 页码（从0开始）
            
        Returns:
            识别结果字典
        """
        doc = None
        pix = None
        try:
            import fitz  # PyMuPDF
            import gc  # 垃圾回收
            
            logger.info(f"开始处理PDF页面: {pdf_path}, 页码: {page_num}")
            
            # 打开PDF文档
            doc = fitz.open(pdf_path)
            if page_num >= len(doc):
                raise ValueError(f"页码超出范围: {page_num} (总页数: {len(doc)})")
            
            # 获取页面
            page = doc[page_num]
            
            # 将页面转换为图片 - 使用更保守的设置避免内存问题
            mat = fitz.Matrix(1.5, 1.5)  # 降低缩放比例，减少内存使用
            pix = page.get_pixmap(matrix=mat, alpha=False)  # 禁用alpha通道
            
            # 立即释放页面对象
            page = None
            
            # 转换为字节数据
            img_data = pix.tobytes("png")
            
            # 立即释放pixmap对象
            pix = None
            
            # 强制垃圾回收
            gc.collect()
            
            logger.info(f"PDF页面转换为图像完成，大小: {len(img_data)} bytes")
            
            # 转换为PIL图片
            from io import BytesIO
            img = Image.open(BytesIO(img_data))
            
            # 进行OCR识别，添加异常处理
            try:
                result = self.extract_text(img)
                result['page_number'] = page_num + 1
                result['pdf_path'] = pdf_path
                
                logger.info(f"OCR识别完成: success={result.get('success', False)}, text_length={len(result.get('text', ''))}")
                
                # 清理图片对象
                img.close()
                
            except Exception as ocr_error:
                logger.error(f"OCR识别过程失败: {str(ocr_error)}")
                # 返回空结果而不是抛出异常
                result = {
                    'engine': 'tesseract',
                    'text': '',
                    'words': [],
                    'total_words': 0,
                    'average_confidence': 0,
                    'page_number': page_num + 1,
                    'pdf_path': pdf_path,
                    'success': False,
                    'error': str(ocr_error)
                }
            
            return result
            
        except Exception as e:
            logger.error(f"PDF页面OCR识别失败: {str(e)}")
            # 返回错误结果而不是抛出异常
            return {
                'engine': 'tesseract',
                'text': '',
                'words': [],
                'total_words': 0,
                'average_confidence': 0,
                'page_number': page_num + 1,
                'pdf_path': pdf_path,
                'success': False,
                'error': str(e)
            }
        finally:
            # 确保资源被正确释放
            try:
                if pix is not None:
                    pix = None
                if doc is not None:
                    doc.close()
                # 强制垃圾回收
                import gc
                gc.collect()
            except:
                pass
    
    def health_check(self) -> Dict[str, Any]:
        """
        Tesseract OCR服务健康检查
        
        Returns:
            服务状态信息
        """
        status = {
            'tesseract_available': False,
            'version': None,
            'supported_languages': [],
            'error': None
        }
        
        try:
            # 检查Tesseract版本
            version = pytesseract.get_tesseract_version()
            status['tesseract_available'] = True
            status['version'] = version
            
            # 获取支持的语言
            try:
                langs = pytesseract.get_languages()
                status['supported_languages'] = langs
            except Exception as e:
                logger.warning(f"无法获取支持的语言列表: {e}")
                status['supported_languages'] = ['eng', 'chi_sim']  # 默认支持的语言
            
            logger.info(f"Tesseract OCR服务健康检查通过，版本: {version}")
            
        except Exception as e:
            status['error'] = str(e)
            logger.error(f"Tesseract OCR服务健康检查失败: {str(e)}")
        
        return status


# 创建全局实例
tesseract_ocr_service = TesseractOCRService()
