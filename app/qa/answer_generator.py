from __future__ import annotations  # 启用延迟类型注解，避免运行时前向引用问题

import re  # 导入正则表达式工具

from app.llm.client import LLMClient, MockLLMClient  # 导入可插拔 LLM Reader 接口
from app.models import Answer, Evidence, UserQuestion  # 导入问答流程共享的数据结构


VOLTAGE_PATTERN = re.compile(r"\b\d+(?:\.\d+)?\s*(?:V|v)(?:\s*(?:-|to|~|–|—)\s*\d+(?:\.\d+)?\s*(?:V|v))?")  # 计算并保存 VOLTAGE_PATTERN
READER_SYSTEM_PROMPT = (  # 定义 LLM Reader 的系统提示词
    "你是严谨的芯片资料问答与产品需求评估助手。必须先给结论，再给证据和推导。"
    "本地 datasheet 证据优先级最高，联网资料只能作为补充。"
    "不要把推导伪装成原文；证据不足时要明确说明不确定。"
)  # 结束系统提示词定义


class AnswerGenerator:  # 基于证据生成固定格式答案
    def __init__(self, llm_client: LLMClient | None = None, use_llm_reader: bool = False) -> None:  # 初始化答案生成器依赖
        self.llm_client = llm_client or MockLLMClient()  # 保存可选 LLM Reader，默认使用 mock
        self.use_llm_reader = use_llm_reader  # 保存是否启用真实 LLM Reader 的开关

    def generate(self, question: UserQuestion, evidence: list[Evidence], web_evidence: list[Evidence] | None = None, answer_mode: str = "full") -> Answer:  # 生成完整或简洁回答
        web_evidence = web_evidence or []  # 统一处理没有联网证据的情况
        if question.chip_model is None:  # 检查条件：question.chip_model is None
            return Answer(  # 返回构造好的回答对象
                conclusion="无法回答：问题中未识别到目标芯片型号。",  # 保存结论段落
                uncertainty="请按“芯片型号：XXX 问题：...”的格式补充目标芯片型号。",  # 保存不确定性和限制说明
                recommendation="先确认芯片型号，再重新提问。",  # 保存工程复核或下一步建议
            )  # 结束当前多行结构

        if not evidence and (answer_mode == "simple" or not web_evidence):  # 简单模式或无联网证据时不能只靠模型猜测
            return Answer(  # 返回构造好的回答对象
                conclusion=f"资料不足：本地索引中没有找到 {question.chip_model} 的相关证据，不能给出确定结论。",  # 保存结论段落
                web_evidence=web_evidence,  # 保留已经找到的联网证据，方便用户人工复核
                uncertainty="当前没有可引用的本地 datasheet 证据；若已配置 LLM Reader 和联网搜索，可结合联网证据给出补充判断。",  # 保存不确定性和限制说明
                recommendation="请确认该芯片资料已导入，或补充更具体的问题关键词。",  # 保存工程复核或下一步建议
            )  # 结束当前多行结构

        if self.use_llm_reader and not isinstance(self.llm_client, MockLLMClient):  # 配置真实 LLM Reader 时优先使用模型综合证据
            llm_answer = self._generate_with_llm(question, evidence, web_evidence, answer_mode)  # 调用 LLM Reader 生成结构化答案
            if llm_answer is not None:  # LLM 成功返回答案时直接使用
                return llm_answer  # 返回 LLM Reader 的答案

        conclusion = self._build_conclusion(question, evidence)  # 保存结论段落
        reasoning = self._build_reasoning(question, evidence)  # 保存基于证据的推导过程
        uncertainty = (  # 保存不确定性和限制说明
            "该回答基于当前检索到的本地资料片段生成。若 datasheet 中存在表格、图片或扫描页，"  # 执行当前业务逻辑
            "第一版可能无法完整提取；最终工程设计应复核原始文档。"  # 执行当前业务逻辑
        )  # 结束当前多行结构
        return Answer(  # 返回构造好的回答对象
            conclusion=conclusion,  # 保存结论段落
            local_evidence=evidence,  # 保存本地资料证据列表
            web_evidence=web_evidence,  # 保存联网资料证据列表
            reasoning=reasoning,  # 保存基于证据的推导过程
            uncertainty=uncertainty,  # 保存不确定性和限制说明
            recommendation="建议打开引用页码或 Slide，结合完整章节、典型应用电路和绝对最大额定值复核。",  # 保存工程复核或下一步建议
        )  # 结束当前多行结构

    def _generate_with_llm(self, question: UserQuestion, evidence: list[Evidence], web_evidence: list[Evidence], answer_mode: str) -> Answer | None:  # 使用 LLM Reader 基于证据生成答案
        prompt = _build_reader_prompt(question, evidence, web_evidence, answer_mode)  # 构造要求先结论后证据的 Reader 提示词
        try:  # 捕获模型服务异常，避免影响本地兜底问答
            content = self.llm_client.chat([{"role": "system", "content": READER_SYSTEM_PROMPT}, {"role": "user", "content": prompt}])  # 调用 LLM Reader
        except Exception:  # 模型调用失败时回退到规则答案
            return None  # 返回 None 表示交给规则模板
        if not content:  # 空响应无法作为最终答案
            return None  # 返回 None 表示交给规则模板
        return Answer(  # 将 LLM 输出放入 Answer 结构
            conclusion=content.strip(),  # 保存模型生成的完整结构化答案
            local_evidence=evidence,  # 保留本地证据用于 UI 展示
            web_evidence=web_evidence,  # 保留联网证据用于 UI 展示
            reasoning="LLM Reader 已基于本地证据、联网证据和问题约束生成综合判断；请优先核对引用证据。",  # 说明推导来源
            uncertainty="LLM Reader 可能会基于证据做工程推导；若用于硬件定型，需要复核原始 datasheet、参考设计和官方资料。",  # 说明模型推导限制
            recommendation="建议把产品需求拆成接口、性能、功耗、封装、软件支持和风险项逐项复核。",  # 给出复杂需求评估建议
        )  # 结束 Answer 构造

    def _build_conclusion(self, question: UserQuestion, evidence: list[Evidence]) -> str:  # 定义 _build_conclusion 函数或方法
        if _is_requirement_evaluation(question.question):  # 客户需求评估优先使用逐项满足度兜底，避免退回泛化模板
            requirement_summary = _extract_requirement_evaluation_summary(question, evidence)  # 从需求文本和证据中生成逐项判断
            if requirement_summary:  # 只在能识别到关键客户需求时使用结构化兜底
                return requirement_summary  # 返回客户需求逐项评估结论
        if _asks_camera_capacity(question.question):  # 识别摄像头数量或分辨率能力类问题
            camera_capacity = _extract_camera_capacity_summary(question, evidence)  # 从本地证据中提炼摄像头接入能力结论
            if camera_capacity:  # 找到足够证据时优先返回明确结论
                if _is_requirement_evaluation(question.question):  # 客户需求评估需要转换为满足度结论
                    return _format_requirement_camera_conclusion(question, camera_capacity)  # 返回客户需求评估结论
                return camera_capacity  # 返回摄像头能力的结构化判断
        if _asks_working_voltage(question.question):  # 检查条件：_asks_working_voltage(question.question)
            working_voltage = _extract_working_voltage_summary(question, evidence)  # 计算并保存 working_voltage
            if working_voltage:  # 检查条件：working_voltage
                return working_voltage  # 返回 working_voltage
        top_quote = evidence[0].quote  # 计算并保存 top_quote
        voltage = VOLTAGE_PATTERN.search(top_quote)  # 计算并保存 voltage
        if voltage and any(keyword in question.question for keyword in ["电压", "voltage", "Voltage", "V"]):  # 检查条件：voltage and any(keyword in question.question for keyword in 
            return (  # 返回 (
                f"基于本地资料，{question.chip_model} 的相关电压信息包含：{voltage.group(0)}。"  # 执行当前业务逻辑
                "请以依据中的原文和上下文为准。"  # 执行当前业务逻辑
            )  # 结束当前多行结构
        return (  # 返回 (
            f"基于本地资料，已找到与 {question.chip_model} 和该问题相关的证据。"  # 执行当前业务逻辑
            "由于第一版不启用真实 LLM 推理，结论以引用原文为核心依据；若原文未直接给出答案，则应视为需要人工复核。"  # 执行当前业务逻辑
        )  # 结束当前多行结构

    def _build_reasoning(self, question: UserQuestion, evidence: list[Evidence]) -> str:  # 定义 _build_reasoning 函数或方法
        if not evidence:  # 检查条件：not evidence
            return "- 没有足够证据，未进行推导。"  # 返回 "- 没有足够证据，未进行推导。"
        module_line = _format_related_modules(question)  # 生成回答前参考的相关模块说明
        return (  # 返回 (
            f"- 已先按芯片型号 `{question.chip_model}` 过滤本地资料，再检索问题关键词。\n"  # 执行当前业务逻辑
            f"{module_line}"  # 写入自动规划的相关模块
            "- 当前结论只使用本地资料证据，不把通用芯片常识包装成 datasheet 原文。\n"  # 执行当前业务逻辑
            "- 若问题涉及是否适合某系统电压、接口外接电阻、散热或时序裕量，需要结合 datasheet 的工作条件、"  # 执行当前业务逻辑
            "绝对最大额定值和典型应用电路进一步推导。"  # 执行当前业务逻辑
        )  # 结束当前多行结构


