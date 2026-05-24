import unittest  # 导入标准库单元测试框架

from app.qa.context_planner import build_related_queries, infer_related_modules  # 导入问题相关模块规划工具


class ContextPlannerTest(unittest.TestCase):  # 定义上下文规划测试类
    def test_camera_question_expands_to_video_pipeline_modules(self):  # 验证摄像头问题会自动扩展到完整视频链路
        question = "CV1843H可以接几个5Mp的sensor，帧率是25fps"  # 构造用户未显式提到 ISP 和编码的问题
        queries = build_related_queries(question)  # 生成扩展检索词
        modules = infer_related_modules(question)  # 推断相关芯片模块
        self.assertTrue(any("视频输入" in query for query in queries))  # 断言扩展查询包含视频输入
        self.assertTrue(any("ISP" in query for query in queries))  # 断言扩展查询包含 ISP
        self.assertTrue(any("H.265" in query for query in queries))  # 断言扩展查询包含编码能力
        self.assertIn("视频输入接口 VI/VIVO/MIPI Rx", modules)  # 断言纠错规则补充 VIVO/VI/MIPI 输入模块
        self.assertIn("ISP 与图像处理", modules)  # 断言模块规划包含 ISP
        self.assertIn("视频编解码 VCU/H.264/H.265", modules)  # 断言纠错规则补充 H.264/H.265 编解码模块
