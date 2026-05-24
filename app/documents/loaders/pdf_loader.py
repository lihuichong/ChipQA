from __future__ import annotations  # 启用延迟类型注解，避免运行时前向引用问题

from pathlib import Path  # 导入 Path 以统一处理文件路径

from app.documents.loaders.base import LoadedPage  # 导入文档解析或切片相关组件
from app.text_utils import clean_text  # 导入文本清洗工具以移除非法字符


class PdfLoader:  # 按页提取 PDF 文本
    def load(self, path: str | Path) -> list[LoadedPage]:  # 定义 load 函数或方法
        try:  # 尝试执行可能失败的操作
            from pypdf import PdfReader  # 导入当前模块需要的依赖
        except ImportError as exc:  # 捕获依赖未安装的情况
            raise RuntimeError("pypdf is required to load PDF files. Run: pip install -r requirements.txt") from exc  # 将缺失依赖转换成可读的运行时错误

        reader = PdfReader(str(path))  # 计算并保存 reader
        pages: list[LoadedPage] = []  # 保存当前流程中的 pages 数据
        for index, page in enumerate(reader.pages, start=1):  # 遍历当前集合中的每个元素
            text = clean_text(page.extract_text() or "")  # 保存切片原文内容
            if text.strip():  # 检查条件：text.strip()
                pages.append(LoadedPage(text=text, page_number=index))  # 将当前结果追加到列表
        return pages  # 返回 pages
