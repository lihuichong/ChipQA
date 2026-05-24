from __future__ import annotations  # 启用延迟类型注解，避免运行时前向引用问题

from dataclasses import dataclass  # 导入 dataclass 用于定义纠错规则结构


@dataclass(frozen=True)  # 将纠错规则声明为不可变数据结构
class CorrectionRule:  # 定义回答纠错规则
    name: str  # 保存规则名称
    triggers: list[str]  # 保存触发关键词
    modules: list[str]  # 保存必须补充参考的芯片 IP 或模块
    queries: list[str]  # 保存必须补充检索的查询词
    note: str  # 保存规则来源和说明


CORRECTION_RULES: list[CorrectionRule] = [  # 维护用户指出过的回答纠错记录
    CorrectionRule(  # 定义摄像头链路纠错规则
        name="camera_pipeline_requires_input_isp_codec",  # 保存规则唯一名称
        triggers=["摄像头", "sensor", "camera", "镜头", "视频输入", "几路", "几个", "多少路", "fps", "帧率", "分辨率"],  # 保存触发词
        modules=["整体规格", "视频输入接口 VI/VIVO/MIPI Rx", "ISP 与图像处理", "视频编解码 VCU/H.264/H.265", "内存与带宽"],  # 保存必须参考模块
        queries=[  # 保存补充检索词
            "视频输入 VI VIVO MIPI Rx Sensor 路数 分辨率 帧率",  # 覆盖前端视频输入链路
            "ISP 图像处理 多路 输入 HDR 分辨率 帧率",  # 覆盖 ISP 处理链路
            "H.265 H.264 视频编码 编码总性能 25fps VCU",  # 覆盖编码吞吐瓶颈
            "产品概述 整体规格 视频输入 ISP 视频编码 DDR",  # 覆盖总体能力和带宽背景
        ],  # 结束补充检索词
        note="用户纠错：能接多少路摄像头不光和 VIVO/视频输入接口有关，还和 ISP 以及编解码规格相关。",  # 保存纠错说明
    )  # 结束摄像头链路规则
]  # 结束纠错规则列表


def matching_correction_rules(question: str) -> list[CorrectionRule]:  # 根据问题返回命中的纠错规则
    question_lower = question.lower()  # 将问题转为小写以兼容英文关键词
    matched: list[CorrectionRule] = []  # 保存命中的规则
    for rule in CORRECTION_RULES:  # 遍历全部纠错规则
        if any(trigger in question_lower or trigger in question for trigger in rule.triggers):  # 判断是否命中任一触发词
            matched.append(rule)  # 保存命中的规则
    return matched  # 返回命中规则列表
