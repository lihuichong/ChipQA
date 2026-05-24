from __future__ import annotations  # 启用延迟类型注解，避免运行时前向引用问题

import hashlib  # 计算 chunk 文本哈希，用于判断 embedding 是否仍然匹配
import json  # 读写 JSONL 格式的 embedding 索引
from pathlib import Path  # 统一处理文件路径
from time import time  # 记录 embedding 生成时间

from app.models import DocumentChunk  # 导入 chunk 数据结构
from app.retrieval.embeddings import EmbeddingClient  # 导入 embedding 客户端接口
from app.text_utils import clean_text  # 清理写入 JSONL 前的非法字符


class EmbeddingIndexStore:  # 管理 data/index/embeddings.jsonl 中的 chunk embedding
    def __init__(self, index_dir: str | Path = "data/index") -> None:  # 初始化 embedding 索引路径
        self.index_dir = Path(index_dir)  # 保存索引目录路径
        self.embeddings_path = self.index_dir / "embeddings.jsonl"  # 保存 embedding JSONL 文件路径

    def build_missing_embeddings(self, chunks: list[DocumentChunk], client: EmbeddingClient | None, model: str | None) -> int:  # 为缺失或失效的 chunk 生成 embedding
        if client is None or not model:  # 没有 embedding 配置时不生成
            return 0  # 返回生成数量为零
        existing = self.load_raw_by_chunk_id()  # 读取已有 embedding 记录
        updated = dict(existing)  # 复制已有记录，后续增量更新
        generated = 0  # 记录本次生成的 embedding 数量
        pending: list[tuple[DocumentChunk, dict]] = []  # 保存需要生成或刷新的 chunk 及其签名
        for chunk in chunks:  # 遍历待检查的 chunk
            current_signature = _chunk_signature(chunk, model)  # 计算当前 chunk 的 embedding 签名
            old_record = existing.get(chunk.id)  # 读取该 chunk 旧 embedding 记录
            if not _record_matches(old_record, current_signature):  # 缺失或失效时加入待生成列表
                pending.append((chunk, current_signature))  # 保存待生成项
        for batch in _batched(pending, 10):  # 按最多十条一组生成 embedding，兼容 SophNet 限制
            texts = [chunk.text[:2000] for chunk, _signature in batch]  # 准备批量输入文本
            embeddings = client.embed_many(texts)  # 调用 embedding 服务批量生成 chunk 向量
            batch_generated = 0  # 记录当前批次成功生成数量
            for (chunk, current_signature), embedding in zip(batch, embeddings):  # 按顺序写回每个 chunk 的向量
                if not embedding:  # 服务未返回有效向量时跳过保存
                    continue  # 继续处理后续 chunk
                updated[chunk.id] = {  # 保存新的 embedding 记录
                    **current_signature,  # 写入模型、文件时间和文本哈希等签名字段
                    "chunk_id": chunk.id,  # 保存 chunk ID
                    "embedding": embedding,  # 保存 embedding 向量
                    "created_at": time(),  # 保存生成时间戳
                }  # 结束记录构造
                generated += 1  # 累加生成数量
                batch_generated += 1  # 累加当前批次生成数量
            if batch_generated:  # 当前批次有成功结果时立即落盘，支持超时后断点续跑
                self.write_records(updated.values())  # 将合并后的记录写回 JSONL
        return generated  # 返回本次生成数量

    def attach_embeddings(self, chunks: list[DocumentChunk], model: str | None) -> int:  # 将有效 embedding 挂载到 chunk.metadata
        if not model:  # 没有 embedding 模型名时无法校验记录
            return 0  # 返回挂载数量为零
        records = self.load_raw_by_chunk_id()  # 读取 embedding 文件
        attached = 0  # 记录成功挂载数量
        for chunk in chunks:  # 遍历待挂载的 chunk
            record = records.get(chunk.id)  # 读取当前 chunk 的 embedding 记录
            if not _record_matches(record, _chunk_signature(chunk, model)):  # 记录不存在或已失效时跳过
                continue  # 继续处理下一个 chunk
            chunk.metadata = dict(chunk.metadata or {})  # 确保 metadata 可写
            chunk.metadata["embedding"] = record.get("embedding", [])  # 挂载 embedding 向量到 chunk
            chunk.metadata["embedding_model"] = model  # 记录当前使用的 embedding 模型
            attached += 1  # 累加挂载数量
        return attached  # 返回成功挂载数量

    def prune_to_chunk_ids(self, chunk_ids: set[str]) -> int:  # 删除已经不存在的 chunk embedding
        records = self.load_raw_by_chunk_id()  # 读取已有 embedding 记录
        kept = {chunk_id: record for chunk_id, record in records.items() if chunk_id in chunk_ids}  # 只保留仍存在的 chunk
        removed = len(records) - len(kept)  # 计算删除数量
        if removed:  # 有孤儿记录时写回文件
            self.write_records(kept.values())  # 写回清理后的记录
        return removed  # 返回删除数量

    def load_raw_by_chunk_id(self) -> dict[str, dict]:  # 按 chunk_id 读取 embedding 记录
        if not self.embeddings_path.exists():  # 文件不存在时返回空索引
            return {}  # 返回空字典
        records: dict[str, dict] = {}  # 初始化记录映射
        with self.embeddings_path.open("r", encoding="utf-8") as file:  # 打开 embedding JSONL 文件
            for line in file:  # 遍历每一行 JSON
                if not line.strip():  # 跳过空行
                    continue  # 继续下一行
                record = json.loads(line)  # 解析 JSON 记录
                chunk_id = record.get("chunk_id")  # 读取 chunk ID
                if chunk_id:  # 只保存有 chunk_id 的记录
                    records[chunk_id] = record  # 写入记录映射
        return records  # 返回记录映射

    def write_records(self, records) -> None:  # 将 embedding 记录集合写入 JSONL
        self.index_dir.mkdir(parents=True, exist_ok=True)  # 确保索引目录存在
        with self.embeddings_path.open("w", encoding="utf-8") as file:  # 覆盖写入 embedding JSONL
            for record in records:  # 遍历待写入记录
                file.write(json.dumps(_clean_record(record), ensure_ascii=False) + "\n")  # 写入单行 JSON