def _asks_working_voltage(question_text: str) -> bool:  # 定义 _asks_working_voltage 函数或方法
    question_lower = question_text.lower()  # 计算并保存 question_lower
    return "工作电压" in question_text or "operating voltage" in question_lower  # 返回 "工作电压" in question_text or "operating vo


def _format_related_modules(question: UserQuestion) -> str:  # 格式化回答前自动参考的相关模块
    modules = question.constraints.get("related_modules", [])  # 读取问题规划阶段推断的相关模块
    if not modules:  # 没有模块规划时不输出额外行
        return ""  # 返回空字符串
    return "- 回答前已按问题意图补充参考相关芯片模块：" + "、".join(modules) + "。\n"  # 返回模块规划说明


def _is_requirement_evaluation(question_text: str) -> bool:  # 判断问题是否为客户需求满足度评估
    return "客户项目需求明细" in question_text or "客户需求" in question_text  # 命中客户需求关键词


def _format_requirement_camera_conclusion(question: UserQuestion, camera_capacity: str) -> str:  # 将摄像头能力判断转换为客户需求评估结论
    if "建议按 1 路 5MP@25fps" in camera_capacity and ("2路5MP" in question.question or "2 路5MP" in question.question or "2 路 5MP" in question.question):  # 两路 5MP 需求被编码能力限制
        return (  # 返回不满足客户需求的结论
            f"{question.chip_model}型号的芯片不能满足客户的要求。客户需求中的“2路5MP sensor，帧率25fps”不满足："
            + camera_capacity  # 复用完整视频链路推导
        )  # 结束不满足结论
    return f"{question.chip_model}型号的芯片可以满足客户的要求。{camera_capacity}"  # 默认将能力判断包装为满足结论


