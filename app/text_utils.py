from __future__ import annotations  # 启用延迟类型注解，避免运行时前向引用问题


def clean_text(text: str) -> str:  # 定义 clean_text 函数或方法
    encoded = text.encode("utf-8", errors="ignore")  # 计算并保存 encoded
    decoded = encoded.decode("utf-8", errors="ignore")  # 计算并保存 decoded
    return decoded.replace("\x00", "")  # 返回 decoded.replace("\x00", "")
