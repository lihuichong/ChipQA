from __future__ import annotations  # 启用延迟类型注解，避免运行时前向引用问题

import argparse  # 导入命令行参数解析工具
import json  # 导入 JSON 序列化和反序列化工具

from app.pipeline import EmbeddingPipeline, IngestPipeline, QaPipeline  # 导入资料导入、embedding 和问答流程
from app.web import DEFAULT_HOST, DEFAULT_PORT, run_server  # 导入当前模块需要的依赖


def main() -> None:  # 定义 main 函数或方法
    parser = argparse.ArgumentParser(description="Local chip datasheet QA")  # 创建命令行参数解析器
    subparsers = parser.add_subparsers(dest="command", required=True)  # 创建子命令解析器集合

    ingest_parser = subparsers.add_parser("ingest", help="Ingest PDF/PPT/PPTX/TXT/MD files")  # 创建 ingest_parser 子命令解析器
    ingest_parser.add_argument("path", help="File or directory path")  # 计算并保存 ingest_parser.add_argument("path", help

    ask_parser = subparsers.add_parser("ask", help="Ask a question against local index")  # 创建 ask_parser 子命令解析器
    ask_parser.add_argument("question", help="Question text")  # 计算并保存 ask_parser.add_argument("question", help
    ask_parser.add_argument("--top-k", type=int, default=5)  # 计算并保存 ask_parser.add_argument("--top-k", type
    ask_parser.add_argument("--mode", choices=["simple", "full"], default="full")  # 选择简单回答或完整解释模式

    eval_parser = subparsers.add_parser("evaluate", help="Evaluate customer requirements against a chip")  # 创建客户需求评估子命令
    eval_parser.add_argument("--chip", required=True, help="Target chip model")  # 读取目标芯片型号
    eval_group = eval_parser.add_mutually_exclusive_group(required=True)  # 创建需求输入互斥参数组
    eval_group.add_argument("--requirements-file", help="Customer requirement file path")  # 读取客户需求文件路径
    eval_group.add_argument("--requirements-text", help="Customer requirement text")  # 读取客户需求文本
    eval_parser.add_argument("--top-k", type=int, default=8)  # 读取需求评估证据数量
    eval_parser.add_argument("--mode", choices=["simple", "full"], default="full")  # 读取回答模式

    subparsers.add_parser("rebuild-embeddings", help="Build or refresh chunk embeddings")  # 创建 embedding 重建子命令

    serve_parser = subparsers.add_parser("serve", help="Start the local web UI")  # 创建 serve_parser 子命令解析器
    serve_parser.add_argument("--host", default=DEFAULT_HOST)  # 计算并保存 serve_parser.add_argument("--host", default
    serve_parser.add_argument("--port", type=int, default=DEFAULT_PORT)  # 计算并保存 serve_parser.add_argument("--port", type

    args = parser.parse_args()  # 计算并保存 args
    if args.command == "ingest":  # 检查条件：args.command == "ingest"
        result = IngestPipeline().ingest(args.path)  # 保存 result 的处理结果
        print(json.dumps(result, ensure_ascii=False, indent=2))  # 将结果或服务地址输出到控制台
        return  # 执行当前业务逻辑

    if args.command == "ask":  # 检查条件：args.command == "ask"
        answer = QaPipeline().ask(args.question, top_k=args.top_k, answer_mode=args.mode)  # 保存 answer 的处理结果
        print(answer.to_markdown(mode=args.mode))  # 将结果或服务地址输出到控制台
        return  # 执行当前业务逻辑

    if args.command == "evaluate":  # 检查条件：args.command == "evaluate"
        pipeline = QaPipeline()  # 初始化问答评估流程
        if args.requirements_file:  # 使用需求文件作为输入
            answer = pipeline.evaluate_requirement_file(args.chip, args.requirements_file, top_k=args.top_k, answer_mode=args.mode)  # 解析需求文件并评估
        else:  # 使用命令行需求文本作为输入
            answer = pipeline.evaluate_requirements(args.chip, args.requirements_text, top_k=args.top_k, answer_mode=args.mode)  # 评估需求文本
        print(answer.to_markdown(mode=args.mode))  # 输出评估结果
        return  # 执行当前业务逻辑

    if args.command == "rebuild-embeddings":  # 检查条件：args.command == "rebuild-embeddings"
        result = EmbeddingPipeline().rebuild()  # 执行 embedding 重建流程
        print(json.dumps(result, ensure_ascii=False, indent=2))  # 将重建统计输出到控制台
        return  # 执行当前业务逻辑

    if args.command == "serve":  # 检查条件：args.command == "serve"
        run_server(args.host, args.port)  # 执行当前业务逻辑
        return  # 执行当前业务逻辑


if __name__ == "__main__":  # 检查条件：__name__ == "__main__"
    main()  # 执行当前业务逻辑
