from __future__ import annotations  # 启用延迟类型注解，避免运行时前向引用问题

from pathlib import Path  # 导入 Path 以统一处理文件路径
from uuid import uuid4  # 导入 uuid4 为文档和切片生成唯一 ID

from app.chips.model_extractor import extract_chip_models, extract_from_file_name  # 导入芯片型号抽取和规范化工具
from app.documents.loaders.base import LoadedPage  # 导入文档解析或切片相关组件
from app.models import DocumentChunk, DocumentRecord  # 导入问答流程共享的数据结构
from app.text_utils import clean_text  # 导入文本清洗工具以移除非法字符


class DocumentChunker:  # 把页面文本切分成可检索的文档片段
    def __init__(self, chunk_size: int = 1200, overlap: int = 160) -> None:  # 初始化对象所需依赖和配置
        self.chunk_size = chunk_size  # 初始化或更新对象属性 self.chunk_size
        self.overlap = overlap  # 初始化或更新对象属性 self.overlap

    def build_record(self, path: str | Path, pages: list[LoadedPage]) -> DocumentRecord:  # 定义 build_record 函数或方法
        file_path = Path(path)  # 保存资料文件路径
        head_text = "\n".join(page.text[:1000] for page in pages[:3])  # 计算并保存 head_text
        models = extract_from_file_name(file_path)  # 保存当前流程中的 models 数据
        for model in extract_chip_models(head_text):  # 遍历当前集合中的每个元素
            if model not in models:  # 检查条件：model not in models
                models.append(model)  # 将当前结果追加到列表
        return DocumentRecord(  # 返回 DocumentRecord(
            id=str(uuid4()),  # 保存记录唯一标识
            file_name=file_path.name,  # 保存资料文件名
            file_path=str(file_path),  # 保存资料文件路径
            document_type=file_path.suffix.lower().lstrip("."),  # 保存文档类型
            chip_models=models,  # 保存文档中识别出的芯片型号
        )  # 结束当前多行结构

    def chunk_pages(self, record: DocumentRecord, pages: list[LoadedPage]) -> list[DocumentChunk]:  # 定义 chunk_pages 函数或方法
        chunks: list[DocumentChunk] = []  # 保存当前流程中的 chunks 数据
        fallback_model = record.chip_models[0] if record.chip_models else None  # 计算并保存 fallback_model
        for page in pages:  # 遍历当前集合中的每个元素
            parts = self._split_text(page.text)  # 计算并保存 parts
            for index, part in enumerate(parts):  # 遍历当前集合中的每个元素
                models = extract_chip_models(part, limit=1)  # 保存当前流程中的 models 数据
                chip_model = models[0] if models else fallback_model  # 保存该片段对应的芯片型号
                chunks.append(  # 将当前结果追加到列表
                    DocumentChunk(  # 执行当前业务逻辑
                        id=str(uuid4()),  # 保存记录唯一标识
                        document_id=record.id,  # 关联所属文档 ID
                        file_name=record.file_name,  # 保存资料文件名
                        file_path=record.file_path,  # 保存资料文件路径
                        text=part,  # 保存切片原文内容
                        chip_model=chip_model,  # 保存该片段对应的芯片型号
                        page_number=page.page_number,  # 保存 PDF 页码
                        slide_number=page.slide_number,  # 保存 PPT Slide 编号
                        chunk_index=index,  # 保存切片在当前页内的顺序
                    )  # 结束当前多行结构
                )  # 结束当前多行结构
        return chunks  # 返回 chunks

    def _split_text(self, text: str) -> list[str]:  # 定义 _split_text 函数或方法
        safe_text = clean_text(text)  # 计算并保存 safe_text
        cleaned = "\n".join(line.strip() for line in safe_text.splitlines() if line.strip())  # 计算并保存 cleaned
        if len(cleaned) <= self.chunk_size:  # 检查条件：len(cleaned) <= self.chunk_size
            return [cleaned] if cleaned else []  # 返回 [cleaned] if cleaned else []

        chunks: list[str] = []  # 保存当前流程中的 chunks 数据
        start = 0  # 计算并保存 start
        while start < len(cleaned):  # 按条件循环处理文本或数据
            end = min(start + self.chunk_size, len(cleaned))  # 计算并保存 end
            chunk = cleaned[start:end].strip()  # 计算并保存 chunk
            if chunk:  # 检查条件：chunk
                chunks.append(chunk)  # 将当前结果追加到列表
            if end == len(cleaned):  # 检查条件：end == len(cleaned)
                break  # 达到结束条件后退出循环
            start = max(0, end - self.overlap)  # 计算并保存 start
        return chunks  # 返回 chunks
