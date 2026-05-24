from __future__ import annotations  # 启用延迟类型注解，避免运行时前向引用问题

from app.config import ApiConfig  # 导入 OpenAI-compatible API 配置结构
from app.http_client import post_json  # 导入标准库 JSON POST 请求工具
from app.models import Evidence  # 导入证据数据结构


class Reranker:  # 定义证据重排接口
    def rerank(self, query: str, evidence: list[Evidence], top_k: int) -> list[Evidence]:  # 对候选证据重新排序
        raise NotImplementedError  # 子类必须实现具体重排逻辑


class ScoreReranker(Reranker):  # 使用现有相关性分数进行兜底重排
    def rerank(self, query: str, evidence: list[Evidence], top_k: int) -> list[Evidence]:  # 按 relevance_score 排序
        return sorted(evidence, key=lambda item: item.relevance_score, reverse=True)[:top_k]  # 返回分数最高的前 top_k 条证据


class OpenAICompatibleReranker(Reranker):  # 调用常见 rerank API 对候选证据排序
    def __init__(self, config: ApiConfig) -> None:  # 初始化 Reranker 客户端
        if not config.enabled:  # 检查 API 配置是否完整
            raise ValueError("Reranker API config is incomplete.")  # 配置不完整时给出明确错误
        self.config = config  # 保存 API 配置供后续请求使用

    def rerank(self, query: str, evidence: list[Evidence], top_k: int) -> list[Evidence]:  # 使用远程 reranker 重排证据
        if not evidence:  # 没有候选证据时直接返回
            return []  # 返回空列表
        url = self.config.base_url.rstrip("/") + "/v1/rerank"  # 拼接常见 rerank endpoint
        documents = [item.quote for item in evidence]  # 提取候选证据文本
        payload = {"model": self.config.model, "query": query, "documents": documents, "top_n": top_k}  # 构造 rerank 请求体
        headers = {"Authorization": f"Bearer {self.config.api_key}", "Content-Type": "application/json"}  # 构造认证请求头
        data = post_json(url, headers, payload, self.config.timeout_seconds)  # 发起 HTTP 请求并解析响应
        results = data.get("results", data.get("data", []))  # 兼容常见 results/data 响应字段
        ranked: list[Evidence] = []  # 保存重排后的证据列表
        for result in results:  # 遍历 reranker 返回的排序结果
            index = int(result.get("index", result.get("document_index", -1)))  # 兼容不同服务的文档下标字段
            score = float(result.get("relevance_score", result.get("score", 0.0)))  # 兼容不同服务的分数字段
            if 0 <= index < len(evidence):  # 只接收有效下标
                evidence[index].relevance_score = score  # 用 reranker 分数覆盖候选证据分数
                ranked.append(evidence[index])  # 保存该条重排结果
        if ranked:  # 服务返回有效排序时使用远程排序
            return ranked[:top_k]  # 返回前 top_k 条重排证据
        return ScoreReranker().rerank(query, evidence, top_k)  # 远程响应异常时回退到本地分数排序


def build_reranker(config: ApiConfig) -> Reranker:  # 根据配置创建 reranker
    if config.enabled:  # 配置完整时使用远程 reranker
        return OpenAICompatibleReranker(config)  # 返回远程 reranker 客户端
    return ScoreReranker()  # 默认使用本地分数重排
