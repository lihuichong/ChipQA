import unittest  # 导入标准库单元测试框架

from app.chips.model_extractor import extract_chip_models  # 导入芯片型号抽取和规范化工具


class ModelExtractorTest(unittest.TestCase):  # 定义 ModelExtractorTest 类
    def test_extract_chip_models_from_text(self):  # 定义测试用例 test_extract_chip_models_from_text
        self.assertEqual(extract_chip_models("CV1800B preliminary datasheet"), ["CV1800B"])  # 断言测试结果符合预期
        self.assertEqual(extract_chip_models("ABC1234-QFN supports I2C"), ["ABC1234-QFN"])  # 断言测试结果符合预期