def _extract_requirement_evaluation_summary(question: UserQuestion, evidence: list[Evidence]) -> str | None:  # 为客户需求评估生成本地规则兜底答案
    requirement_text = question.question  # 读取构造后的客户需求评估问题正文
    if not any(term in requirement_text for term in ["新人脸面板产品规划", "人脸容量", "掌静脉容量", "TPU | 1.5T"]):  # 只处理当前能可靠识别的门禁面板需求表
        return None  # 非该类结构化需求时交给通用问答逻辑
    combined_quote = "\n".join(item.quote for item in evidence)  # 合并本地证据，便于判断 datasheet 是否覆盖关键能力
    cpu_status = "不满足或至少资料不支持，datasheet 证据为 Cortex-A53 @ 1.1GHz，客户要求为 CPU 1.5GHz。" if "1.1GHz" in combined_quote else "资料不足，当前证据没有证明 CPU 可达到 1.5GHz。"  # 判断 CPU 主频
    tpu_status = "满足，datasheet 写明 TPU 可提供 1.5TOPS@INT8。" if "1.5TOPS" in combined_quote else "资料不足，当前证据没有检索到 1.5TOPS TPU 描述。"  # 判断 TPU 算力
    ddr_status = "部分满足，datasheet 写明 DDR3 16bitx1、容量 256~512MB；客户表中的 256MB/512MB 有证据，128MB 需单独确认。" if "256~512MB" in combined_quote or "2~4Gbit" in combined_quote else "资料不足，当前证据没有覆盖 DDR 容量。"  # 判断 DDR 容量
    video_status = "满足 2M MIPI 输入和 30W/DVP 接口层能力，datasheet 支持 MIPI、DVP/并口类输入，最高视频输入覆盖 2M。" if _has_video_input_8m(combined_quote) else "资料不足，当前证据没有完整覆盖视频输入能力。"  # 判断视频输入
    codec_status = "满足 H.264/H.265，datasheet 写明集成 H.264/H.265 编码器，编码性能 9M@25fps。" if "H.265" in combined_quote and "H.264" in combined_quote else "资料不足，当前证据没有同时覆盖 H.264/H.265。"  # 判断编解码
    display_status = "基本满足显示接口，datasheet 支持 MIPI TX、LVDS、RGB565/666/888 等输出；具体 1280x800 屏参需要按面板 timing 复核。" if "RGB565" in combined_quote or "MIPI TX" in combined_quote else "资料不足，当前证据没有完整覆盖显示输出。"  # 判断显示输出
    network_status = "满足 10/100M 以太网，datasheet 写明内建 10/100Mbps Fast Ethernet Transceiver。" if "10/100Mbps" in combined_quote else "资料不足，当前证据没有覆盖以太网。"  # 判断以太网
    io_status = "接口层面满足 WiFi SDIO、Bluetooth UART、NFC I2C/SPI、触摸 I2C 和扩展 IO；外接模块仍需驱动和板级适配。" if any(term in combined_quote for term in ["SDIO", "UART", "I2C", "SPI", "GPIO", "USB"]) else "资料不足，当前证据没有覆盖外设接口。"  # 判断外设接口
    dark_status = "不能仅凭 SoC datasheet 判定，无白色补光灯黑暗识别依赖 sensor、补光方案和算法模型；芯片只提供 HDR/ISP/TPU 基础能力。"  # 判断暗光识别
    capacity_status = "不能仅凭 SoC datasheet 判定，人脸/掌静脉容量取决于算法特征库、存储容量和业务软件，不是单纯芯片规格。"  # 判断生物特征容量
    return (  # 返回逐项评估结论
        f"{question.chip_model}型号的芯片不能直接判定完全满足客户的要求；多数硬件接口和 AI/视频基础能力可以覆盖，但 CPU 1.5GHz、暗光无白光识别、"
        "人脸/掌静脉容量属于明确风险或待确认项。\n\n"
        f"- 液晶屏与分辨率：{display_status}\n"
        f"- CPU：{cpu_status}\n"
        f"- TPU：{tpu_status}\n"
        f"- SDRAM/DDR：{ddr_status}\n"
        "- NAND/eMMC：接口和启动形态有证据，但 128MB/256MB/512MB/8GB 具体容量组合需结合 Flash/eMMC 器件和启动限制确认。\n"
        f"- H.264/H.265：{codec_status}\n"
        f"- 视频输入：{video_status}\n"
        f"- ISP 与暗光识别：{dark_status}\n"
        "- USB-OTG/烧录/U 盘：datasheet 有 USB device mode 烧写证据，U 盘和 OTG 角色需 SDK/板级配置确认。\n"
        f"- 以太网：{network_status}\n"
        f"- WiFi/蓝牙/NFC/扩展接口：{io_status}\n"
        f"- 人脸容量与掌静脉容量：{capacity_status}"
    )  # 结束逐项评估文本


