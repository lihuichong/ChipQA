import unittest  # 导入标准库单元测试框架

from app.documents.chunker import DocumentChunker  # 导入文档解析或切片相关组件
from app.documents.loaders.base import LoadedPage  # 导入文档解析或切片相关组件


class ChunkerTest(unittest.TestCase):  # 定义 ChunkerTest 类
    def test_chunker_preserves_source_metadata(self):  # 定义测试用例 test_chunker_preserves_source_metadata
        pages = [LoadedPage(text="ABC1234 Electrical Characteristics Operating voltage 2.7V to 5.5V", page_number=3)]  # 保存当前流程中的 pages 数据
        chunker = DocumentChunker(chunk_size=50, overlap=5)  # 计算并保存 chunker
        record = chunker.build_record("ABC1234_Datasheet.txt", pages)  # 计算并保存 record
        chunks = chunker.chunk_pages(record, pages)  # 保存当前流程中的 chunks 数据
        self.assertTrue(chunks)  # 断言测试结果符合预期
        self.assertEqual(chunks[0].file_name, "ABC1234_Datasheet.txt")  # 断言测试结果符合预期
        self.assertEqual(chunks[0].page_number, 3)  # 断言测试结果符合预期
        self.assertEqual(chunks[0].chip_model, "ABC1234")  # 断言测试结果符合预期
