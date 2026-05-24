from __future__ import annotations  # 启用延迟类型注解，避免运行时前向引用问题

from urllib.parse import urlencode  # 构造联网搜索查询参数

from app.config import SearchConfig  # 导入联网搜索配置结构
from app.http_client import get_json, post_json  # 导入标准库 HTTP JSON 工具
from app.models import Evidence  # 导入证据数据结构


class WebSearchClient:  # 定义联网搜索接口
    def search(self, query: str, top_k: int) -> list[Evidence]:  # 搜索联网证据
        raise NotImplementedError  # 子类必须实现具体搜索逻辑


class DisabledWebSearchClient(WebSearchClient):  # 默认禁用联网搜索的安全实现
    def search(self, query: str, top_k: int) -> list[Evidence]:  # 禁用状态下不返回联网证据
        return []  # 返回空联网证据列表


class BingWebSearchClient(WebSearchClient):  # 调用 Bing Web Search API
    def __init__(self, config: SearchConfig) -> None:  # 初始化 Bing 搜索客户端
        self.config = config  # 保存搜索配置

    def search(self, query: str, top_k: int) -> list[Evidence]:  # 搜索联网资料并转换为证据
        endpoint = self.config.endpoint or "https://api.bing.microsoft.com/v7.0/search"  # 使用默认 Bing endpoint
        url = endpoint + "?" + urlencode({"q": query, "count": top_k, "mkt": "zh-CN"})  # 拼接搜索 URL
        headers = {"Ocp-Apim-Subscription-Key": self.config.api_key or ""}  # 构造 Bing 认证头
        data = get_json(url, headers, self.config.timeout_seconds)  # 发起搜索请求
        items = data.get("webPages", {}).get("value", [])  # 读取网页搜索结果列表
        return [_to_web_evidence(item, index) for index, item in enumerate(items[:top_k], start=1)]  # 转换为 Evidence 列表


class TavilyWebSearchClient(WebSearchClient):  # 调用 Tavily Search API
    def __init__(self, config: SearchConfig) -> None:  # 初始化 Tavily 搜索客户端
        self.config = config  # 保存搜索配置

    def search(self, query: str, top_k: int) -> list[Evidence]:  # 搜索联网资料并转换为证据
        endpoint = self.config.endpoint or "https://api.tavily.com/search"  # 使用默认 Tavily endpoint
        payload = {"api_key": self.config.api_key, "query": query, "max_results": top_k, "search_depth": "basic"}  # 构造 Tavily 请求体
        data = post_json(endpoint, {"Content-Type": "application/json"}, payload, self.config.timeout_seconds)  # 发起搜索请求
        items = data.get("results", [])  # 读取 Tavily 搜索结果
        return [_to_web_evidence(item, index) for index, item in enumerate(items[:top_k], start=1)]  # 转换为 Evidence 列表


class SerpApiWebSearchClient(WebSearchClient):  # 调用 SerpAPI Google 搜索
    def __init__(self, config: SearchConfig) -> None:  # 初始化 SerpAPI 搜索客户端
        self.config = config  # 保存搜索配置

    def search(self, query: str, top_k: int) -> list[Evidence]:  # 搜索联网资料并转换为证据
        endpoint = self.config.endpoint or "https://serpapi.com/search.json"  # 使用默认 SerpAPI endpoint
        url = endpoint + "?" + urlencode({"q": query, "api_key": self.config.api_key, "hl": "zh-cn", "num": top_k})  # 拼接搜索 URL
        data = get_json(url, {}, self.config.timeout_seconds)  # 发起搜索请求
        items = data.get("organic_results", [])  # 读取自然搜索结果
        return [_to_web_evidence(item, index) for index, item in enumerate(items[:top_k], start=1)]  # 转换为 Evidence 列表


def build_web_search_client(config: SearchConfig) -> WebSearchClient:  # 根据配置创建联网搜索客户端
    if not config.enabled or not config.api_key:  # 未启用或未配置 key 时禁用联网搜索
        return DisabledWebSearchClient()  # 返回禁用搜索客户端
    if config.provider == "tavily":  # provider 配置为 tavily 时使用 Tavily
        return TavilyWebSearchClient(config)  # 返回 Tavily 搜索客户端
    if config.provider == "serpapi":  # provider 配置为 serpapi 时使用 SerpAPI
        return SerpApiWebSearchClient(config)  # 返回 SerpAPI 搜索客户端
    return BingWebSearchClient(config)  # 默认使用 Bing Web Search


def _to_web_evidence(item: dict, index: int) -> Evidence:  # 将搜索结果字典转换为证据对象
    title = item.get("name") or item.get("title") or "未知标题"  # 读取搜索结果标题
    snippet = item.get("snippet") or item.get("content") or item.get("body") or ""  # 读取搜索结果摘要
    url = item.get("url") or item.get("link") or item.get("href")  # 读取搜索结果链接
    return Evidence(  # 构造联网证据对象
        source_type="web",  # 标记证据来自联网搜索
        quote=snippet or title,  # 保存搜索摘要作为可引用片段
        url=url,  # 保存网页链接
        summary=f"{title}：{snippet}".strip("："),  # 保存标题和摘要组成的说明
        relevance_score=float(100 - index),  # 按搜索排名生成初始分数
        confidence="low",  # 搜索结果摘要默认低可信，后续由 Reader 综合判断
    )  # 结束证据对象构造
