from __future__ import annotations  # 启用延迟类型注解，避免运行时前向引用问题

import hashlib  # 导入当前模块需要的依赖
import math  # 计算向量归一化和余弦相似度

from app.config import ApiConfig  # 导入 OpenAI-compatible API 配置结构
from app.http_client import post_json  # 导入标准库 JSON POST 请求工具


class EmbeddingClient:  # 定义 embedding 模型接口
    def embed(self, text: str) -> list[float]:  # 定义 embed 函数或方法
        raise NotImplementedError  # 向调用方报告当前错误

    def embed_many(self, texts: list[str]) -> list[list[float]]:  # 批量生成 embedding，默认逐条调用单文本接口
        return [self.embed(text) for text in texts]  # 返回每段文本对应的向量


class FakeEmbeddingClient(EmbeddingClient):  # 提供可测试的伪 embedding 实现
    def __init__(self, dimensions: int = 16) -> None:  # 初始化对象所需依赖和配置
        self.dimensions = dimensions  # 初始化或更新对象属性 self.dimensions

    def embed(self, text: str) -> list[float]:  # 定义 embed 函数或方法
        digest = hashlib.sha256(text.encode("utf-8")).digest()  # 计算并保存 digest
        return [digest[index] / 255.0 for index in range(self.dimensions)]  # 返回 [digest[index] / 255.0 for index in rang


class OpenAICompatibleEmbeddingClient(EmbeddingClient):  # 调用兼容 OpenAI Embeddings 协议的向量模型
    def __init__(self, config: ApiConfig) -> None:  # 初始化 Embedding 客户端
        if not config.enabled:  # 检查 API 配置是否完整
            raise ValueError("Embedding API config is incomplete.")  # 配置不完整时给出明确错误
        self.config = config  # 保存 API 配置供后续请求使用

    def embed(self, text: str) -> list[float]:  # 生成单段文本的 embedding 向量
        url = self.config.base_url.rstrip("/") + "/v1/embeddings"  # 拼接 OpenAI-compatible embeddings endpoint
        payload = {"model": self.config.model, "input": text}  # 构造 embeddings 请求体
        headers = {"Authorization": f"Bearer {self.config.api_key}", "Content-Type": "application/json"}  # 构造认证请求头
        data = post_json(url, headers, payload, self.config.timeout_seconds)  # 发起 HTTP 请求并解析响应
        items = data.get("data", [])  # 读取 embedding 结果列表
        if not items:  # 没有返回向量时给出空向量
            return []  # 返回空向量让上层忽略语义分
        return [float(value) for value in items[0].get("embedding", [])]  # 将返回值统一转换为 float 列表

    def embed_many(self, texts: list[str]) -> list[list[float]]:  # 使用 OpenAI-compatible 批量接口生成多段文本向量
        if not texts:  # 没有输入文本时直接返回空列表
            return []  # 返回空批量结果
        url = self.config.base_url.rstrip("/") + "/v1/embeddings"  # 拼接 OpenAI-compatible embeddings endpoint
        payload = {"model": self.config.model, "input": texts}  # 批量输入多段文本
        headers = {"Authorization": f"Bearer {self.config.api_key}", "Content-Type": "application/json"}  # 构造认证请求头
        data = post_json(url, headers, payload, self.config.timeout_seconds)  # 发起 HTTP 请求并解析响应
        items = sorted(data.get("data", []), key=lambda item: item.get("index", 0))  # 按返回 index 保持输入顺序
        return [[float(value) for value in item.get("embedding", [])] for item in items]  # 返回批量向量列表


