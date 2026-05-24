from __future__ import annotations  # 启用延迟类型注解，避免运行时前向引用问题

from dataclasses import dataclass  # 导入 dataclass 工具定义轻量数据结构


@dataclass  # 将下方类声明为数据类
class LoadedPage:  # 定义 LoadedPage 类
    text: str  # 执行当前业务逻辑
    page_number: int | None = None  # 保存 PDF 页码
    slide_number: int | None = None  # 保存 PPT Slide 编号
