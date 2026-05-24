from __future__ import annotations  # 启用延迟类型注解，避免运行时前向引用问题

from pathlib import Path  # 导入 Path 以统一处理文件路径

from app.config import AppConfig, load_config  # 导入应用配置加载工具
from app.documents.chunker import DocumentChunker  # 导入文档解析或切片相关组件
from app.documents.parser import DocumentParser, iter_supported_files  # 导入文档解析或切片相关组件
from app.llm.client import build_llm_client  # 导入 LLM Reader 构造函数
from app.models import Answer  # 导入问答流程共享的数据结构
from app.qa.answer_generator import AnswerGenerator  # 导入问题解析或答案生成组件
from app.qa.context_planner import build_related_queries, infer_related_modules  # 导入问题相关模块规划工具
from app.qa.question_parser import QuestionParser  # 导入问题解析或答案生成组件
from app.retrieval.embeddings import build_embedding_client, validate_embedding_config  # 导入 embedding 客户端构造和配置校验函数
from app.retrieval.embedding_store import EmbeddingIndexStore  # 导入本地 embedding 索引存储
from app.retrieval.reranker import build_reranker  # 导入 reranker 构造函数
from app.retrieval.retriever import LocalRetriever  # 导入本地检索或 embedding 相关组件
from app.requirements_parser import RequirementDocumentParser  # 导入客户需求文档解析器
from app.storage import JsonIndexStore  # 导入 JSONL 本地索引存储实现
from app.web_search import build_web_search_client  # 导入联网搜索客户端构造函数


class IngestPipeline:  # 封装资料导入、切片和索引写入流程
    def __init__(self, store: JsonIndexStore | None = None, config: AppConfig | None = None) -> None:  # 初始化对象所需依赖和配置
        self.config = config or load_config()  # 加载 embedding 等索引配置
        self.store = store or JsonIndexStore()  # 初始化或更新对象属性 self.store
        self.embedding_store = EmbeddingIndexStore(self.store.index_dir)  # 初始化 embedding 索引存储
        self.embedding_client = build_embedding_client(self.config.embedding)  # 构建可选 embedding 客户端
        self.parser = DocumentParser()  # 初始化或更新对象属性 self.parser
        self.chunker = DocumentChunker()  # 初始化或更新对象属性 self.chunker

    def ingest(self, path: str | Path) -> dict:  # 定义 ingest 函数或方法
        records = []  # 保存当前流程中的 records 数据
        chunks = []  # 保存当前流程中的 chunks 数据
        files = iter_supported_files(path)  # 保存当前流程中的 files 数据
        for file_path in files:  # 遍历当前集合中的每个元素
            pages = self.parser.load_pages(file_path)  # 保存当前流程中的 pages 数据
            record = self.chunker.build_record(file_path, pages)  # 计算并保存 record
            file_chunks = self.chunker.chunk_pages(record, pages)  # 计算并保存 file_chunks
            records.append(record)  # 将当前结果追加到列表
            chunks.extend(file_chunks)  # 将多个元素批量追加到列表

        embedding_count = 0  # 保存本次生成的 embedding 数量
        if records or chunks:  # 检查条件：records or chunks
            file_paths = {str(file_path) for file_path in files}  # 记录本次导入文件路径集合
            self.store.replace_files(records, chunks, file_paths)  # 替换这些文件的旧文档、旧 chunk
            try:  # 导入资料时尝试同步生成 embedding，但不让网络问题破坏基础索引
                embedding_count = self.embedding_store.build_missing_embeddings(chunks, self.embedding_client, self.config.embedding.model)  # 为新 chunk 生成 embedding
            except Exception:  # embedding 服务不可用时保留 chunks 索引并回退关键词检索
                embedding_count = 0  # 返回零表示本次没有成功生成 embedding
            all_chunk_ids = {chunk.id for chunk in self.store.load_chunks()}  # 读取当前索引中仍存在的 chunk ID
            self.embedding_store.prune_to_chunk_ids(all_chunk_ids)  # 清理旧文件替换后遗留的 embedding

        models = sorted({model for record in records for model in record.chip_models})  # 保存当前流程中的 models 数据
        return {  # 返回 {
            "files": len(files),  # 执行当前业务逻辑
            "documents": len(records),  # 执行当前业务逻辑
            "chunks": len(chunks),  # 执行当前业务逻辑
            "embeddings": embedding_count,  # 返回本次生成的 embedding 数量
            "chip_models": models,  # 执行当前业务逻辑
        }  # 结束当前多行结构


