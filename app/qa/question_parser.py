from __future__ import annotations  # 启用延迟类型注解，避免运行时前向引用问题

import re  # 导入正则表达式工具

from app.chips.model_extractor import extract_chip_models, normalize_model  # 导入芯片型号抽取和规范化工具
from app.models import UserQuestion  # 导入问答流程共享的数据结构


CHIP_FIELD_PATTERN = re.compile(  # 计算并保存 CHIP_FIELD_PATTERN
    r"(?:芯片型号|型号|chip\s*model|model)\s*[:：]\s*([A-Za-z0-9][A-Za-z0-9\-_.]*)",  # 执行当前业务逻辑
    re.IGNORECASE,  # 执行当前业务逻辑
)  # 结束当前多行结构
QUESTION_FIELD_PATTERN = re.compile(r"(?:问题|question)\s*[:：]\s*(.+)", re.IGNORECASE | re.DOTALL)  # 计算并保存 QUESTION_FIELD_PATTERN


class QuestionParser:  # 从用户输入中解析芯片型号和问题正文
    def parse(self, raw_text: str) -> UserQuestion:  # 定义 parse 函数或方法
        chip_model = self._extract_explicit_model(raw_text)  # 保存该片段对应的芯片型号
        if chip_model is None:  # 检查条件：chip_model is None
            candidates = extract_chip_models(raw_text, limit=1)  # 保存当前流程中的 candidates 数据
            chip_model = candidates[0] if candidates else None  # 保存该片段对应的芯片型号

        question = self._extract_question(raw_text)  # 保存去除型号后的问题正文
        if chip_model:  # 检查条件：chip_model
            question = question.replace(chip_model, "", 1).strip(" ：:，,。")  # 保存去除型号后的问题正文

        return UserQuestion(  # 返回 UserQuestion(
            raw_text=raw_text,  # 保存用户原始问题
            chip_model=normalize_model(chip_model),  # 保存该片段对应的芯片型号
            question=question or raw_text,  # 保存去除型号后的问题正文
        )  # 结束当前多行结构

    def _extract_explicit_model(self, raw_text: str) -> str | None:  # 定义 _extract_explicit_model 函数或方法
        match = CHIP_FIELD_PATTERN.search(raw_text)  # 计算并保存 match
        if match:  # 检查条件：match
            return match.group(1)  # 返回 match.group(1)
        return None  # 没有匹配结果时返回 None

    def _extract_question(self, raw_text: str) -> str:  # 定义 _extract_question 函数或方法
        match = QUESTION_FIELD_PATTERN.search(raw_text)  # 计算并保存 match
        if match:  # 检查条件：match
            return match.group(1).strip()  # 返回 match.group(1).strip()
        return raw_text.strip()  # 返回 raw_text.strip()
