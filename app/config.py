from __future__ import annotations  # 启用延迟类型注解，避免运行时前向引用问题

import os  # 读取环境变量中的模型和联网搜索配置
from dataclasses import dataclass  # 用 dataclass 保存轻量配置对象
from pathlib import Path  # 定位项目根目录下的 .env 文件


@dataclass  # 将下方配置结构声明为数据类
class ApiConfig:  # 保存一个 OpenAI-compatible API 的连接配置
    api_key: str | None  # 保存 API key，未配置时为 None
    base_url: str | None  # 保存接口基础 URL，例如 https://api.deepseek.com
    model: str | None  # 保存模型名称，例如 deepseek-chat
    provider: str = "openai"  # 保存 API 协议类型，默认使用 OpenAI-compatible 协议
    project_id: str | None = None  # 保存 SophNet embedding 所需的项目 ID
    easyllm_id: str | None = None  # 保存 SophNet embedding 所需的 EasyLLM ID
    dimensions: int | None = None  # 保存 embedding 输出维度
    timeout_seconds: int = 60  # 保存 HTTP 请求超时时间

    @property  # 将是否可用暴露为只读属性
    def enabled(self) -> bool:  # 判断该 API 配置是否足够发起请求
        return bool(self.api_key and self.base_url and self.model)  # 只有 key、base_url、model 都存在才启用


@dataclass  # 将下方配置结构声明为数据类
class SearchConfig:  # 保存联网搜索模块的配置
    enabled: bool  # 标记是否允许联网搜索
    provider: str  # 保存搜索供应商名称
    api_key: str | None  # 保存搜索服务 API key
    endpoint: str | None  # 保存搜索服务 endpoint
    timeout_seconds: int = 20  # 保存搜索请求超时时间


@dataclass  # 将下方配置结构声明为数据类
class AppConfig:  # 汇总 RAG 升级版所需的全部配置
    llm: ApiConfig  # 保存 LLM Reader 配置
    embedding: ApiConfig  # 保存 Embedding 配置
    reranker: ApiConfig  # 保存 Reranker 配置
    search: SearchConfig  # 保存联网搜索配置
    local_recall_k: int = 24  # 保存本地初召回数量
    web_recall_k: int = 5  # 保存联网搜索证据数量
    use_llm_reader: bool = False  # 标记是否使用真实 LLM 生成最终答案


def load_config() -> AppConfig:  # 从环境变量加载应用配置
    load_dotenv()  # 先读取本地 .env，再解析环境变量配置
    embedding_provider = _env_first("QA_EMBEDDING_PROVIDER", "EMBEDDING_PROVIDER", default="openai") or "openai"  # 提前读取 embedding 协议类型
    llm = ApiConfig(  # 构造 LLM Reader 配置
        api_key=_env_first("QA_LLM_API_KEY", "DEEPSEEK_API_KEY", "GLM_API_KEY", "MINIMAX_API_KEY"),  # 读取 LLM API key
        base_url=_env_first("QA_LLM_BASE_URL", "DEEPSEEK_BASE_URL", default="https://api.deepseek.com"),  # 读取 LLM base URL
        model=_env_first("QA_LLM_MODEL", "DEEPSEEK_MODEL", default="deepseek-chat"),  # 读取 LLM 模型名
    )  # 结束 LLM 配置构造
    embedding = ApiConfig(  # 构造 Embedding 配置
        api_key=_env_first("QA_EMBEDDING_API_KEY", "EMBEDDING_API_KEY", "QA_LLM_API_KEY"),  # 读取 Embedding API key，默认复用 LLM key
        base_url=_env_first("QA_EMBEDDING_BASE_URL", "EMBEDDING_BASE_URL", default=_default_embedding_base_url(embedding_provider)),  # 读取 Embedding base URL
        model=_env_first("QA_EMBEDDING_MODEL", "EMBEDDING_MODEL", "QA_EMBEDDING_EASYLLM_ID", "SOPHNET_EASYLLM_ID"),  # 读取 Embedding 模型名或 EasyLLM ID
        provider=embedding_provider,  # 保存 embedding 协议类型
        project_id=_env_first("QA_EMBEDDING_PROJECT_ID", "SOPHNET_PROJECT_ID"),  # 读取 SophNet 项目 ID
        easyllm_id=_env_first("QA_EMBEDDING_EASYLLM_ID", "SOPHNET_EASYLLM_ID"),  # 读取 SophNet EasyLLM ID
        dimensions=_env_int("QA_EMBEDDING_DIMENSIONS", "EMBEDDING_DIMENSIONS"),  # 读取 embedding 输出维度
    )  # 结束 Embedding 配置构造
    reranker = ApiConfig(  # 构造 Reranker 配置
        api_key=_env_first("QA_RERANKER_API_KEY", "RERANKER_API_KEY"),  # 读取 Reranker API key
        base_url=_env_first("QA_RERANKER_BASE_URL", "RERANKER_BASE_URL"),  # 读取 Reranker base URL
        model=_env_first("QA_RERANKER_MODEL", "RERANKER_MODEL"),  # 读取 Reranker 模型名
    )  # 结束 Reranker 配置构造
    search = SearchConfig(  # 构造联网搜索配置
        enabled=_truthy(os.getenv("QA_ENABLE_WEB_SEARCH")),  # 读取是否启用联网搜索
        provider=os.getenv("QA_WEB_SEARCH_PROVIDER", "bing").lower(),  # 读取联网搜索供应商
        api_key=_env_first("QA_WEB_SEARCH_API_KEY", "BING_SEARCH_API_KEY", "TAVILY_API_KEY", "SERPAPI_API_KEY"),  # 读取搜索 API key
        endpoint=_env_first("QA_WEB_SEARCH_ENDPOINT", "BING_SEARCH_ENDPOINT"),  # 读取搜索 endpoint
    )  # 结束搜索配置构造
    return AppConfig(  # 返回汇总后的应用配置
        llm=llm,  # 保存 LLM 配置
        embedding=embedding,  # 保存 Embedding 配置
        reranker=reranker,  # 保存 Reranker 配置
        search=search,  # 保存搜索配置
        local_recall_k=int(os.getenv("QA_LOCAL_RECALL_K", "24")),  # 读取本地初召回数量
        web_recall_k=int(os.getenv("QA_WEB_RECALL_K", "5")),  # 读取联网搜索证据数量
        use_llm_reader=_truthy(os.getenv("QA_USE_LLM_READER")),  # 读取是否启用真实 LLM Reader
    )  # 结束应用配置构造


