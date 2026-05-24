from __future__ import annotations  # 启用延迟类型注解，避免运行时前向引用问题

from app.qa.correction_rules import matching_correction_rules  # 导入用户纠错规则匹配器


def build_related_queries(question: str) -> list[str]:  # 根据问题意图生成需要整体参考的模块检索词
    related_queries = [question]  # 原始问题始终作为第一条检索词
    question_lower = question.lower()  # 统一转换为小写，便于匹配英文关键词
    for rule in matching_correction_rules(question):  # 遍历命中的用户纠错规则
        related_queries.extend(f"{question} {query}" for query in rule.queries)  # 将规则补充查询加入检索计划
    if _is_requirement_evaluation_question(question):  # 客户需求评估需要先覆盖芯片整体规格
        related_queries.extend(_requirement_evaluation_queries(question))  # 追加产品需求评估扩展查询
    if _is_camera_pipeline_question(question, question_lower):  # 摄像头类问题需要覆盖完整视频链路
        related_queries.extend(  # 追加视频链路相关模块检索词
            [  # 定义摄像头链路扩展查询
                f"{question} 视频输入 MIPI Rx Sensor 分辨率 帧率 路 Sensor 输入",  # 覆盖传感器输入和接口能力
                f"{question} ISP 图像处理 多路 输入 分辨率 帧率",  # 覆盖 ISP 和图像处理能力
                f"{question} H.265 H.264 视频编码 编码总性能 25fps",  # 覆盖编解码吞吐瓶颈
                f"{question} 产品概述 整体规格 视频输入接口 ISP 视频编码",  # 覆盖 datasheet 整体规格页
            ]  # 结束扩展查询列表
        )  # 批量追加扩展查询
    return _deduplicate_queries(related_queries)  # 返回去重后的查询列表


def infer_related_modules(question: str) -> list[str]:  # 推断回答前必须参考的芯片内部模块
    question_lower = question.lower()  # 统一转换为小写，便于匹配英文关键词
    modules: list[str] = []  # 保存推断出的相关模块
    for rule in matching_correction_rules(question):  # 遍历命中的用户纠错规则
        modules.extend(rule.modules)  # 将纠错规则要求的模块加入参考范围
    if _is_requirement_evaluation_question(question):  # 客户需求评估需要覆盖常见产品模块
        modules.extend(["整体规格", "视频输入接口 VI/MIPI Rx", "ISP 与图像处理", "视频编解码 VCU/JPEG", "音频接口", "网络接口", "存储与外设接口", "电源与封装"])  # 追加产品评估模块
    if _is_camera_pipeline_question(question, question_lower):  # 摄像头类需求涉及完整视频输入处理链路
        modules.extend(["整体规格", "视频输入接口 VI/MIPI Rx", "ISP 与图像处理", "视频编解码 VCU/JPEG"])  # 追加视频链路模块
    if any(term in question_lower or term in question for term in ["wifi", "以太网", "网络", "ethernet"]):  # 网络相关问题需要查网络模块
        modules.append("网络接口 Ethernet/SDIO")  # 追加网络相关模块
    if any(term in question_lower or term in question for term in ["音频", "mic", "speaker", "i2s", "codec"]):  # 音频相关问题需要查音频模块
        modules.append("音频接口与 Audio Codec")  # 追加音频相关模块
    return _deduplicate_modules(modules)  # 返回去重后的模块列表


def _is_requirement_evaluation_question(question: str) -> bool:  # 判断是否为客户需求满足度评估问题
    return "客户项目需求明细" in question or "客户需求" in question or "是否可以满足客户" in question  # 命中需求评估关键词


def _requirement_evaluation_queries(question: str) -> list[str]:  # 生成客户需求评估需要的扩展查询
    return [  # 返回需求评估扩展查询列表
        f"{question} 产品概述 整体规格 feature overview",  # 覆盖芯片总览能力
        f"{question} 视频输入 MIPI Sensor ISP 图像处理",  # 覆盖视频输入和 ISP
        f"{question} H.265 H.264 JPEG 视频编码 编码性能",  # 覆盖编解码能力
        f"{question} 音频 I2S PCM Audio Codec",  # 覆盖音频能力
        f"{question} Ethernet SDIO USB SPI I2C UART 网络 外设 存储",  # 覆盖网络和外设
        f"{question} 工作电压 功耗 封装 DDR memory",  # 覆盖电源、封装和内存
    ]  # 结束扩展查询列表


def _is_camera_pipeline_question(question: str, question_lower: str) -> bool:  # 判断是否为摄像头视频链路问题
    camera_terms = ["sensor", "camera", "摄像头", "镜头", "视频输入"]  # 定义摄像头相关关键词
    capacity_terms = ["mp", "5m", "200万", "分辨率", "fps", "帧率", "几路", "几个", "多少路"]  # 定义规格和容量关键词
    has_camera = any(term in question_lower or term in question for term in camera_terms)  # 判断是否提到摄像头或 sensor
    has_capacity = any(term in question_lower or term in question for term in capacity_terms)  # 判断是否提到容量、分辨率或帧率
    return has_camera and has_capacity  # 同时命中主题和规格才视为视频链路问题


def _deduplicate_queries(queries: list[str]) -> list[str]:  # 按顺序去重检索词
    seen: set[str] = set()  # 保存已经出现过的检索词
    unique: list[str] = []  # 保存去重后的检索词
    for query in queries:  # 遍历候选检索词
        if query in seen:  # 已出现过则跳过
            continue  # 继续处理下一条检索词
        seen.add(query)  # 记录当前检索词
        unique.append(query)  # 保存当前检索词
    return unique  # 返回去重结果


def _deduplicate_modules(modules: list[str]) -> list[str]:  # 按顺序去重模块列表
    seen: set[str] = set()  # 保存已经出现过的模块名
    unique: list[str] = []  # 保存去重后的模块名
    for module in modules:  # 遍历候选模块
        if module in seen:  # 已出现过则跳过
            continue  # 继续处理下一个模块
        seen.add(module)  # 记录当前模块
        unique.append(module)  # 保存当前模块
    return unique  # 返回去重结果
