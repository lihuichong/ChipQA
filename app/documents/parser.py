from __future__ import annotations  # 启用延迟类型注解，避免运行时前向引用问题

from pathlib import Path  # 导入 Path 以统一处理文件路径

from app.documents.loaders.base import LoadedPage  # 导入文档解析或切片相关组件
from app.documents.loaders.pdf_loader import PdfLoader  # 导入文档解析或切片相关组件
from app.documents.loaders.ppt_loader import PptLoader  # 导入文档解析或切片相关组件
from app.documents.loaders.text_loader import TextLoader  # 导入文档解析或切片相关组件


SUPPORTED_EXTENSIONS = {".pdf", ".ppt", ".pptx", ".txt", ".md"}  # 计算并保存 SUPPORTED_EXTENSIONS


class DocumentParser:  # 根据文件扩展名选择对应的文档解析器
    def load_pages(self, path: str | Path) -> list[LoadedPage]:  # 定义 load_pages 函数或方法
        file_path = Path(path)  # 保存资料文件路径
        suffix = file_path.suffix.lower()  # 计算并保存 suffix
        if suffix == ".pdf":  # 检查条件：suffix == ".pdf"
            return PdfLoader().load(file_path)  # 返回 PdfLoader().load(file_path)
        if suffix in {".ppt", ".pptx"}:  # 检查条件：suffix in {".ppt", ".pptx"}
            return PptLoader().load(file_path)  # 返回 PptLoader().load(file_path)
        if suffix in {".txt", ".md"}:  # 检查条件：suffix in {".txt", ".md"}
            return TextLoader().load(file_path)  # 返回 TextLoader().load(file_path)
        raise ValueError(f"Unsupported file type: {file_path.suffix}")  # 向调用方报告当前错误


def iter_supported_files(path: str | Path) -> list[Path]:  # 定义 iter_supported_files 函数或方法
    root = Path(path)  # 计算并保存 root
    if root.is_file():  # 检查条件：root.is_file()
        return [root] if root.suffix.lower() in SUPPORTED_EXTENSIONS else []  # 返回 [root] if root.suffix.lower() in SUPPORT
    return sorted(file for file in root.rglob("*") if file.is_file() and file.suffix.lower() in SUPPORTED_EXTENSIONS)  # 返回 sorted(file for file in root.rglob("*") 
