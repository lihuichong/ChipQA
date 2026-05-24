from __future__ import annotations  # 启用延迟类型注解，避免运行时前向引用问题

from dataclasses import asdict, dataclass, field  # 导入 dataclass 工具定义轻量数据结构
from typing import Any  # 导入 Any 表示灵活的元数据类型


@dataclass  # 将下方类声明为数据类
class DocumentRecord:  # 定义文档级元数据结构
    id: str  # 执行当前业务逻辑
    file_name: str  # 执行当前业务逻辑
    file_path: str  # 执行当前业务逻辑
    document_type: str  # 执行当前业务逻辑
    chip_models: list[str] = field(default_factory=list)  # 保存文档中识别出的芯片型号

    def to_dict(self) -> dict[str, Any]:  # 定义 to_dict 函数或方法
        return asdict(self)  # 返回 asdict(self)

    @classmethod  # 声明该方法从类本身构造对象
    def from_dict(cls, data: dict[str, Any]) -> "DocumentRecord":  # 定义 from_dict 函数或方法
        return cls(**data)  # 返回 cls(**data)


@dataclass  # 将下方类声明为数据类
class DocumentChunk:  # 定义可检索文本片段及来源定位结构
    id: str  # 执行当前业务逻辑
    document_id: str  # 执行当前业务逻辑
    file_name: str  # 执行当前业务逻辑
    file_path: str  # 执行当前业务逻辑
    text: str  # 执行当前业务逻辑
    chip_model: str | None = None  # 保存该片段对应的芯片型号
    page_number: int | None = None  # 保存 PDF 页码
    slide_number: int | None = None  # 保存 PPT Slide 编号
    section_title: str | None = None  # 预留章节标题字段
    chunk_index: int = 0  # 保存切片在当前页内的顺序
    metadata: dict[str, Any] = field(default_factory=dict)  # 保存额外元数据

    def to_dict(self) -> dict[str, Any]:  # 定义 to_dict 函数或方法
        return asdict(self)  # 返回 asdict(self)

    @classmethod  # 声明该方法从类本身构造对象
    def from_dict(cls, data: dict[str, Any]) -> "DocumentChunk":  # 定义 from_dict 函数或方法
        return cls(**data)  # 返回 cls(**data)


@dataclass  # 将下方类声明为数据类
class UserQuestion:  # 定义解析后的用户问题结构
    raw_text: str  # 执行当前业务逻辑
    chip_model: str | None  # 执行当前业务逻辑
    question: str  # 执行当前业务逻辑
    constraints: dict[str, Any] = field(default_factory=dict)  # 保存问题中的约束条件
    need_web_search: bool = False  # 标记是否需要联网补充


@dataclass  # 将下方类声明为数据类
class Evidence:  # 定义检索证据及引用来源结构
    source_type: str  # 执行当前业务逻辑
    quote: str  # 执行当前业务逻辑
    file_name: str | None = None  # 保存资料文件名
    file_path: str | None = None  # 保存资料文件路径
    page_number: int | None = None  # 保存 PDF 页码
    slide_number: int | None = None  # 保存 PPT Slide 编号
    url: str | None = None  # 计算并保存 url
    summary: str | None = None  # 保存证据与问题的关联说明
    relevance_score: float = 0.0  # 保存检索相关性分数
    confidence: str = "medium"  # 保存证据可信度标记