def _chunk_signature(chunk: DocumentChunk, model: str) -> dict:  # 生成判断 embedding 是否有效的签名
    return {  # 返回签名字典
        "embedding_model": model,  # 保存 embedding 模型名
        "text_hash": _text_hash(chunk.text),  # 保存 chunk 文本哈希
        "file_path": chunk.file_path,  # 保存来源文件路径
        "file_mtime": _file_mtime(chunk.file_path),  # 保存来源文件修改时间
    }  # 结束签名字典


def _batched(items: list, size: int):  # 将列表按固定大小切成多个批次
    for start in range(0, len(items), size):  # 按步长遍历列表起点
        yield items[start : start + size]  # 返回当前批次切片


def _record_matches(record: dict | None, signature: dict) -> bool:  # 判断已有 embedding 记录是否仍然有效
    if not record:  # 没有记录时不匹配
        return False  # 返回无效
    return all(record.get(key) == value for key, value in signature.items())  # 所有签名字段一致才视为有效


def _text_hash(text: str) -> str:  # 计算 chunk 文本哈希
    return hashlib.sha256(clean_text(text).encode("utf-8")).hexdigest()  # 返回 SHA-256 哈希


def _file_mtime(file_path: str) -> float | None:  # 读取来源文件修改时间
    path = Path(file_path)  # 转换为 Path 对象
    if not path.exists():  # 来源文件不存在时无法记录修改时间
        return None  # 返回 None
    return path.stat().st_mtime  # 返回文件修改时间戳


def _clean_record(value):  # 清理 embedding 记录中的非法字符串
    if isinstance(value, str):  # 字符串需要清理非法字符
        return clean_text(value)  # 返回清理后的字符串
    if isinstance(value, list):  # 列表递归清理每个元素
        return [_clean_record(item) for item in value]  # 返回清理后的列表
    if isinstance(value, dict):  # 字典递归清理每个值
        return {key: _clean_record(item) for key, item in value.items()}  # 返回清理后的字典
    return value  # 其它类型原样返回