class QaPipeline:  # 封装问题解析、证据检索和答案生成流程
    def __init__(self, store: JsonIndexStore | None = None, config: AppConfig | None = None) -> None:  # 初始化对象所需依赖和配置
        self.config = config or load_config()  # 加载环境变量中的 RAG 增强配置
        self.store = store or JsonIndexStore()  # 初始化或更新对象属性 self.store
        self.embedding_store = EmbeddingIndexStore(self.store.index_dir)  # 初始化 embedding 索引存储
        self.question_parser = QuestionParser()  # 初始化或更新对象属性 self.question_parser
        self.embedding_client = build_embedding_client(self.config.embedding)  # 构建可选 embedding 客户端
        self.reranker = build_reranker(self.config.reranker)  # 构建可选 reranker 客户端
        self.web_search_client = build_web_search_client(self.config.search)  # 构建可选联网搜索客户端
        self.llm_client = build_llm_client(self.config.llm, self.config.use_llm_reader)  # 构建可选 LLM Reader 客户端
        self.answer_generator = AnswerGenerator(self.llm_client, self.config.use_llm_reader)  # 初始化答案生成器

    def ask(self, raw_question: str, top_k: int = 5, answer_mode: str = "full") -> Answer:  # 根据回答模式执行问答流程
        question = self.question_parser.parse(raw_question)  # 保存去除型号后的问题正文
        chunks = self.store.load_chunks()  # 保存当前流程中的 chunks 数据
        self.embedding_store.attach_embeddings(chunks, self.config.embedding.model)  # 从 embeddings.jsonl 读取有效 chunk embedding
        recall_k = max(top_k, self.config.local_recall_k)  # 使用较大的初召回数量给 reranker 留空间
        local_retriever = LocalRetriever(chunks, embedding_client=self.embedding_client)  # 构建带可选 embedding 的本地检索器
        related_queries = build_related_queries(question.question)  # 根据问题自动补齐需要参考的相关模块查询
        question.constraints["related_modules"] = infer_related_modules(question.question)  # 保存推断出的相关模块供回答生成使用
        local_candidates = _merge_evidence_results(  # 合并原始问题和扩展查询的检索结果
            local_retriever.search(query, question.chip_model, top_k=recall_k) for query in related_queries  # 针对每条相关查询执行本地召回
        )  # 结束候选证据合并
        try:  # 捕获 reranker 外部服务异常，保证本地检索可用
            evidence = self.reranker.rerank(question.question, local_candidates, top_k=top_k)  # 对本地候选证据重排并截断
        except Exception:  # reranker 调用失败时回退到本地初召回排序
            evidence = local_candidates[:top_k]  # 使用本地检索分数最高的候选证据
        web_evidence = []  # 默认不使用联网证据
        if answer_mode != "simple":  # 完整解释模式才尝试联网补充
            web_query = _build_web_query(question.chip_model, question.question)  # 构造联网搜索 query
            try:  # 捕获联网搜索异常，避免搜索服务故障阻断问答
                web_evidence = self.web_search_client.search(web_query, self.config.web_recall_k)  # 执行可选联网搜索
            except Exception:  # 联网搜索失败时返回空联网证据
                web_evidence = []  # 使用空列表表示没有可用联网证据
        return self.answer_generator.generate(question, evidence, web_evidence=web_evidence, answer_mode=answer_mode)  # 生成最终答案

    def evaluate_requirements(self, chip_model: str, requirement_text: str, top_k: int = 8, answer_mode: str = "full") -> Answer:  # 基于客户需求明细评估芯片是否满足
        question = _build_requirement_question(chip_model, requirement_text)  # 将需求明细转换为评估问题
        requirement_top_k = max(top_k, 20)  # 复杂需求覆盖接口、视频、存储、网络等模块，至少保留二十条证据
        return self.ask(question, top_k=requirement_top_k, answer_mode=answer_mode)  # 复用现有 RAG 问答流程生成评估结果

    def evaluate_requirement_file(self, chip_model: str, requirement_path: str, top_k: int = 8, answer_mode: str = "full") -> Answer:  # 解析需求文件并评估芯片满足度
        requirement_text = RequirementDocumentParser().parse_path(requirement_path)  # 解析本地需求文档
        return self.evaluate_requirements(chip_model, requirement_text, top_k=top_k, answer_mode=answer_mode)  # 基于解析文本生成评估结果

    def evaluate_requirement_upload(self, chip_model: str, file_name: str, content_base64: str, top_k: int = 8, answer_mode: str = "full") -> Answer:  # 解析上传需求文件并评估芯片满足度
        requirement_text = RequirementDocumentParser().parse_upload(file_name, content_base64)  # 解析上传需求文件
        return self.evaluate_requirements(chip_model, requirement_text, top_k=top_k, answer_mode=answer_mode)  # 基于解析文本生成评估结果


