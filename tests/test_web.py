import json  # 导入 JSON 序列化和反序列化工具
import threading  # 导入当前模块需要的依赖
import unittest  # 导入标准库单元测试框架
from http.server import ThreadingHTTPServer  # 导入标准库 HTTP 服务组件
from urllib.request import Request  # 构造 HTTP 请求对象
from urllib.request import urlopen  # 导入 URL 解析或请求工具

from app.web import DatasheetQaHandler  # 导入当前模块需要的依赖


class WebUiTest(unittest.TestCase):  # 定义 WebUiTest 类
    def test_home_and_status_routes(self):  # 定义测试用例 test_home_and_status_routes
        server = ThreadingHTTPServer(("127.0.0.1", 0), DatasheetQaHandler)  # 计算并保存 server
        thread = threading.Thread(target=server.serve_forever, daemon=True)  # 计算并保存 thread
        thread.start()  # 执行当前业务逻辑
        try:  # 尝试执行可能失败的操作
            host, port = server.server_address  # 计算并保存 host, port
            with urlopen(f"http://{host}:{port}/", timeout=5) as response:  # 打开资源并在结束时自动关闭
                html = response.read().decode("utf-8")  # 计算并保存 html
            self.assertIn("Chip Datasheet QA", html)  # 断言测试结果符合预期
            self.assertIn("简单回答", html)  # 断言页面包含回答模式切换
            self.assertIn("客户需求评估", html)  # 断言页面包含客户需求评估入口
            self.assertIn("需求解析中间格式", html)  # 断言页面展示需求中间格式区域

            with urlopen(f"http://{host}:{port}/api/status", timeout=5) as response:  # 打开资源并在结束时自动关闭
                status = json.loads(response.read().decode("utf-8"))  # 计算并保存 status
            self.assertIn("chunks", status)  # 断言测试结果符合预期
            self.assertIn("chip_models", status)  # 断言测试结果符合预期
        finally:  # 执行当前业务逻辑
            server.shutdown()  # 执行当前业务逻辑
            server.server_close()  # 执行当前业务逻辑

    def test_ask_supports_simple_answer_mode(self):  # 验证问答接口支持简单回答参数
        server = ThreadingHTTPServer(("127.0.0.1", 0), DatasheetQaHandler)  # 启动隔离的测试 HTTP 服务
        thread = threading.Thread(target=server.serve_forever, daemon=True)  # 创建后台服务线程
        thread.start()  # 启动后台服务线程
        try:  # 确保测试结束后关闭服务
            host, port = server.server_address  # 读取测试服务地址
            payload = json.dumps({"question": "芯片型号：ABC1234 问题：工作电压是多少？", "answer_mode": "simple"}).encode("utf-8")  # 构造简单回答请求体
            request = Request(  # 构造 POST 请求对象
                f"http://{host}:{port}/api/ask",  # 指定问答接口地址
                data=payload,  # 写入 JSON 请求体
                headers={"Content-Type": "application/json"},  # 声明 JSON 请求类型
                method="POST",  # 使用 POST 方法
            )  # 结束请求对象构造
            with urlopen(request, timeout=5) as response:  # 发送请求并读取响应
                result = json.loads(response.read().decode("utf-8"))  # 解析 JSON 响应
            self.assertIn("## 答案", result["answer_markdown"])  # 断言响应使用简单回答模板
            self.assertIn("## 数据库参考", result["answer_markdown"])  # 断言响应包含数据库参考
        finally:  # 执行清理逻辑
            server.shutdown()  # 关闭测试 HTTP 服务
            server.server_close()  # 释放服务端口

    def test_evaluate_requirements_accepts_text(self):  # 验证客户需求评估接口接受文本需求
        server = ThreadingHTTPServer(("127.0.0.1", 0), DatasheetQaHandler)  # 启动隔离的测试 HTTP 服务
        thread = threading.Thread(target=server.serve_forever, daemon=True)  # 创建后台服务线程
        thread.start()  # 启动后台服务线程
        try:  # 确保测试结束后关闭服务
            host, port = server.server_address  # 读取测试服务地址
            payload = json.dumps({"chip_model": "ABC1234", "requirement_text": "客户需求：工作电压 3.3V", "answer_mode": "simple"}).encode("utf-8")  # 构造需求评估请求
            request = Request(  # 构造 POST 请求对象
                f"http://{host}:{port}/api/evaluate-requirements",  # 指定需求评估接口地址
                data=payload,  # 写入 JSON 请求体
                headers={"Content-Type": "application/json"},  # 声明 JSON 请求类型
                method="POST",  # 使用 POST 方法
            )  # 结束请求对象构造
            with urlopen(request, timeout=5) as response:  # 发送请求并读取响应
                result = json.loads(response.read().decode("utf-8"))  # 解析 JSON 响应
            self.assertIn("answer_markdown", result)  # 断言返回 Markdown 结果
            self.assertIn("parsed_requirements_markdown", result)  # 断言返回需求解析中间格式
            self.assertIn("REQ-001", result["parsed_requirements_markdown"])  # 断言中间格式包含需求编号
        finally:  # 执行清理逻辑
            server.shutdown()  # 关闭测试 HTTP 服务
            server.server_close()  # 释放服务端口