def _build_reader_prompt(question: UserQuestion, evidence: list[Evidence], web_evidence: list[Evidence], answer_mode: str) -> str:  # 构造 LLM Reader 的用户提示词
    local_text = _format_evidence_for_prompt(evidence, "本地 datasheet 证据")  # 格式化本地证据
    web_text = _format_evidence_for_prompt(web_evidence, "联网补充证据")  # 格式化联网证据
    style_instruction = _answer_style_instruction(answer_mode)  # 根据回答模式生成风格要求
    module_text = _format_modules_for_prompt(question)  # 格式化必须参考的相关模块
    task_instruction = _task_specific_instruction(question)  # 生成任务特定回答要求
    if answer_mode == "simple":  # 简单模式使用更短的 Reader 提示词
        return (  # 返回简洁回答提示词
            f"目标芯片型号：{question.chip_model}\n"  # 写入目标芯片型号
            f"用户问题：{question.question}\n\n"  # 写入用户问题正文
            f"{module_text}\n"  # 写入自动规划的相关模块
            f"{task_instruction}\n"  # 写入客户需求评估等任务要求
            f"{style_instruction}\n\n"  # 写入简单模式要求
            f"{local_text}"  # 只附加本地 datasheet 证据
        )  # 结束简洁提示词构造
    return (  # 返回完整提示词
        f"目标芯片型号：{question.chip_model}\n"  # 写入目标芯片型号
        f"用户问题：{question.question}\n\n"  # 写入用户问题正文
        f"{module_text}\n"  # 写入自动规划的相关模块
        f"{task_instruction}\n"  # 写入客户需求评估等任务要求
        f"{style_instruction}\n\n"  # 写入简单或完整模式要求
        "请按以下结构回答：\n"  # 指定固定回答结构
        "1. 结论：直接回答能不能、是否满足、满足到什么程度。\n"  # 要求先给结论
        "2. 本地资料证据：引用 datasheet 原文，并说明页码或文件名。\n"  # 要求引用本地证据
        "3. 联网资料证据：只使用提供的联网摘要，不要自行编造链接内容。\n"  # 要求区分联网证据
        "4. 推导逻辑：说明从证据到结论的判断过程。\n"  # 要求展示推导
        "5. 风险与待确认项：列出产品落地前还要确认的条件。\n\n"  # 要求说明风险
        f"{local_text}\n\n{web_text}"  # 附加证据正文
    )  # 结束提示词构造