def _env_first(*names: str, default: str | None = None) -> str | None:  # 按顺序读取第一个非空环境变量
    for name in names:  # 遍历候选环境变量名
        value = os.getenv(name)  # 读取当前环境变量
        if value:  # 命中非空变量时返回
            return value  # 返回当前环境变量值
    return default  # 都未配置时返回默认值


def _truthy(value: str | None) -> bool:  # 将常见字符串配置解析为布尔值
    return value is not None and value.strip().lower() in {"1", "true", "yes", "on"}  # 判断是否为启用值


def _default_embedding_base_url(provider: str) -> str | None:  # 根据供应商选择 embedding 默认 base URL
    if provider.lower() == "sophnet":  # SophNet 使用官方 open-apis 根地址
        return "https://www.sophnet.com/api/open-apis"  # 返回 SophNet 默认 base URL
    return None  # 其它协议不默认猜测地址


def _env_int(*names: str) -> int | None:  # 按顺序读取第一个可解析为整数的环境变量
    value = _env_first(*names)  # 读取原始环境变量值
    if not value:  # 没有配置时返回空
        return None  # 返回 None 表示未指定
    return int(value)  # 将字符串配置转换为整数


def load_dotenv(path: str | Path = ".env") -> None:  # 读取项目本地 .env 配置文件
    env_path = Path(path)  # 将传入路径转换为 Path 对象
    if not env_path.exists():  # 没有 .env 文件时直接跳过
        return  # 返回调用方继续使用系统环境变量
    for raw_line in env_path.read_text(encoding="utf-8").splitlines():  # 按行读取 .env 内容
        line = raw_line.strip()  # 去掉行首尾空白
        if not line or line.startswith("#") or "=" not in line:  # 跳过空行、注释和非法行
            continue  # 继续处理下一行
        name, value = line.split("=", 1)  # 按第一个等号拆分变量名和值
        name = name.strip().lstrip("\ufeff")  # 清理变量名空白和 Windows UTF-8 BOM
        value = _strip_env_quotes(value.strip())  # 清理变量值空白和包裹引号
        os.environ.setdefault(name, value)  # 不覆盖系统中已经显式设置的同名环境变量


def _strip_env_quotes(value: str) -> str:  # 去掉 .env 值两侧成对的引号
    if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:  # 检查是否由同类引号包裹
        return value[1:-1]  # 返回去掉首尾引号后的值
    return value  # 没有包裹引号时原样返回
