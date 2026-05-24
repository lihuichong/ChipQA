from __future__ import annotations  # 启用延迟类型注解，避免运行时前向引用问题

import re  # 导入正则表达式工具
from pathlib import Path  # 导入 Path 以统一处理文件路径


MODEL_PATTERN = re.compile(r"\b[A-Z]{2,}[A-Z0-9]*(?:-[A-Z0-9]+)*\b", re.IGNORECASE)  # 计算并保存 MODEL_PATTERN
STOPWORDS = {  # 计算并保存 STOPWORDS
    "PDF",  # 执行当前业务逻辑
    "PPT",  # 执行当前业务逻辑
    "PPTX",  # 执行当前业务逻辑
    "DATASHEET",  # 执行当前业务逻辑
    "PRELIMINARY",  # 执行当前业务逻辑
    "VERSION",  # 执行当前业务逻辑
    "PUBLIC",  # 执行当前业务逻辑
    "CHINESE",  # 执行当前业务逻辑
    "ENGLISH",  # 执行当前业务逻辑
    "I2C",  # 执行当前业务逻辑
    "SPI",  # 执行当前业务逻辑
    "UART",  # 执行当前业务逻辑
    "GPIO",  # 执行当前业务逻辑
    "ADC",  # 执行当前业务逻辑
    "USB",  # 执行当前业务逻辑
}  # 结束当前多行结构


def extract_chip_models(text: str, limit: int = 10) -> list[str]:  # 定义 extract_chip_models 函数或方法
    candidates: list[str] = []  # 保存当前流程中的 candidates 数据
    for match in MODEL_PATTERN.finditer(text.upper()):  # 遍历当前集合中的每个元素
        value = match.group(0).strip("-_ ")  # 计算并保存 value
        if not any(char.isdigit() for char in value):  # 检查条件：not any(char.isdigit() for char in value)
            continue  # 当前项不符合条件，跳过后续处理
        if value in STOPWORDS:  # 检查条件：value in STOPWORDS
            continue  # 当前项不符合条件，跳过后续处理
        if len(value) < 4:  # 检查条件：len(value) < 4
            continue  # 当前项不符合条件，跳过后续处理
        if value not in candidates:  # 检查条件：value not in candidates
            candidates.append(value)  # 将当前结果追加到列表
        if len(candidates) >= limit:  # 检查条件：len(candidates) >= limit
            break  # 达到结束条件后退出循环
    return candidates  # 返回 candidates


def extract_from_file_name(path: str | Path) -> list[str]:  # 定义 extract_from_file_name 函数或方法
    stem = Path(path).stem.replace("_", " ").replace("-", " -")  # 计算并保存 stem
    return extract_chip_models(stem)  # 返回 extract_chip_models(stem)


def normalize_model(model: str | None) -> str | None:  # 定义 normalize_model 函数或方法
    if not model:  # 检查条件：not model
        return None  # 没有匹配结果时返回 None
    return re.sub(r"\s+", "", model).upper()  # 返回 re.sub(r"\s+", "", model).upper()