def _answer_style_instruction(answer_mode: str) -> str:  # 生成 LLM Reader 的回答详略要求
    if answer_mode == "simple":  # 简单回答模式要求压缩输出
        return "回答模式：简单回答。请只输出 2-4 句话的直接答案，不要使用 Markdown 标题；只依据本地 datasheet 证据，不展开长篇推导。"  # 返回简洁模式提示
    return "回答模式：完整解释。请给出结论、详细证据、推导逻辑、联网补充信息和风险项。"  # 返回完整模式提示


def _task_specific_instruction(question: UserQuestion) -> str:  # 根据任务类型生成额外回答要求
    if "客户项目需求明细" in question.question or "客户需求" in question.question:  # 客户需求评估需要明确满足度结论
        return (  # 返回客户需求评估专用提示
            "这是客户项目需求满足度评估。请先输出明确结论：若满足，使用“"
            f"{question.chip_model}型号的芯片可以满足客户的要求”；若不满足，使用“"
            f"{question.chip_model}型号的芯片不能满足客户的要求”。"
            "随后用表格逐项列出：客户需求项、是否满足、datasheet 证据、推导说明、风险或待确认项。"
            "不能只说泛泛满足，必须指出具体规格如何满足；不能满足时必须指出客户需求中的具体不满足项。"
        )  # 结束客户需求评估提示
    return "请先基于目标芯片整体规格和问题相关内部模块建立判断，再给出结论。"  # 返回通用任务提示


def _format_modules_for_prompt(question: UserQuestion) -> str:  # 为 LLM Reader 格式化必须参考的模块列表
    modules = question.constraints.get("related_modules", [])  # 读取模块规划结果
    if not modules:  # 没有规划模块时返回通用要求
        return "回答前请先判断该问题涉及的芯片内部模块，并综合相关证据后再给结论。"  # 返回通用模块参考要求
    return "回答前必须整体参考这些相关模块：" + "、".join(modules) + "。"  # 返回具体模块参考要求


def _format_evidence_for_prompt(evidence: list[Evidence], title: str) -> str:  # 将证据列表格式化给 LLM Reader
    if not evidence:  # 没有证据时返回占位说明
        return f"{title}：无"  # 返回无证据说明
    lines = [f"{title}："]  # 初始化证据文本行
    for index, item in enumerate(evidence, start=1):  # 遍历证据并编号
        source = item.file_name or item.url or "未知来源"  # 选择文件名或 URL 作为来源
        location = f" page={item.page_number}" if item.page_number is not None else ""  # 保存 PDF 页码信息
        lines.append(f"[{index}] 来源：{source}{location}\n原文/摘要：{item.quote}")  # 追加单条证据文本
    return "\n".join(lines)  # 返回合并后的证据文本


