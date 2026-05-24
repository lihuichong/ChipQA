from __future__ import annotations  # 启用延迟类型注解，避免运行时前向引用问题

from app.config import ApiConfig  # 导入 OpenAI-compatible API 配置结构
from app.http_client import post_json  # 导入标准库 JSON POST 请求工具


class LLMClient:  # 定义 LLM 对话模型接口
    def chat(self, messages: list[dict[str, str]]) -> str:  # 定义 chat 函数或方法
        raise NotImplementedError  # 向调用方报告当前错误


class MockLLMClient(LLMClient):  # 提供 MVP 阶段的占位 LLM 实现
    def chat(self, messages: list[dict[str, str]]) -> str:  # 定义 chat 函数或方法
        return "Mock LLM is disabled for factual generation in MVP."  # 返回 "Mock LLM is disabled for factual genera


class OpenAICompatibleLLMClient(LLMClient):  # 调用兼容 OpenAI Chat Completions 协议的 LLM 服务
    def __init__(self, config: ApiConfig) -> None:  # 初始化 LLM 客户端
        if not config.enabled:  # 检查 API 配置是否完整
            raise ValueError("LLM API config is incomplete.")  # 配置不完整时阻止运行时才失败
        self.config = config  # 保存 API 配置供后续请求使用

    def chat(self, messages: list[dict[str, str]]) -> str:  # 调用对话模型并返回文本内容
        url = self.config.base_url.rstrip("/") + "/v1/chat/completions"  # 拼接 OpenAI-compatible chat endpoint
        payload = {  # 构造 Chat Completions 请求体
            "model": self.config.model,  # 指定模型名称
            "messages": messages,  # 传入 system/user 等消息
            "temperature": 0.1,  # 降低随机性，优先保证技术问答稳定
        }  # 结束请求体构造
        headers = {  # 构造认证和内容类型请求头
            "Authorization": f"Bearer {self.config.api_key}",  # 使用 Bearer token 传递 API key
            "Content-Type": "application/json",  # 声明请求体为 JSON
        }  # 结束请求头构造
        data = post_json(url, headers, payload, self.config.timeout_seconds)  # 发起 HTTP 请求并解析 JSON 响应
        choices = data.get("choices", [])  # 读取模型返回的候选列表
        if not choices:  # 没有候选结果时返回空字符串
            return ""  # 返回空结果给上层兜底
        message = choices[0].get("message", {})  # 读取第一个候选的 message 对象
        return str(message.get("content", "")).strip()  # 返回模型生成的正文


def build_llm_client(config: ApiConfig, enabled: bool) -> LLMClient:  # 根据配置创建 LLM 客户端
    if enabled and config.enabled:  # 只有显式启用且配置完整才调用真实模型
        return OpenAICompatibleLLMClient(config)  # 返回 OpenAI-compatible LLM 客户端
    return MockLLMClient()  # 默认返回不生成事实答案的 mock 客户端