@dataclass  # 将下方类声明为数据类
class Answer:  # 定义最终回答的结构化表示
    conclusion: str  # 执行当前业务逻辑
    local_evidence: list[Evidence] = field(default_factory=list)  # 保存本地资料证据列表
    web_evidence: list[Evidence] = field(default_factory=list)  # 保存联网资料证据列表
    reasoning: str = ""  # 保存基于证据的推导过程
    uncertainty: str = ""  # 保存不确定性和限制说明
    recommendation: str = ""  # 保存工程复核或下一步建议

    def to_markdown(self, mode: str = "full") -> str:  # 将结构化回答渲染成 Markdown
        if mode == "simple":  # 简单回答只输出直接答案和本地引用
            return self.to_simple_markdown()  # 返回简短 Markdown
        lines: list[str] = ["## 结论", "", self.conclusion.strip(), "", "## 依据", ""]  # 计算并保存 lines
        lines.extend(["### 1. 本地资料证据", ""])  # 将多个元素批量追加到列表
        if self.local_evidence:  # 检查条件：self.local_evidence
            for index, evidence in enumerate(self.local_evidence, start=1):  # 遍历当前集合中的每个元素
                location = _format_location(evidence)  # 计算并保存 location
                lines.extend(  # 将多个元素批量追加到列表
                    [  # 执行当前业务逻辑
                        f"{index}. 来源文件：{evidence.file_name or '未知'}{location}",  # 执行当前业务逻辑
                        f"   - 原文摘录：{evidence.quote}",  # 执行当前业务逻辑
                        f"   - 对应解释：{evidence.summary or '该原文与问题高度相关，需结合上下文确认最终工程含义。'}",  # 执行当前业务逻辑
                    ]  # 结束当前多行结构
                )  # 结束当前多行结构
        else:  # 处理上述条件都不满足的情况
            lines.append("- 未找到可引用的本地资料证据。")  # 将当前结果追加到列表

        lines.extend(["", "### 2. 联网资料证据", ""])  # 将多个元素批量追加到列表
        if self.web_evidence:  # 检查条件：self.web_evidence
            for evidence in self.web_evidence:  # 遍历当前集合中的每个元素
                lines.append(f"- 来源链接：{evidence.url or '未知'}")  # 将当前结果追加到列表
                lines.append(f"  - 摘要：{evidence.summary or evidence.quote}")  # 将当前结果追加到列表
        else:  # 处理上述条件都不满足的情况
            lines.append("- 未找到联网资料证据，或当前未启用联网搜索。")  # 将当前结果追加到列表

        lines.extend(  # 将多个元素批量追加到列表
            [  # 执行当前业务逻辑
                "",  # 执行当前业务逻辑
                "### 3. 芯片常识与推导",  # 执行当前业务逻辑
                "",  # 执行当前业务逻辑
                self.reasoning.strip() or "- 当前回答未使用额外芯片常识推导。",  # 执行当前业务逻辑
                "",  # 执行当前业务逻辑
                "## 不确定性与限制",  # 执行当前业务逻辑
                "",  # 执行当前业务逻辑
                self.uncertainty.strip() or "未发现额外限制。",  # 执行当前业务逻辑
                "",  # 执行当前业务逻辑
                "## 建议",  # 执行当前业务逻辑
                "",  # 执行当前业务逻辑
                self.recommendation.strip() or "建议结合完整 datasheet 相关章节和实际硬件设计约束复核。",  # 执行当前业务逻辑
            ]  # 结束当前多行结构
        )  # 结束当前多行结构
        return "\n".join(lines)  # 返回 "\n".join(lines)

    def to_simple_markdown(self) -> str:  # 将回答渲染为简洁版本
        lines: list[str] = ["## 答案", "", self.conclusion.strip(), "", "## 数据库参考", ""]  # 初始化简洁回答行
        if self.local_evidence:  # 有本地证据时展示来源和原文摘录
            for index, evidence in enumerate(self.local_evidence[:3], start=1):  # 最多展示三条本地引用
                location = _format_location(evidence)  # 生成页码或 Slide 位置信息
                lines.append(f"{index}. {evidence.file_name or '未知'}{location}")  # 追加证据来源
                lines.append(f"   - {evidence.quote}")  # 追加数据库原文摘录
        else:  # 没有本地证据时明确说明
            lines.append("- 未找到可引用的本地资料证据。")  # 追加无证据说明
        return "\n".join(lines)  # 返回简洁 Markdown 文本


def _format_location(evidence: Evidence) -> str:  # 定义 _format_location 函数或方法
    if evidence.page_number is not None:  # 检查条件：evidence.page_number is not None
        return f"，页码：{evidence.page_number}"  # 返回 f"，页码：{evidence.page_number}"
    if evidence.slide_number is not None:  # 检查条件：evidence.slide_number is not None
        return f"，Slide：{evidence.slide_number}"  # 返回 f"，Slide：{evidence.slide_number}"
    return ""  # 返回 ""