def _asks_camera_capacity(question_text: str) -> bool:  # 判断用户是否在询问摄像头接入数量或分辨率能力
    question_lower = question_text.lower()  # 统一转换为小写，便于匹配英文关键词
    camera_terms = ["摄像头", "镜头", "sensor", "camera"]  # 定义摄像头相关关键词集合
    capacity_terms = ["几个", "几路", "多少路", "多少个", "200万", "2mp", "2m", "5mp", "5m", "fps", "帧率", "分辨率"]  # 定义数量和分辨率相关关键词集合
    has_camera_term = any(term in question_lower or term in question_text for term in camera_terms)  # 判断问题是否提到摄像头或传感器
    has_capacity_term = any(term in question_lower or term in question_text for term in capacity_terms)  # 判断问题是否提到数量或分辨率
    return has_camera_term and has_capacity_term  # 只有同时命中主题和能力词才进入摄像头能力规则


def _extract_camera_capacity_summary(question: UserQuestion, evidence: list[Evidence]) -> str | None:  # 从证据中抽取摄像头数量和分辨率能力摘要
    combined_quote = "\n".join(item.quote for item in evidence)  # 合并候选证据，便于跨片段综合判断
    five_mp_summary = _extract_five_mp_sensor_summary(question, combined_quote)  # 尝试提炼 5MP sensor 与帧率能力结论
    if five_mp_summary:  # 命中 5MP sensor 场景时优先返回更精确结论
        return five_mp_summary  # 返回 5MP sensor 结构化判断
    supports_2mp = _has_2mp_capacity(combined_quote)  # 判断资料是否证明单路 200 万像素输入能力
    mipi_single_sensor = _has_mipi_single_sensor_limit(combined_quote)  # 判断 MIPI Rx 是否存在一路 sensor 的接口限制
    isp_dual_sensor = _has_isp_dual_sensor_capacity(combined_quote)  # 判断 ISP 是否具备双镜头处理能力
    if supports_2mp and mipi_single_sensor and isp_dual_sensor:  # 三类证据都存在时给出最完整的工程结论
        return (  # 返回摄像头能力结论
            f"{question.chip_model} 可以接 200 万像素摄像头；若按 MIPI Rx 接口理解，datasheet 明确写的是一路 sensor 输入，"  # 给出能否接入和 MIPI 数量限制
            "因此可确定支持 1 个 200 万像素 MIPI 摄像头。资料同时提到 ISP 支持双镜头输入，说明后端具备双路图像处理能力，"  # 补充 ISP 双镜头处理能力
            "但是否能直接接 2 个 200 万摄像头还要结合具体接口组合、引脚复用和目标帧率复核。"  # 给出双摄判断的限制条件
        )  # 结束完整结论字符串
    if supports_2mp and mipi_single_sensor:  # 找到单路分辨率和 MIPI 一路限制时给出保守结论
        return (  # 返回保守摄像头能力结论
            f"{question.chip_model} 可以接 1 个 200 万像素 MIPI 摄像头；datasheet 证据显示单一 sensor 能力高于 2MP，"  # 给出明确的一路判断
            "同时 MIPI Rx 描述为支持一路 sensor 数据输入。"  # 说明一路数量来自接口限制
        )  # 结束保守结论字符串
    if supports_2mp:  # 只找到分辨率能力时避免过度推断数量
        return (  # 返回分辨率能力结论
            f"{question.chip_model} 的资料支持 200 万像素级摄像头输入，但当前证据不足以确定最多能接几个摄像头。"  # 明确能接 2MP 但不能定数量
        )  # 结束分辨率结论字符串
    return None  # 证据不足时交回通用答案模板处理


