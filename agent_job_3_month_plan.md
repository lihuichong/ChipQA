# 三个月 Agent 开发求职学习路线

适用背景：算法背景，当前产品经理，有 Python 和大模型基础，目标冲大厂 Agent / 大模型应用相关岗位。

时间投入：工作日每天 2 小时，周末每天 4 小时。每周约 18 小时，三个月约 216 小时。

主项目：企业知识库 + 工作流 Agent。

最终目标：12 周后能够展示一个面向企业知识问答和业务流程执行的 Agent 系统，支持 RAG、工具调用、状态管理、评测、日志、成本统计和失败恢复。

## 总体节奏

- 第 1 个月：打底并做出可运行 Demo
- 第 2 个月：把 Demo 变成有工程质量的 Agent 系统
- 第 3 个月：补评测、产品化、简历和面试表达

每周原则：

- 工作日每天 2 小时：学习 + 小功能实现
- 周末每天 4 小时：集中写代码、整理项目文档、复盘
- 每周至少产出一个可展示结果，不只看资料

## 第 1 周：搭环境，理解 Agent 基础

目标：搞清楚 Agent、RAG、tool calling、workflow 的基本关系。

学习内容：

- LLM API 调用
- function calling / tool calling
- structured output
- Agent 和普通聊天机器人的区别
- LangGraph 基础概念：node、edge、state、checkpoint

实践任务：

- 建一个 Python 项目
- 用 FastAPI 或命令行实现一个最小聊天接口
- 接入一个大模型 API
- 实现一个简单 tool，比如 get_current_time、calculator
- 让模型决定是否调用 tool

周末产出：

- 一个最小 Agent Demo
- README 写清楚：Agent 如何判断是否调用工具

## 第 2 周：RAG 基础

目标：做出一个能基于文档回答问题的知识库。

学习内容：

- embedding
- chunking
- vector database
- top-k retrieval
- prompt with context
- 引用来源

实践任务：

- 支持上传或读取 PDF / Markdown / TXT
- 文档切块
- 存入向量库，推荐先用 Chroma 或 FAISS
- 用户提问后召回相关片段
- 回答时附带来源

周末产出：

- 一个基础 RAG 问答系统
- 准备 10 个测试问题，记录哪些答对、哪些答错

## 第 3 周：RAG 质量优化

目标：从“能答”升级到“答得相对可靠”。

学习内容：

- chunk size / overlap 对效果的影响
- rerank
- hybrid search 基本概念
- 幻觉与拒答
- query rewrite

实践任务：

- 调整 chunk 策略
- 增加引用片段展示
- 增加“找不到答案就拒答”
- 尝试加 rerank，如果时间不够，先把接口位置留好
- 做一个简单评测脚本，批量跑问题

周末产出：

- 一份 RAG 评测表：问题、期望答案、实际答案、是否命中来源、是否幻觉
- README 增加“RAG 优化策略”

## 第 4 周：LangGraph 工作流 Agent

目标：把 RAG 和工具调用编排成一个工作流。

学习内容：

- LangGraph state
- 条件分支
- 多节点流程
- retry / fallback
- human-in-the-loop 概念

实践任务：

设计流程：

```text
用户问题
-> 判断意图
-> 如果是知识问答，走 RAG
-> 如果是业务任务，调用工具
-> 如果信息不足，请求补充
-> 输出结构化结果
```

工具可以先做几个模拟的：

- 查询客户信息
- 生成邮件草稿
- 创建待办事项
- 查询订单状态

周末产出：

- Agent 可以区分“问知识”和“办任务”
- 项目结构初步成型

第一个月结束时，应有一个能演示的版本：用户问公司制度，Agent 查知识库回答；用户说“帮我给客户生成一封跟进邮件”，Agent 调用工具生成草稿。

## 第 5 周：后端服务化

目标：从脚本变成一个像样的服务。

学习内容：

- FastAPI
- Pydantic
- API 设计
- 日志
- 配置管理
- 错误处理

实践任务：

- 做 REST API
- /chat
- /documents/upload
- /documents/search
- /agent/run
- 增加配置文件
- 增加基础日志
- 把模型调用、RAG、Agent workflow 拆成模块

周末产出：

- 一个可通过 API 调用的 Agent 服务
- README 增加接口说明

## 第 6 周：状态管理与多轮对话

目标：让 Agent 不是“一问一答”，而是能记住任务进度。

学习内容：

- conversation state
- thread/session
- short-term memory
- checkpoint
- task state

实践任务：

- 增加 session_id
- 保存多轮对话历史
- 保存 Agent 当前任务状态
- 支持用户补充信息后继续执行
- 示例流程：
  - 用户：“帮我写一封客户跟进邮件”
  - Agent：“客户是谁？”
  - 用户：“张三，上周演示过产品”
  - Agent：继续生成邮件

周末产出：

- 一个多轮任务 Demo
- 项目文档写清楚 state 设计

## 第 7 周：工具调用可靠性

目标：让 Agent 遇到失败时有处理策略。

学习内容：

- tool schema 设计
- 参数校验
- retry
- timeout
- fallback
- 人工确认

实践任务：

- 给工具参数加 Pydantic 校验
- 工具调用失败时返回可解释错误
- 高风险操作前要求确认
- 比如发送邮件、创建工单、修改数据前先让用户确认
- 增加 tool call log

周末产出：

- 一次完整流程展示：Agent 计划调用工具，用户确认后执行
- 一份工具调用日志样例

