from __future__ import annotations  # 启用延迟类型注解，避免运行时前向引用问题

from pathlib import Path  # 导入 Path 以统一处理文件路径

from app.documents.loaders.base import LoadedPage  # 导入文档解析或切片相关组件
from app.text_utils import clean_text  # 导入文本清洗工具以移除非法字符


class TextLoader:  # 读取 TXT/MD 文本文档
    def load(self, path: str | Path) -> list[LoadedPage]:  # 定义 load 函数或方法
        text = clean_text(Path(path).read_text(encoding="utf-8", errors="ignore"))  # 以 UTF-8 读取文本文件内容
        return [LoadedPage(text=text, page_number=1)] if text.strip() else []  # 返回 [LoadedPage(text=text, page_number=1)] i
