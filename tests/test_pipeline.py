import tempfile  # 导入临时目录工具用于测试隔离
import unittest  # 导入标准库单元测试框架
from pathlib import Path  # 导入 Path 以统一处理文件路径

from app.pipeline import IngestPipeline, QaPipeline  # 导入资料导入流程和问答流程
from app.storage import JsonIndexStore  # 导入 JSONL 本地索引存储实现


class PipelineTest(unittest.TestCase):  # 定义 PipelineTest 类
    def test_ingest_and_ask_text_datasheet(self):  # 定义测试用例 test_ingest_and_ask_text_datasheet
        with tempfile.TemporaryDirectory() as temp_dir:  # 打开资源并在结束时自动关闭
            tmp_path = Path(temp_dir)  # 计算并保存 tmp_path
            source = tmp_path / "ABC1234_Datasheet.txt"  # 计算并保存 source
            source.write_text(  # 执行当前业务逻辑
                "ABC1234 Electrical Characteristics\nOperating voltage: 2.7V to 5.5V\n",  # 执行当前业务逻辑
                encoding="utf-8",  # 计算并保存 encoding
            )  # 结束当前多行结构
            store = JsonIndexStore(tmp_path / "index")  # 计算并保存 store

            ingest_result = IngestPipeline(store).ingest(source)  # 计算并保存 ingest_result
            self.assertEqual(ingest_result["chunks"], 1)  # 断言测试结果符合预期
            self.assertIn("ABC1234", ingest_result["chip_models"])  # 断言测试结果符合预期

            answer = QaPipeline(store).ask("芯片型号：ABC1234 问题：Operating voltage 是多少？")  # 保存 answer 的处理结果
            markdown = answer.to_markdown()  # 保存 markdown 的处理结果
            self.assertIn("2.7V to 5.5V", markdown)  # 断言测试结果符合预期

            evaluation = QaPipeline(store).evaluate_requirements("ABC1234", "客户需求：Operating voltage 需要支持 3.3V", answer_mode="simple")  # 执行客户需求评估
            self.assertIn("数据库参考", evaluation.to_markdown(mode="simple"))  # 断言评估结果包含本地证据参考

    def test_ingest_removes_invalid_surrogate_text(self):  # 定义测试用例 test_ingest_removes_invalid_surrogate_text
        with tempfile.TemporaryDirectory() as temp_dir:  # 打开资源并在结束时自动关闭
            tmp_path = Path(temp_dir)  # 计算并保存 tmp_path
            source = tmp_path / "ABC1234_Datasheet.txt"  # 计算并保存 source
            source.write_text("ABC1234 voltage \ud835 3.3V\n", encoding="utf-8", errors="surrogatepass")  # 计算并保存 source.write_text("ABC1234 voltage \ud835 3.3V\n", encoding
            store = JsonIndexStore(tmp_path / "index")  # 计算并保存 store

            ingest_result = IngestPipeline(store).ingest(source)  # 计算并保存 ingest_result
            chunks = store.load_chunks()  # 保存当前流程中的 chunks 数据

            self.assertEqual(ingest_result["chunks"], 1)  # 断言测试结果符合预期
            self.assertNotIn("\ud835", chunks[0].text)  # 断言测试结果符合预期