## 第 8 周：权限、安全与成本意识

目标：补大厂非常看重的生产化意识。

学习内容：

- prompt injection
- 数据权限
- 敏感信息处理
- token 成本
- latency
- cache

实践任务：

- RAG 检索时增加文档权限字段，比如 department/user_role
- 增加基础敏感词或敏感字段过滤
- 记录每次调用 token、耗时、模型名
- 对相同问题做简单 cache
- 增加 prompt injection 防护提示和工具白名单

周末产出：

- 一个安全与成本设计文档
- API 返回中包含 latency / token usage / source info

第二个月结束时，应能够讲清楚：不仅做了 Agent，还考虑了权限、状态、失败恢复、成本和可观测性。

## 第 9 周：Agent 评测体系

目标：这是区别于普通 Demo 开发者的关键。

学习内容：

- golden dataset
- task success rate
- retrieval hit rate
- answer faithfulness
- LLM-as-judge
- regression test

实践任务：

- 建一个 eval_dataset.json
- 至少 30 条测试样例
- 分类：
  - 知识问答
  - 多轮任务
  - 工具调用
  - 拒答
  - 权限场景
- 写评测脚本
- 输出指标：
  - answer pass rate
  - retrieval hit rate
  - tool success rate
  - average latency
  - average token cost

周末产出：

- eval_report.md
- 一张指标表

## 第 10 周：做一个简单前端或演示界面

目标：让面试官能直观看到项目。

建议：如果偏工程，用 React；如果想节省时间，用 Streamlit 或 Gradio。建议先用 Streamlit，效率最高。

实践任务：

- 左侧文档上传
- 中间聊天窗口
- 右侧展示：
  - 检索来源
  - 工具调用记录
  - token 成本
  - Agent 当前状态
- 增加几个预设 Demo 问题

周末产出：

- 一个可以录屏展示的界面
- 录一个 2-3 分钟项目演示视频，自己留着面试前复习

## 第 11 周：简历与项目包装

目标：把项目讲成大厂能听懂的能力。

准备三套表达。

30 秒版本：

> 我做了一个企业知识库和工作流 Agent，支持基于文档的 RAG 问答、业务工具调用、多轮状态管理、人工确认和评测体系。项目重点不是简单聊天，而是模拟企业内部 Agent 如何可靠地接入业务流程。

3 分钟版本：

讲清楚：

- 为什么做
- 架构是什么
- RAG 怎么做
- Agent 怎么编排
- 工具调用怎么保证可靠
- 如何评测
- 遇到的问题和优化

10 分钟版本：

准备系统设计级别讲法：

- 模块架构
- 数据流
- 权限设计
- 状态设计
- 评测指标
- 后续扩展

简历项目 bullet 示例：

- 基于 LangGraph 设计企业工作流 Agent，支持意图识别、RAG 问答、工具调用、人工确认与失败恢复。
- 构建文档知识库 RAG 流程，支持文档切块、向量检索、引用溯源、拒答策略与召回评测。
- 设计 Agent 评测集，覆盖知识问答、多轮任务、工具调用、权限控制等场景，统计任务成功率、检索命中率、延迟和 token 成本。
- 实现 FastAPI 服务与 Streamlit 演示界面，展示对话状态、检索来源、工具调用日志和成本监控。

## 第 12 周：面试冲刺

目标：进入投递状态。

准备内容：

1. 系统设计题
   - 设计企业知识库 Agent
   - 设计客服 Agent
   - 设计数据分析 Agent
   - 设计多 Agent 协作平台

2. RAG 高频题
   - RAG 为什么会答错？
   - chunk 怎么切？
   - embedding 和 rerank 怎么选？
   - 怎么降低幻觉？
   - 怎么做权限过滤？

3. Agent 高频题
   - Agent 和 workflow 的区别是什么？
   - 工具调用失败怎么办？
   - 多轮任务如何保存状态？
   - 如何防止 Agent 乱调用工具？
   - 什么场景不适合 Agent？

4. 产品判断题
   - 如何判断一个场景是否适合 Agent？
   - Agent MVP 怎么定义？
   - 如何从 Demo 上线到生产？
   - 如何评估业务价值？

5. 行为面试
   - 你为什么从产品转 Agent？
   - 你的算法背景有什么帮助？
   - 你相比纯工程候选人的优势是什么？

回答核心：

> 我不是单纯从产品转技术，而是希望把算法理解、产品判断和工程实现结合起来，做能真正落地的 Agent 系统。

## 每周固定时间安排

工作日 2 小时：

- 30 分钟：学习文档/课程
- 75 分钟：写代码或改项目
- 15 分钟：记录今天学到什么、遇到什么问题

周末 4 小时：

- 60 分钟：补理论
- 120 分钟：集中实现功能
- 45 分钟：测试和修 bug
- 15 分钟：更新 README / 项目日志

每周日晚上复盘：

- 本周实现了什么？
- 哪个功能可以面试展示？
- 哪个概念还讲不清？
- 下周最重要的交付是什么？

## 优先级提醒

对冲大厂最有价值的是：

1. RAG 质量与评测
2. Agent 工作流编排
3. 工具调用可靠性
4. 状态管理
5. 产品化表达

框架本身不是重点。会 LangGraph 是加分，但更重要的是能讲清楚为什么这么设计、失败时怎么办、怎么评估效果、怎么上线。

建议第一周就开始建项目，不要先看一个月资料。Agent 这个方向，只有边做边撞问题，理解才会真的长出来。
