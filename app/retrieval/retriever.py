from __future__ import annotations  # 启用延迟类型注解，避免运行时前向引用问题

import math  # 导入数学函数用于相关性打分
import re  # 导入正则表达式工具
from collections import Counter  # 导入 Counter 统计检索 token 词频

from app.chips.model_extractor import normalize_model  # 导入芯片型号抽取和规范化工具
from app.models import DocumentChunk, Evidence  # 导入问答流程共享的数据结构
from app.retrieval.embeddings import EmbeddingClient, cosine_similarity  # 导入可选向量检索能力


TOKEN_PATTERN = re.compile(r"[A-Za-z0-9]+|[\u4e00-\u9fff]")  # 计算并保存 TOKEN_PATTERN


class LocalRetriever:  # 实现本地关键词检索、型号过滤和证据排序
    def __init__(self, chunks: list[DocumentChunk], embedding_client: EmbeddingClient | None = None) -> None:  # 初始化对象所需依赖和配置
        self.chunks = chunks  # 初始化或更新对象属性 self.chunks
        self.embedding_client = embedding_client  # 保存可选 embedding 客户端用于语义召回

    def search(self, question: str, chip_model: str | None, top_k: int = 5) -> list[Evidence]:  # 定义 search 函数或方法
        normalized_model = normalize_model(chip_model)  # 计算并保存 normalized_model
        candidates = [  # 保存当前流程中的 candidates 数据
            chunk  # 执行当前业务逻辑
            for chunk in self.chunks  # 遍历当前集合中的每个元素
            if _matches_chip_model(chunk, normalized_model)  # 检查条件：_matches_chip_model(chunk, normalized_model)
        ]  # 结束当前多行结构
        query_tokens = _tokenize(question)  # 保存检索打分中间值 query_tokens
        query_embedding = self._embed_query(question)  # 生成可选问题向量
        scored: list[tuple[float, DocumentChunk]] = []  # 保存当前流程中的 scored 数据
        for chunk in candidates:  # 遍历当前集合中的每个元素
            score = _score_chunk(question, query_tokens, chunk)  # 保存检索打分中间值 score
            score += self._semantic_score(query_embedding, chunk)  # 将可选语义分合入总分
            if score > 0:  # 检查条件：score > 0
                scored.append((score, chunk))  # 将当前结果追加到列表

        scored.sort(key=lambda item: item[0], reverse=True)  # 计算并保存 scored.sort(key
        unique_scored = _deduplicate_scored_chunks(scored)  # 计算并保存 unique_scored
        return [  # 返回 [
            Evidence(  # 执行当前业务逻辑
                source_type="local",  # 标记证据来源类型
                file_name=chunk.file_name,  # 保存资料文件名
                file_path=chunk.file_path,  # 保存资料文件路径
                page_number=chunk.page_number,  # 保存 PDF 页码
                slide_number=chunk.slide_number,  # 保存 PPT Slide 编号
                quote=_compact_quote(chunk.text),  # 保存可引用的原文片段
                summary="该片段来自目标芯片资料，和用户问题存在关键词或语义线索重合。",  # 保存证据与问题的关联说明
                relevance_score=score,  # 保存检索相关性分数
            )  # 结束当前多行结构
            for score, chunk in unique_scored[:top_k]  # 遍历当前集合中的每个元素
        ]  # 结束当前多行结构

    def _embed_query(self, question: str) -> list[float]:  # 生成问题向量并吞掉配置期网络异常
        if self.embedding_client is None:  # 未配置 embedding 时跳过语义召回
            return []  # 返回空向量表示不使用语义分
        try:  # 防止 embedding 服务失败导致本地 RAG 整体不可用
            return self.embedding_client.embed(question)  # 调用 embedding 服务生成问题向量
        except Exception:  # 捕获外部服务错误并回退关键词检索
            return []  # 返回空向量让上层继续使用关键词分

    def _semantic_score(self, query_embedding: list[float], chunk: DocumentChunk) -> float:  # 计算单个 chunk 的可选语义分
        if not query_embedding or self.embedding_client is None:  # 没有问题向量或客户端时不计算
            return 0.0  # 返回零分
        cached_embedding = chunk.metadata.get("embedding") if chunk.metadata else None  # 尝试读取索引中缓存的 chunk 向量
        if not cached_embedding:  # 没有缓存 embedding 时绝不在问答阶段临时生成
            return 0.0  # 返回零分
        return max(0.0, cosine_similarity(query_embedding, cached_embedding)) * 6.0  # 将余弦相似度映射到检索加权分


def _tokenize(text: str) -> list[str]:  # 定义 _tokenize 函数或方法
    return [token.lower() for token in TOKEN_PATTERN.findall(text)]  # 返回 [token.lower() for token in TOKEN_PATTER


def _matches_chip_model(chunk: DocumentChunk, normalized_model: str | None) -> bool:  # 定义 _matches_chip_model 函数或方法
    if normalized_model is None:  # 检查条件：normalized_model is None
        return True  # 条件满足时返回 True
    chunk_model = normalize_model(chunk.chip_model)  # 计算并保存 chunk_model
    if chunk_model == normalized_model:  # 检查条件：chunk_model == normalized_model
        return True  # 条件满足时返回 True
    searchable_text = f"{chunk.file_name}\n{chunk.text}".upper()  # 计算并保存 searchable_text
    return normalized_model in searchable_text  # 返回 normalized_model in searchable_text


