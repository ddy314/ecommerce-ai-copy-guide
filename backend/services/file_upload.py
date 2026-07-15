"""文件上传服务 - 支持评论文件上传(txt/excel/word/md)"""
from __future__ import annotations

import io
import logging
import os
import re

logger = logging.getLogger(__name__)


class FileUploadService:
    """评论文件解析服务"""

    SUPPORTED_EXTENSIONS = {".txt", ".csv", ".md", ".xlsx", ".xls", ".docx", ".doc"}

    def parse_reviews_file(self, filename: str, file_data: bytes) -> list[str]:
        """解析上传的评论文件，返回评论列表"""
        ext = os.path.splitext(filename)[1].lower()

        if ext not in self.SUPPORTED_EXTENSIONS:
            raise ValueError(f"不支持的文件格式: {ext}，支持: {', '.join(self.SUPPORTED_EXTENSIONS)}")

        if ext in (".txt", ".md"):
            return self._parse_text(file_data)
        elif ext == ".csv":
            return self._parse_csv(file_data)
        elif ext in (".xlsx", ".xls"):
            return self._parse_excel(file_data, ext)
        elif ext in (".docx", ".doc"):
            return self._parse_docx(file_data, ext)
        else:
            raise ValueError(f"不支持的文件格式: {ext}")

    def _parse_text(self, data: bytes) -> list[str]:
        """解析文本文件 - 每行一条评论"""
        try:
            text = data.decode("utf-8")
        except UnicodeDecodeError:
            text = data.decode("gbk", errors="ignore")

        lines = [line.strip() for line in text.splitlines() if line.strip()]
        # 过滤掉过短的行（可能是标题或分隔符）
        return [line for line in lines if len(line) > 3]

    def _parse_csv(self, data: bytes) -> list[str]:
        """解析 CSV 文件"""
        try:
            text = data.decode("utf-8")
        except UnicodeDecodeError:
            text = data.decode("gbk", errors="ignore")

        import csv
        reader = csv.reader(io.StringIO(text))
        reviews = []
        for i, row in enumerate(reader):
            if i == 0 and len(row) <= 3:
                # 跳过表头
                continue
            # 取最后一列作为评论内容，或拼接所有列
            if row:
                content = row[-1].strip() if len(row) == 1 else " ".join(c.strip() for c in row if c.strip())
                if content and len(content) > 3:
                    reviews.append(content)
        return reviews

    def _parse_excel(self, data: bytes, ext: str) -> list[str]:
        """解析 Excel 文件"""
        try:
            import openpyxl
        except ImportError:
            # 降级为 CSV 解析
            logger.warning("openpyxl 未安装，尝试用 CSV 方式解析")
            return self._parse_text(data)

        wb = openpyxl.load_workbook(io.BytesIO(data), read_only=True)
        ws = wb.active
        reviews = []
        for i, row in enumerate(ws.iter_rows(values_only=True)):
            if i == 0:
                continue  # 跳过表头
            # 找到第一个非空字符串单元格
            for cell in row:
                if cell and isinstance(cell, str) and len(cell.strip()) > 3:
                    reviews.append(cell.strip())
                    break
        wb.close()
        return reviews

    def _parse_docx(self, data: bytes, ext: str) -> list[str]:
        """解析 Word 文档"""
        if ext == ".docx":
            try:
                from docx import Document
                doc = Document(io.BytesIO(data))
                reviews = []
                for para in doc.paragraphs:
                    text = para.text.strip()
                    if text and len(text) > 3:
                        reviews.append(text)
                return reviews
            except ImportError:
                logger.warning("python-docx 未安装，尝试用文本方式解析")
                return self._parse_text(data)
        else:
            # .doc 格式 - 降级为文本解析
            return self._parse_text(data)