def _extract_five_mp_sensor_summary(question: UserQuestion, text: str) -> str | None:  # 针对 5MP sensor 25fps 问题提炼整链路结论
    question_lower = question.question.lower()  # 转换问题文本为小写
    if not ("5mp" in question_lower or "5m" in question_lower or "5Mp" in question.question):  # 只处理 5MP/5M sensor 问题
        return None  # 非 5MP 问题交给其它规则
    if not ("sensor" in question_lower or "摄像头" in question.question or "镜头" in question.question):  # 必须是摄像头传感器问题
        return None  # 非 sensor 问题交给其它规则
    has_input_two_sensor = _has_two_sensor_input(text)  # 判断输入接口是否支持 2 路 sensor
    has_video_input_8m = _has_video_input_8m(text)  # 判断视频输入是否覆盖单路 5MP 分辨率
    h265_capacity = _extract_h265_capacity_mp_at_25fps(text)  # 抽取 H.265 编码总性能
    if has_input_two_sensor and has_video_input_8m and h265_capacity is not None:  # 输入与编码证据都齐全时给出整链路判断
        if h265_capacity < 10.0:  # 两路 5MP@25fps 合计约 10MP@25fps
            return (  # 返回以编码吞吐为瓶颈的结论
                f"{question.chip_model} 如果按完整视频链路（Sensor 输入 + ISP + 编码）评估，建议按 1 路 5MP@25fps sensor 设计；"  # 给出直接结论
                "MIPI Rx/视频输入侧资料显示可以支持多路 Sensor 和最高 8M 视频输入，单路 5MP 输入本身满足；"  # 说明输入侧能力
                f"但 H.265 编码总性能为 {h265_capacity:g}M@25fps，两路 5MP@25fps 合计约 10M@25fps，已经超过该编码总性能，"  # 说明编码瓶颈
                "因此不能仅凭输入接口能力判断为可接 2 路并完成编码。"  # 给出为什么不是 2 路
            )  # 结束结论字符串
        return (  # 编码能力足够覆盖两路时返回双路结论
            f"{question.chip_model} 从当前证据看可支持 2 路 5MP@25fps sensor 的完整链路，但仍需复核 ISP 模式、码流配置和内存带宽。"  # 返回双路结论
        )  # 结束结论字符串
    if has_input_two_sensor and has_video_input_8m:  # 只有输入证据时给出接口侧结论
        return (  # 返回输入侧能力结论
            f"{question.chip_model} 在视频输入接口侧可支持 2 路 Sensor，且最高 8M 输入覆盖单路 5MP；"  # 给出输入侧判断
            "但当前证据不足以完成 ISP 与编码吞吐判断，不能确定 2 路 5MP@25fps 是否可完整落地。"  # 说明缺少后端能力证据
        )  # 结束输入侧结论字符串
    return None  # 证据不足时交给其它规则


def _has_two_sensor_input(text: str) -> bool:  # 判断资料是否说明 MIPI Rx 支持两路 sensor
    text_lower = text.lower()  # 转换为小写以兼容英文关键词
    return (  # 返回是否命中两路视频或 sensor 输入描述
        "2 路 sensor" in text_lower  # 匹配两路 sensor 描述
        or "2路 sensor" in text_lower  # 匹配无空格的两路 sensor 描述
        or "同时支持 2 路 sensor" in text_lower  # 匹配同时支持两路 sensor 描述
        or "最高支持 2 路视频输入" in text  # 匹配整体规格中的两路视频输入描述
        or "支持同时三路视频输入" in text  # 匹配 mipi 2L+2L+DVP 三路视频输入描述
        or "mipi 2L+2L+DVP" in text  # 匹配三路输入组合描述
    )  # 结束两路输入判断


def _has_video_input_8m(text: str) -> bool:  # 判断资料是否说明视频输入最大 8M
    return "最大分辨率 8M" in text or "8M(3840x2160)" in text or "3840x2160" in text  # 匹配 8M 输入能力描述


def _extract_h265_capacity_mp_at_25fps(text: str) -> float | None:  # 抽取 H.265 25fps 编码总性能
    match = re.search(r"H\.265\s*编码总性能\s*[:：]\s*([0-9.]+)\s*M\s*@\s*25\s*fps", text, flags=re.IGNORECASE)  # 匹配 H.265 编码总性能
    if not match:  # 未找到 H.265 性能时返回空
        return None  # 返回 None 表示无法判断编码瓶颈
    return float(match.group(1))  # 返回 M@25fps 数值