class EmbeddingPipeline:  # 封装已有 chunk 的 embedding 重建流程
    def __init__(self, store: JsonIndexStore | None = None, config: AppConfig | None = None) -> None:  # 初始化重建流程依赖
        self.config = config or load_config()  # 加载 embedding 配置
        self.store = store or JsonIndexStore()  # 初始化索引存储
        self.embedding_store = EmbeddingIndexStore(self.store.index_dir)  # 初始化 embedding 存储
        self.embedding_client = build_embedding_client(self.config.embedding)  # 构建可选 embedding 客户端

    def rebuild(self) -> dict:  # 为当前 chunks.jsonl 中缺失或失效的 chunk 生成 embedding
        validate_embedding_config(self.config.embedding)  # 主动重建 embedding 时要求配置完整，避免静默生成零条
        chunks = self.store.load_chunks()  # 读取当前全部 chunk
        generated = self.embedding_store.build_missing_embeddings(chunks, self.embedding_client, self.config.embedding.model)  # 生成缺失或失效 embedding
        removed = self.embedding_store.prune_to_chunk_ids({chunk.id for chunk in chunks})  # 清理孤儿 embedding 记录
        return {  # 返回重建统计信息
            "chunks": len(chunks),  # 返回当前 chunk 总数
            "embeddings_generated": generated,  # 返回本次生成的 embedding 数量
            "embeddings_removed": removed,  # 返回清理的孤儿 embedding 数量
            "embedding_model": self.config.embedding.model,  # 返回使用的 embedding 模型
        }  # 结束统计字典


def _merge_evidence_results(results) -> list:  # 合并多轮检索结果并按最高分去重
    merged = {}  # 使用来源位置和摘录作为 key 合并证据
    for evidence_list in results:  # 遍历每轮检索返回的证据列表
        for evidence in evidence_list:  # 遍历单条证据
            key = (evidence.file_name, evidence.page_number, evidence.slide_number, evidence.quote[:180])  # 构造稳定去重 key
            existing = merged.get(key)  # 读取已有证据
            if existing is None or evidence.relevance_score > existing.relevance_score:  # 保留相关性更高的版本
                merged[key] = evidence  # 保存当前证据
    return sorted(merged.values(), key=lambda item: item.relevance_score, reverse=True)  # 返回按分数排序的合并结果


def _build_web_query(chip_model: str | None, question: str) -> str:  # 构造适合联网搜索的查询语句
    if chip_model:  # 有目标芯片型号时把型号放到搜索词前面
        return f"{chip_model} datasheet {question}"  # 返回包含型号和 datasheet 的搜索词
    return question  # 没有型号时直接使用问题作为搜索词


def _build_requirement_question(chip_model: str, requirement_text: str) -> str:  # 构造客户需求满足度评估问题
    clipped_requirements = requirement_text[:12000]  # 限制需求文本长度，避免一次请求过长
    return (  # 返回结构化评估问题
        f"芯片型号：{chip_model} 问题：请评估该芯片是否可以满足客户项目需求明细。\n"  # 写入目标芯片和任务
        "回答要求：如果可以满足客户需求，结论必须写“" + chip_model + "型号的芯片可以满足客户的要求”；"  # 指定满足时结论措辞
        "如果不能满足，结论必须明确写不能满足，并指出客户需求中具体哪一项应用或规格不满足。\n"  # 指定不满足时结论措辞
        "请逐项对比客户需求和 datasheet 规格，给出对应论据、页码和推导。\n"  # 要求逐项对比证据
        "客户项目需求明细如下：\n"  # 标记需求正文开始
        f"{clipped_requirements}"  # 写入客户需求文本
    )  # 结束评估问题构造