class SophNetEmbeddingClient(EmbeddingClient):  # 调用 SophNet EasyLLM embedding 专用接口
    def __init__(self, config: ApiConfig) -> None:  # 初始化 SophNet embedding 客户端
        if not _sophnet_embedding_ready(config):  # 校验 SophNet 必填参数
            raise ValueError("SophNet embedding config requires api key, base url, model, and dimensions.")  # 抛出配置错误
        self.config = config  # 保存 API 配置供后续请求使用

    def embed(self, text: str) -> list[float]:  # 生成单段文本 embedding
        embeddings = self.embed_many([text])  # 复用批量接口
        return embeddings[0] if embeddings else []  # 返回第一条向量或空向量

    def embed_many(self, texts: list[str]) -> list[list[float]]:  # 批量生成 embedding
        if not texts:  # 没有输入文本时直接返回空列表
            return []  # 返回空批量结果
        url = _sophnet_embedding_url(self.config)  # 拼接 SophNet embedding endpoint
        payload = {  # 构造 SophNet embedding 请求体
            "model": self.config.model,  # 指定 embedding 模型名称，例如 bge-m3
            "dimensions": self.config.dimensions,  # 指定返回向量维度
            "input_texts": texts[:10],  # SophNet 单次最多提交十段文本
        }  # 结束请求体构造
        if self.config.easyllm_id:  # 配置 EasyLLM ID 时使用项目内服务
            payload["easyllm_id"] = self.config.easyllm_id  # 指定 SophNet 控制台中的 EasyLLM 服务 ID
        headers = {"Authorization": f"Bearer {self.config.api_key}", "Content-Type": "application/json"}  # 构造认证请求头
        data = post_json(url, headers, payload, self.config.timeout_seconds)  # 发起 HTTP 请求并解析响应
        raw_embeddings = data.get("embeddings") or data.get("data") or []  # 兼容 embeddings 或 data 两种返回字段
        return [_coerce_embedding(item) for item in raw_embeddings]  # 标准化批量向量格式


def _coerce_embedding(item) -> list[float]:  # 将不同返回形态统一转换为 float 向量
    values = item.get("embedding", item) if isinstance(item, dict) else item  # 支持对象或直接数组
    return [float(value) for value in values] if isinstance(values, list) else []  # 返回 float 列表

def cosine_similarity(left: list[float], right: list[float]) -> float:  # 计算两个向量的余弦相似度
    if not left or not right or len(left) != len(right):  # 检查向量是否为空或维度不一致
        return 0.0  # 无法计算时返回零分
    dot = sum(a * b for a, b in zip(left, right))  # 计算向量点积
    left_norm = math.sqrt(sum(value * value for value in left))  # 计算左向量模长
    right_norm = math.sqrt(sum(value * value for value in right))  # 计算右向量模长
    if left_norm == 0 or right_norm == 0:  # 避免除以零
        return 0.0  # 零向量没有有效相似度
    return dot / (left_norm * right_norm)  # 返回标准余弦相似度


def build_embedding_client(config: ApiConfig) -> EmbeddingClient | None:  # 根据配置创建 embedding 客户端
    if config.provider.lower() == "sophnet":  # SophNet 使用专用 embedding API 协议
        if _sophnet_embedding_ready(config):  # SophNet 必填参数完整时启用 embedding
            return SophNetEmbeddingClient(config)  # 返回 SophNet embedding 客户端
        return None  # 缺少项目或 EasyLLM 参数时回退关键词检索
    if config.enabled:  # OpenAI-compatible 配置完整时使用真实 embedding 服务
        return OpenAICompatibleEmbeddingClient(config)  # 返回 OpenAI-compatible embedding 客户端
    return None  # 默认不启用 embedding，避免 fake 向量影响排序


def validate_embedding_config(config: ApiConfig) -> None:  # 主动构建 embedding 索引前执行严格配置校验
    if config.provider.lower() == "sophnet" and not _sophnet_embedding_ready(config):  # SophNet 缺少任一必填参数时提示
        raise ValueError("SophNet embedding requires QA_EMBEDDING_MODEL and QA_EMBEDDING_DIMENSIONS; project/easyllm are optional for the simplified endpoint.")  # 抛出明确错误
    if config.provider.lower() != "sophnet" and not config.enabled:  # OpenAI-compatible 缺少 key/base/model 时提示
        raise ValueError("Embedding requires QA_EMBEDDING_API_KEY, QA_EMBEDDING_BASE_URL, and QA_EMBEDDING_MODEL.")  # 抛出明确错误


def _sophnet_embedding_ready(config: ApiConfig) -> bool:  # 判断 SophNet embedding 配置是否完整
    return bool(config.api_key and config.base_url and config.model and config.dimensions)  # 简化 endpoint 只要求 key、base、model 和维度


def _sophnet_embedding_url(config: ApiConfig) -> str:  # 根据配置拼接 SophNet embedding endpoint
    base_url = config.base_url.rstrip("/")  # 去掉 base URL 末尾斜杠
    if config.project_id:  # 有项目 ID 时使用项目内 endpoint
        return base_url + f"/projects/{config.project_id}/easyllms/embeddings"  # 返回项目内 EasyLLM endpoint
    return base_url + "/projects/easyllms/embeddings"  # 没有项目 ID 时使用简化 endpoint
