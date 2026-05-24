import unittest  # 导入标准库单元测试框架

from app.qa.question_parser import QuestionParser  # 导入问题解析或答案生成组件


class QuestionParserTest(unittest.TestCase):  # 定义 QuestionParserTest 类
    def test_parse_chinese_question_format(self):  # 定义测试用例 test_parse_chinese_question_format
        parsed = QuestionParser().parse("芯片型号：ABC1234 问题：工作电压范围是多少？")  # 计算并保存 parsed
        self.assertEqual(parsed.chip_model, "ABC1234")  # 断言测试结果符合预期
        self.assertIn("工作电压", parsed.question)  # 断言测试结果符合预期
