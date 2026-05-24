import tempfile  # 创建测试临时目录
import unittest  # 导入标准库单元测试框架
from pathlib import Path  # 统一处理测试文件路径

from app.requirements_parser import RequirementDocumentParser, format_requirement_items_markdown, normalize_requirement_text  # 导入客户需求解析器和中间格式工具


class RequirementDocumentParserTest(unittest.TestCase):  # 定义客户需求解析器测试类
    def test_parse_csv_requirements(self):  # 验证 CSV 需求表可以被解析为文本
        with tempfile.TemporaryDirectory() as temp_dir:  # 创建临时目录隔离测试文件
            path = Path(temp_dir) / "requirements.csv"  # 构造 CSV 文件路径
            path.write_text("项目,需求\n摄像头,2路5MP@25fps\n编码,H.265\n", encoding="utf-8")  # 写入测试需求
            text = RequirementDocumentParser().parse_path(path)  # 解析 CSV 需求文件
            self.assertIn("摄像头 | 2路5MP@25fps", text)  # 断言保留表格列内容
            self.assertIn("编码 | H.265", text)  # 断言保留编码需求

    def test_parse_uploaded_text_file(self):  # 验证上传 TXT 文件内容可以解析
        content = "客户需求：1路5MP sensor，H.265编码".encode("utf-8")  # 构造上传文本字节
        import base64  # 导入 base64 编码工具
        text = RequirementDocumentParser().parse_upload("requirements.txt", base64.b64encode(content).decode("ascii"))  # 解析上传文件内容
        self.assertIn("客户需求", text)  # 断言成功解析上传文本

    def test_xls_extension_is_supported(self):  # 验证 xls 扩展名进入支持列表
        with tempfile.TemporaryDirectory() as temp_dir:  # 创建临时目录隔离测试文件
            path = Path(temp_dir) / "requirements.xls"  # 构造 xls 文件路径
            path.write_bytes(b"not a real xls")  # 写入占位字节以触发 xls 解析路径
            try:  # 兼容测试环境可能未安装 xlrd 或文件内容不是合法 xls
                RequirementDocumentParser().parse_path(path)  # 尝试解析 xls 文件
            except Exception as exc:  # 捕获解析异常
                self.assertNotIn("Unsupported requirement file type", str(exc))  # 断言不是格式不支持错误

    def test_normalize_requirement_text_to_intermediate_items(self):  # 验证需求文本会整理为统一中间格式
        text = "新人脸面板产品规划\nCPU | 1.5GHZ\n视频输入 | 2M | MIPI接口\n10M/100M自适应以太网"  # 构造包含标题和需求项的文本
        items = normalize_requirement_text(text)  # 转换为需求中间格式
        markdown = format_requirement_items_markdown(items)  # 渲染中间格式 Markdown
        self.assertEqual(items[0].item_id, "REQ-001")  # 断言生成稳定需求编号
        self.assertEqual(items[0].category, "新人脸面板产品规划")  # 断言标题成为分类
        self.assertIn("CPU", markdown)  # 断言 Markdown 包含 CPU 需求
        self.assertIn("MIPI接口", markdown)  # 断言 Markdown 保留接口备注