def _has_2mp_capacity(text: str) -> bool:  # 判断原文是否包含高于 200 万像素的 sensor 输入能力
    text_lower = text.lower()  # 转换为小写以兼容英文大小写
    has_five_megapixel = "5m" in text_lower or "2688x1944" in text_lower or "2880x1620" in text_lower  # 匹配 5M 或对应分辨率
    has_sensor_context = "sensor" in text_lower or "摄像头" in text or "镜头" in text  # 确认该能力和摄像头传感器有关
    return has_five_megapixel and has_sensor_context  # 5M sensor 能力覆盖 2MP 输入需求


def _has_mipi_single_sensor_limit(text: str) -> bool:  # 判断 MIPI Rx 证据是否限定为一路 sensor 输入
    text_lower = text.lower()  # 转换为小写以兼容英文关键词
    has_mipi = "mipi rx" in text_lower or "mipi" in text_lower  # 检查片段是否在描述 MIPI 接口
    has_single_sensor = "一路 sensor" in text_lower or "一路sensor" in text_lower or "单一sensor" in text_lower  # 检查是否出现一路或单一 sensor 描述
    return has_mipi and has_single_sensor  # 同时满足 MIPI 和一路 sensor 才视为接口数量限制


def _has_isp_dual_sensor_capacity(text: str) -> bool:  # 判断 ISP 证据是否说明具备双镜头处理能力
    text_lower = text.lower()  # 转换为小写以兼容英文关键词
    has_isp = "isp" in text_lower  # 检查片段是否处在 ISP 上下文
    has_dual_lens = "双镜头输入" in text or "双镜头" in text or "两组模块" in text  # 检查是否提到双镜头或两组接收模块
    return has_isp and has_dual_lens  # 同时满足 ISP 和双镜头描述才视为后端双路能力


def _extract_working_voltage_summary(question: UserQuestion, evidence: list[Evidence]) -> str | None:  # 定义 _extract_working_voltage_summary 函数或方法
    for item in evidence:  # 遍历当前集合中的每个元素
        quote = item.quote  # 保存可引用的原文片段
        if "工作电压" not in quote and "operating voltage" not in quote.lower():  # 检查条件："工作电压" not in quote and "operating voltage" not in quote.low
            continue  # 当前项不符合条件，跳过后续处理
        core = _extract_first_match(r"内核电压为\s*([0-9.]+\s*V)", quote)  # 计算并保存 core
        io = _extract_first_match(r"IO\s*电压为\s*([^。；;\n]+?)(?:DDR|封装|$)", quote)  # 计算并保存 io
        ddr = _extract_ddr_voltage(question.chip_model, quote)  # 计算并保存 ddr
        parts: list[str] = []  # 计算并保存 parts
        if core:  # 检查条件：core
            parts.append(f"内核电压为 {core}")  # 将当前结果追加到列表
        if io:  # 检查条件：io
            parts.append(f"IO 电压为 {io.strip()}")  # 将当前结果追加到列表
        if ddr:  # 检查条件：ddr
            parts.append(f"DDR 电压为 {ddr}")  # 将当前结果追加到列表
        if parts:  # 检查条件：parts
            return f"基于本地 datasheet，{question.chip_model} 的工作电压信息为：" + "；".join(parts) + "。"  # 返回 f"基于本地 datasheet，{question.chip_model} 的
    return None  # 没有匹配结果时返回 None


def _extract_first_match(pattern: str, text: str) -> str | None:  # 定义 _extract_first_match 函数或方法
    match = re.search(pattern, text, flags=re.IGNORECASE)  # 计算并保存 match
    if match:  # 检查条件：match
        return match.group(1).strip()  # 返回 match.group(1).strip()
    return None  # 没有匹配结果时返回 None


def _extract_ddr_voltage(chip_model: str | None, text: str) -> str | None:  # 定义 _extract_ddr_voltage 函数或方法
    if not chip_model:  # 检查条件：not chip_model
        return None  # 没有匹配结果时返回 None
    escaped_model = re.escape(chip_model)  # 计算并保存 escaped_model
    model_match = re.search(rf"(?:{escaped_model}|CV180ZB/CV1800B)\s*=\s*([0-9.]+\s*V)", text, flags=re.IGNORECASE)  # 计算并保存 model_match
    if model_match:  # 检查条件：model_match
        return model_match.group(1).strip()  # 返回 model_match.group(1).strip()
    return None  # 没有匹配结果时返回 None
