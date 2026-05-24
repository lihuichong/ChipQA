import tempfile  # 创建测试临时目录
import time  # 调整测试文件修改时间
import unittest  # 导入标准库单元测试框架
from pathlib import Path  # 统一处理测试文件路径

from app.models import DocumentChunk  # 导入 chunk 数据结构
from app.retrieval.embedding_store import EmbeddingIndexStore  # 导入 embedding 索引存储
from app.retrieval.embeddings import EmbeddingClient, FakeEmbeddingClient  # 导入可测试的 embedding 客户端


class EmbeddingStoreTest(unittest.TestCase):  # 定义 embedding 存储测试类
    def test_build_and_attach_embeddings(self):  # 验证 embedding 能写入 JSONL 并挂载回 chunk
        with tempfile.TemporaryDirectory() as temp_dir:  # 创建临时目录隔离测试数据
            tmp_path = Path(temp_dir)  # 转换临时目录路径
            source = tmp_path / "ABC1234.txt"  # 构造临时来源文件路径
            source.write_text("ABC1234 Operating voltage 3.3V", encoding="utf-8")  # 写入来源文件内容
            chunk = DocumentChunk(  # 构造待生成 embedding 的 chunk
                id="chunk-1",  # 设置稳定 chunk ID
                document_id="doc-1",  # 设置所属文档 ID
                file_name=source.name,  # 设置来源文件名
                file_path=str(source),  # 设置来源文件路径
                text="ABC1234 Operating voltage 3.3V",  # 设置 chunk 正文
                chip_model="ABC1234",  # 设置芯片型号
            )  # 结束 chunk 构造
            store = EmbeddingIndexStore(tmp_path / "index")  # 创建 embedding 存储
            generated = store.build_missing_embeddings([chunk], FakeEmbeddingClient(), "fake-embedding")  # 生成并保存 embedding
            self.assertEqual(generated, 1)  # 断言生成了一条 embedding
            self.assertTrue((tmp_path / "index" / "embeddings.jsonl").exists())  # 断言 embedding 文件已创建

            fresh_chunk = DocumentChunk(**chunk.to_dict())  # 构造不带 embedding 的新 chunk 对象
            attached = store.attach_embeddings([fresh_chunk], "fake-embedding")  # 从 JSONL 挂载 embedding
            self.assertEqual(attached, 1)  # 断言成功挂载一条 embedding
            self.assertIn("embedding", fresh_chunk.metadata)  # 断言 metadata 中已有 embedding

    def test_file_mtime_change_invalidates_embedding(self):  # 验证来源文件更新后旧 embedding 会失效
        with tempfile.TemporaryDirectory() as temp_dir:  # 创建临时目录隔离测试数据
            tmp_path = Path(temp_dir)  # 转换临时目录路径
            source = tmp_path / "ABC1234.txt"  # 构造临时来源文件路径
            source.write_text("old text", encoding="utf-8")  # 写入初始文件内容
            chunk = DocumentChunk("chunk-1", "doc-1", source.name, str(source), "old text", chip_model="ABC1234")  # 构造初始 chunk
            store = EmbeddingIndexStore(tmp_path / "index")  # 创建 embedding 存储
            store.build_missing_embeddings([chunk], FakeEmbeddingClient(), "fake-embedding")  # 生成初始 embedding
            source.write_text("new text", encoding="utf-8")  # 更新来源文件修改时间和内容
            future_time = time.time() + 10  # 构造明显不同的文件修改时间
            source.touch()  # 确保文件系统记录一次修改
            source.stat()  # 读取状态以刷新文件系统元数据
            import os  # 导入 os 以设置文件修改时间
            os.utime(source, (future_time, future_time))  # 强制设置来源文件修改时间

            stale_chunk = DocumentChunk(**chunk.to_dict())  # 构造旧文本 chunk 以模拟未重新 ingest 的过期索引
            attached = store.attach_embeddings([stale_chunk], "fake-embedding")  # 尝试挂载旧 embedding
            self.assertEqual(attached, 0)  # 断言文件更新后旧 embedding 不再挂载

    def test_build_embeddings_uses_batch_client(self):  # 验证生成资料向量时使用批量接口
        with tempfile.TemporaryDirectory() as temp_dir:  # 创建临时目录隔离测试数据
            tmp_path = Path(temp_dir)  # 转换临时目录路径
            source = tmp_path / "ABC1234.txt"  # 构造临时来源文件路径
            source.write_text("datasheet", encoding="utf-8")  # 写入来源文件内容
            chunks = [  # 构造多条待生成 embedding 的 chunk
                DocumentChunk(f"chunk-{index}", "doc-1", source.name, str(source), f"text {index}", chip_model="ABC1234")  # 构造单条 chunk
                for index in range(3)  # 生成三条 chunk
            ]  # 结束 chunk 列表
            client = BatchCountingEmbeddingClient()  # 创建统计批量调用的 embedding 客户端
            store = EmbeddingIndexStore(tmp_path / "index")  # 创建 embedding 存储
            generated = store.build_missing_embeddings(chunks, client, "batch-model")  # 批量生成 embedding
            self.assertEqual(generated, 3)  # 断言三条 embedding 都已生成
            self.assertEqual(client.single_calls, 0)  # 断言没有退回单条调用
            self.assertEqual(client.batch_calls, 1)  # 断言三条 chunk 合并为一次批量调用


class BatchCountingEmbeddingClient(EmbeddingClient):  # 用于测试批量生成路径的 embedding 客户端
    def __init__(self) -> None:  # 初始化调用计数器
        self.single_calls = 0  # 保存单条调用次数
        self.batch_calls = 0  # 保存批量调用次数

    def embed(self, text: str) -> list[float]:  # 单条调用只记录次数
        self.single_calls += 1  # 累加单条调用次数
        return [1.0, 0.0]  # 返回固定向量

    def embed_many(self, texts: list[str]) -> list[list[float]]:  # 批量调用返回每条文本的向量
        self.batch_calls += 1  # 累加批量调用次数
        return [[1.0, float(index)] for index, _text in enumerate(texts)]  # 返回与输入数量一致的向量
