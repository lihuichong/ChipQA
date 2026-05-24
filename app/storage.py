from __future__ import annotations  # 启用延迟类型注解，避免运行时前向引用问题

import json  # 导入 JSON 序列化和反序列化工具
from pathlib import Path  # 导入 Path 以统一处理文件路径

from app.models import DocumentChunk, DocumentRecord  # 导入问答流程共享的数据结构
from app.text_utils import clean_text  # 导入文本清洗工具以移除非法字符


class JsonIndexStore:  # 用 JSONL 文件保存和读取本地索引
    def __init__(self, index_dir: str | Path = "data/index") -> None:  # 初始化对象所需依赖和配置
        self.index_dir = Path(index_dir)  # 初始化或更新对象属性 self.index_dir
        self.documents_path = self.index_dir / "documents.jsonl"  # 初始化或更新对象属性 self.documents_path
        self.chunks_path = self.index_dir / "chunks.jsonl"  # 初始化或更新对象属性 self.chunks_path

    def save(self, records: list[DocumentRecord], chunks: list[DocumentChunk], append: bool = True) -> None:  # 定义 save 函数或方法
        self.index_dir.mkdir(parents=True, exist_ok=True)  # 确保索引目录存在
        mode = "a" if append else "w"  # 计算并保存 mode
        with self.documents_path.open(mode, encoding="utf-8") as file:  # 打开资源并在结束时自动关闭
            for record in records:  # 遍历当前集合中的每个元素
                file.write(_safe_json_dumps(record.to_dict()) + "\n")  # 将序列化后的数据写入文件
        with self.chunks_path.open(mode, encoding="utf-8") as file:  # 打开资源并在结束时自动关闭
            for chunk in chunks:  # 遍历当前集合中的每个元素
                file.write(_safe_json_dumps(chunk.to_dict()) + "\n")  # 将序列化后的数据写入文件

    def replace_files(self, records: list[DocumentRecord], chunks: list[DocumentChunk], file_paths: set[str]) -> None:  # 替换指定来源文件的索引记录
        current_records = [record for record in self.load_records() if record.file_path not in file_paths]  # 保留不属于本次文件的文档记录
        current_chunks = [chunk for chunk in self.load_chunks() if chunk.file_path not in file_paths]  # 保留不属于本次文件的 chunk
        self.save(current_records + records, current_chunks + chunks, append=False)  # 覆盖写入去重后的完整索引

    def load_records(self) -> list[DocumentRecord]:  # 定义 load_records 函数或方法
        if not self.documents_path.exists():  # 检查条件：not self.documents_path.exists()
            return []  # 没有可用数据时返回空列表
        return [DocumentRecord.from_dict(item) for item in _read_jsonl(self.documents_path)]  # 返回 [DocumentRecord.from_dict(item) for item

    def load_chunks(self) -> list[DocumentChunk]:  # 定义 load_chunks 函数或方法
        if not self.chunks_path.exists():  # 检查条件：not self.chunks_path.exists()
            return []  # 没有可用数据时返回空列表
        return [DocumentChunk.from_dict(item) for item in _read_jsonl(self.chunks_path)]  # 返回 [DocumentChunk.from_dict(item) for item 


def _read_jsonl(path: Path) -> list[dict]:  # 定义 _read_jsonl 函数或方法
    items: list[dict] = []  # 计算并保存 items
    with path.open("r", encoding="utf-8") as file:  # 打开资源并在结束时自动关闭
        for line in file:  # 遍历当前集合中的每个元素
            if line.strip():  # 检查条件：line.strip()
                items.append(json.loads(line))  # 将当前结果追加到列表
    return items  # 返回 items


def _safe_json_dumps(data: dict) -> str:  # 定义 _safe_json_dumps 函数或方法
    cleaned = _clean_value(data)  # 计算并保存 cleaned
    return json.dumps(cleaned, ensure_ascii=False)  # 返回 JSON 字符串表示


def _clean_value(value):  # 定义 _clean_value 函数或方法
    if isinstance(value, str):  # 检查条件：isinstance(value, str)
        return clean_text(value)  # 返回 clean_text(value)
    if isinstance(value, list):  # 检查条件：isinstance(value, list)
        return [_clean_value(item) for item in value]  # 返回 [_clean_value(item) for item in value]
    if isinstance(value, dict):  # 检查条件：isinstance(value, dict)
        return {key: _clean_value(item) for key, item in value.items()}  # 返回 {key: _clean_value(item) for key, item i
    return value  # 返回 value
