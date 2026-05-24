import unittest  # 导入标准库单元测试框架

from app.models import Evidence  # 导入问答流程共享的数据结构
from app.qa.answer_generator import AnswerGenerator  # 导入问题解析或答案生成组件
from app.qa.question_parser import QuestionParser  # 导入问题解析或答案生成组件


class AnswerGeneratorTest(unittest.TestCase):  # 定义 AnswerGeneratorTest 类
    def test_answer_generator_refuses_without_evidence(self):  # 定义测试用例 test_answer_generator_refuses_without_evidence
        question = QuestionParser().parse("芯片型号：ABC1234 问题：工作电压是多少？")  # 保存去除型号后的问题正文
        answer = AnswerGenerator().generate(question, [])  # 保存 answer 的处理结果
        self.assertIn("资料不足", answer.conclusion)  # 断言测试结果符合预期

    def test_answer_generator_uses_local_evidence(self):  # 定义测试用例 test_answer_generator_uses_local_evidence
        question = QuestionParser().parse("芯片型号：ABC1234 问题：工作电压是多少？")  # 保存去除型号后的问题正文
        evidence = [  # 保存当前流程中的 evidence 数据
            Evidence(  # 执行当前业务逻辑
                source_type="local",  # 标记证据来源类型
                file_name="ABC1234.txt",  # 保存资料文件名
                page_number=1,  # 保存 PDF 页码
                quote="Operating voltage: 2.7V to 5.5V",  # 保存可引用的原文片段
            )  # 结束当前多行结构
        ]  # 结束当前多行结构
        answer = AnswerGenerator().generate(question, evidence)  # 保存 answer 的处理结果
        markdown = answer.to_markdown()  # 保存 markdown 的处理结果
        self.assertIn("2.7V to 5.5V", markdown)  # 断言测试结果符合预期
        self.assertIn("本地资料证据", markdown)  # 断言测试结果符合预期

    def test_answer_generator_prefers_working_voltage_over_destructive_voltage(self):  # 定义测试用例 test_answer_generator_prefers_working_voltage_over_destructive_voltage
        question = QuestionParser().parse("芯片型号：CV1800B 问题：工作电压是多少？")  # 保存去除型号后的问题正文
        evidence = [  # 保存当前流程中的 evidence 数据
            Evidence(  # 执行当前业务逻辑
                source_type="local",  # 标记证据来源类型
                file_name="CV1800B.pdf",  # 保存资料文件名
                page_number=40,  # 保存 PDF 页码
                quote="破坏性电压 VDDC Core power 1.05V V",  # 保存可引用的原文片段
            ),  # 结束当前多行结构
            Evidence(  # 执行当前业务逻辑
                source_type="local",  # 标记证据来源类型
                file_name="CV1800B.pdf",  # 保存资料文件名
                page_number=27,  # 保存 PDF 页码
                quote="工作电压 内核电压为 0.9V IO 电压为 1.8V 及 3.0V DDR 电压如下表. CV180ZB/CV1800B = 1.8V CV1801B = 1.35V",  # 保存可引用的原文片段
            ),  # 结束当前多行结构
        ]  # 结束当前多行结构
        answer = AnswerGenerator().generate(question, evidence)  # 保存 answer 的处理结果
        self.assertIn("内核电压为 0.9V", answer.conclusion)  # 断言测试结果符合预期
        self.assertIn("IO 电压为 1.8V 及 3.0V", answer.conclusion)  # 断言测试结果符合预期
        self.assertIn("DDR 电压为 1.8V", answer.conclusion)  # 断言测试结果符合预期

    def test_answer_generator_concludes_camera_capacity(self):  # 验证摄像头数量和分辨率问题会生成明确结论
        question = QuestionParser().parse("芯片型号：CV1800B 问题：可以接几个200万分辨率的摄像头？")  # 构造包含芯片型号和摄像头能力的问题
        evidence = [  # 准备用于判断摄像头能力的本地资料证据
            Evidence(  # 构造 VI/MIPI 接口能力证据
                source_type="local",  # 标记证据来自本地资料
                file_name="CV1800B.pdf",  # 保存资料文件名
                page_number=324,  # 保存 PDF 页码
                quote="MIPI Rx可支持一路 sensor 数据输入。Sensor 最大支持 5M(2688x1944, 2880x1620) @20fps 线性输入。",  # 保存可引用的原文片段
            )  # 结束 VI/MIPI 证据对象
        ]  # 结束证据列表
        answer = AnswerGenerator().generate(question, evidence)  # 生成摄像头能力回答
        self.assertIn("可以接 1 个 200 万像素 MIPI 摄像头", answer.conclusion)  # 断言结论明确回答能接几个
        self.assertIn("单一 sensor 能力高于 2MP", answer.conclusion)  # 断言结论说明 2MP 能力来源

    def test_answer_generator_checks_full_video_pipeline_for_5mp_sensor(self):  # 验证 5MP sensor 问题会结合输入、ISP 和编码能力
        question = QuestionParser().parse("芯片型号：CV1843H 问题：可以接几个5Mp的sensor，帧率是25fps")  # 构造 5MP sensor 帧率问题
        evidence = [  # 准备覆盖完整视频链路的证据
            Evidence(  # 构造整体规格和编码性能证据
                source_type="local",  # 标记证据来自本地资料
                file_name="CV1843H.pdf",  # 保存资料文件名
                page_number=15,  # 保存 PDF 页码
                quote="H.265 编码总性能 : 9M@25fps 视频输入接口 支持同时三路视频输入 (mipi 2L+2L+DVP) 支持最大宽度为 3840 , 最大分辨率 8M(3840x2160) ISP 与图像处理",  # 保存本地原文摘录
            ),  # 结束整体规格证据
            Evidence(  # 构造 ISP 处理能力证据
                source_type="local",  # 标记证据来自本地资料
                file_name="CV1843H.pdf",  # 保存资料文件名
                page_number=19,  # 保存 PDF 页码
                quote="最大 performance 支持 5M(2880x1620) 30fps HDR，支持最大 8M(3840x2160) 30fps SDR real time online 处理。",  # 保存 ISP 性能摘录
            ),  # 结束 ISP 证据
        ]  # 结束证据列表
        answer = AnswerGenerator().generate(question, evidence)  # 生成回答
        self.assertIn("建议按 1 路 5MP@25fps sensor 设计", answer.conclusion)  # 断言编码瓶颈下给出一路结论
        self.assertIn("两路 5MP@25fps 合计约 10M@25fps", answer.conclusion)  # 断言说明两路超出编码总性能

    def test_requirement_evaluation_reports_unsatisfied_item(self):  # 验证需求评估会指出具体不满足项
        question = QuestionParser().parse("芯片型号：CV1843H 问题：客户项目需求明细：2路5MP sensor，帧率25fps；H.265编码")  # 构造客户需求评估问题
        evidence = [  # 准备覆盖编码瓶颈的证据
            Evidence(  # 构造规格证据
                source_type="local",  # 标记本地证据
                file_name="CV1843H.pdf",  # 保存文件名
                page_number=15,  # 保存页码
                quote="H.265 编码总性能 : 9M@25fps 视频输入接口 支持同时三路视频输入 (mipi 2L+2L+DVP) 支持最大宽度为 3840 , 最大分辨率 8M(3840x2160) ISP 与图像处理",  # 保存证据原文
            )  # 结束证据对象
        ]  # 结束证据列表
        answer = AnswerGenerator().generate(question, evidence)  # 生成需求评估答案
        self.assertIn("不能满足客户的要求", answer.conclusion)  # 断言结论明确不满足
        self.assertIn("2路5MP sensor，帧率25fps", answer.conclusion)  # 断言指出具体不满足项
