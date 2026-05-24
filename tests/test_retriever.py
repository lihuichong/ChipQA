import unittest  # 导入标准库单元测试框架

from app.models import DocumentChunk  # 导入问答流程共享的数据结构
from app.retrieval.embeddings import EmbeddingClient  # 导入 embedding 客户端接口
from app.retrieval.retriever import LocalRetriever  # 导入本地检索或 embedding 相关组件


class RetrieverTest(unittest.TestCase):  # 定义 RetrieverTest 类
    def test_retriever_filters_by_chip_model(self):  # 定义测试用例 test_retriever_filters_by_chip_model
        chunks = [  # 保存当前流程中的 chunks 数据
            DocumentChunk(  # 执行当前业务逻辑
                id="1",  # 保存记录唯一标识
                document_id="d1",  # 关联所属文档 ID
                file_name="a.txt",  # 保存资料文件名
                file_path="a.txt",  # 保存资料文件路径
                chip_model="ABC1234",  # 保存该片段对应的芯片型号
                text="ABC1234 Operating voltage 2.7V to 5.5V",  # 保存切片原文内容
            ),  # 结束当前多行结构
            DocumentChunk(  # 执行当前业务逻辑
                id="2",  # 保存记录唯一标识
                document_id="d2",  # 关联所属文档 ID
                file_name="b.txt",  # 保存资料文件名
                file_path="b.txt",  # 保存资料文件路径
                chip_model="XYZ9999",  # 保存该片段对应的芯片型号
                text="XYZ9999 Operating voltage 1.8V",  # 保存切片原文内容
            ),  # 结束当前多行结构
        ]  # 结束当前多行结构
        evidence = LocalRetriever(chunks).search("Operating voltage", "ABC1234")  # 保存当前流程中的 evidence 数据
        self.assertEqual(len(evidence), 1)  # 断言测试结果符合预期
        self.assertEqual(evidence[0].file_name, "a.txt")  # 断言测试结果符合预期

    def test_retriever_matches_model_in_file_name_for_multi_model_datasheet(self):  # 定义测试用例 test_retriever_matches_model_in_file_name_for_multi_model_datasheet
        chunks = [  # 保存当前流程中的 chunks 数据
            DocumentChunk(  # 执行当前业务逻辑
                id="1",  # 保存记录唯一标识
                document_id="d1",  # 关联所属文档 ID
                file_name="CV180ZB_CV1800B_CV1801B_Datasheet.pdf",  # 保存资料文件名
                file_path="datasheet.pdf",  # 保存资料文件路径
                chip_model="CV180ZB",  # 保存该片段对应的芯片型号
                text="工作电压 内核电压为 0.9V IO 电压为 1.8V 及 3.0V",  # 保存切片原文内容
            ),  # 结束当前多行结构
            DocumentChunk(  # 执行当前业务逻辑
                id="2",  # 保存记录唯一标识
                document_id="d2",  # 关联所属文档 ID
                file_name="XYZ9999_Datasheet.pdf",  # 保存资料文件名
                file_path="other.pdf",  # 保存资料文件路径
                chip_model="XYZ9999",  # 保存该片段对应的芯片型号
                text="工作电压 5V",  # 保存切片原文内容
            ),  # 结束当前多行结构
        ]  # 结束当前多行结构
        evidence = LocalRetriever(chunks).search("工作电压是多少", "CV1800B")  # 保存当前流程中的 evidence 数据
        self.assertEqual(len(evidence), 1)  # 断言测试结果符合预期
        self.assertEqual(evidence[0].file_name, "CV180ZB_CV1800B_CV1801B_Datasheet.pdf")  # 断言测试结果符合预期

    def test_retriever_does_not_embed_chunks_during_search(self):  # 验证问答阶段不会临时为 chunk 生成 embedding
        chunks = [  # 构造没有缓存 embedding 的 chunk
            DocumentChunk(  # 创建测试 chunk
                id="1",  # 设置 chunk ID
                document_id="doc",  # 设置文档 ID
                file_name="ABC1234.txt",  # 设置文件名
                file_path="ABC1234.txt",  # 设置文件路径
                text="Operating voltage 3.3V",  # 设置正文
                chip_model="ABC1234",  # 设置芯片型号
            )  # 结束 chunk 构造
        ]  # 结束 chunk 列表
        client = CountingEmbeddingClient()  # 创建会统计调用次数的 embedding 客户端
        LocalRetriever(chunks, embedding_client=client).search("Operating voltage", "ABC1234")  # 执行检索
        self.assertEqual(client.calls, 1)  # 只允许为问题生成一次 embedding，不能为 chunk 生成


class CountingEmbeddingClient(EmbeddingClient):  # 用于测试调用次数的 embedding 客户端
    def __init__(self) -> None:  # 初始化调用计数
        self.calls = 0  # 保存 embed 调用次数

    def embed(self, text: str) -> list[float]:  # 返回固定向量并累加调用次数
        self.calls += 1  # 累加调用次数
        return [1.0, 0.0]  # 返回固定二维向量