def _score(query_tokens: list[str], chunk_tokens: list[str]) -> float:  # 定义 _score 函数或方法
    if not query_tokens or not chunk_tokens:  # 检查条件：not query_tokens or not chunk_tokens
        return 0.0  # 返回 0.0
    query_counts = Counter(query_tokens)  # 计算并保存 query_counts
    chunk_counts = Counter(chunk_tokens)  # 计算并保存 chunk_counts
    overlap = set(query_counts) & set(chunk_counts)  # 保存检索打分中间值 overlap
    if not overlap:  # 检查条件：not overlap
        return 0.0  # 返回 0.0
    score = 0.0  # 保存检索打分中间值 score
    for token in overlap:  # 遍历当前集合中的每个元素
        score += (1 + math.log(query_counts[token] + 1)) * (1 + math.log(chunk_counts[token] + 1))  # 计算并保存 score +
    return score / math.sqrt(len(chunk_tokens))  # 返回 score / math.sqrt(len(chunk_tokens))


def _score_chunk(question: str, query_tokens: list[str], chunk: DocumentChunk) -> float:  # 定义 _score_chunk 函数或方法
    score = _score(query_tokens, _tokenize(chunk.text))  # 保存检索打分中间值 score
    question_lower = question.lower()  # 计算并保存 question_lower
    chunk_text = chunk.text  # 计算并保存 chunk_text
    if "工作电压" in question or "operating voltage" in question_lower:  # 检查条件："工作电压" in question or "operating voltage" in question_lower
        if "工作电压" in chunk_text or "operating voltage" in chunk_text.lower():  # 检查条件："工作电压" in chunk_text or "operating voltage" in chunk_text.lo
            score += 8.0  # 计算并保存 score +
        if "建议的运作条件" in chunk_text or "recommended" in chunk_text.lower():  # 检查条件："建议的运作条件" in chunk_text or "recommended" in chunk_text.lower
            score += 4.0  # 计算并保存 score +
        if "破坏性电压" in chunk_text or "absolute maximum" in chunk_text.lower():  # 检查条件："破坏性电压" in chunk_text or "absolute maximum" in chunk_text.lo
            score -= 6.0  # 计算并保存 score -
    if _is_camera_capacity_query(question, question_lower):  # 摄像头容量问题需要优先召回完整视频链路模块
        chunk_lower = chunk_text.lower()  # 统一转换为小写，便于匹配英文关键词
        if any(term in chunk_text or term in chunk_lower for term in ["视频输入", "mipi rx", "sensor", "Sensor", "VI (Video Input)"]):  # 匹配视频输入和 MIPI Rx 证据
            score += 8.0  # 提升视频输入接口证据
        if any(term in chunk_text or term in chunk_lower for term in ["ISP", "图像处理", "图像增强", "多路"]):  # 匹配 ISP 和图像处理证据
            score += 6.0  # 提升 ISP 证据
        if any(term in chunk_text or term in chunk_lower for term in ["H.265", "H.264", "视频编码", "编码总性能", "VCU"]):  # 匹配视频编码吞吐证据
            score += 7.0  # 提升编解码证据
        if any(term in chunk_text for term in ["整体规格", "产品概述", "Overview", "概述"]):  # 匹配芯片整体规格页
            score += 3.0  # 提升总览证据
        if any(term in chunk_text for term in ["UART", "Wiegand", "PWM", "KEYSCAN", "USB DRD"]):  # 过滤明显无关的外设章节
            score -= 10.0  # 降低无关外设证据
    return score  # 返回 score


def _is_camera_capacity_query(question: str, question_lower: str) -> bool:  # 判断是否为摄像头数量、分辨率或帧率问题
    camera_terms = ["sensor", "camera", "摄像头", "镜头"]  # 定义摄像头关键词
    capacity_terms = ["mp", "5m", "200万", "分辨率", "fps", "帧率", "几个", "几路", "多少路"]  # 定义规格关键词
    has_camera = any(term in question_lower or term in question for term in camera_terms)  # 判断是否提到摄像头主题
    has_capacity = any(term in question_lower or term in question for term in capacity_terms)  # 判断是否提到容量规格
    return has_camera and has_capacity  # 同时命中才启用视频链路加权


def _deduplicate_scored_chunks(scored: list[tuple[float, DocumentChunk]]) -> list[tuple[float, DocumentChunk]]:  # 定义 _deduplicate_scored_chunks 函数或方法
    seen: set[tuple[str, int | None, int | None, str]] = set()  # 计算并保存 seen
    unique: list[tuple[float, DocumentChunk]] = []  # 计算并保存 unique
    for score, chunk in scored:  # 遍历当前集合中的每个元素
        key = (chunk.file_name, chunk.page_number, chunk.slide_number, _compact_quote(chunk.text, limit=160))  # 计算并保存 key
        if key in seen:  # 检查条件：key in seen
            continue  # 当前项不符合条件，跳过后续处理
        seen.add(key)  # 执行当前业务逻辑
        unique.append((score, chunk))  # 将当前结果追加到列表
    return unique  # 返回 unique


def _compact_quote(text: str, limit: int = 500) -> str:  # 定义 _compact_quote 函数或方法
    compact = " ".join(text.split())  # 计算并保存 compact
    if len(compact) <= limit:  # 检查条件：len(compact) <= limit
        return compact  # 返回 compact
    return compact[: limit - 3] + "..."  # 返回 compact[: limit - 3] + "..."
