# 第 1 周：搭环境，理解 Agent 基础

## 学习目标

学完本周后，我应该能够：

- 用自己的话解释 LLM Agent 是什么
- 说明 Agent 和普通 Chatbot、Workflow、RAG 的区别
- 理解 tool calling / function calling 的基本原理
- 写出一个最小可运行 Agent Demo
- 让模型根据用户问题决定是否调用工具
- 用 2-3 分钟向面试官讲清楚一个最小 Agent 的工作流程

## 本周核心主题

- LLM API 调用
- Structured Output
- Tool Calling / Function Calling
- Agent 与 Chatbot / Workflow / RAG 的区别
- LangGraph 基础概念：state、node、edge、checkpoint
- 最小 Agent Demo

## 时间安排

工作日每天 2 小时：

- 30 分钟：阅读文档或学习概念
- 75 分钟：写代码
- 15 分钟：记录学习笔记和问题

周末每天 4 小时：

- 60 分钟：补齐原理
- 120 分钟：集中实现 Demo
- 45 分钟：测试与调试
- 15 分钟：更新 README 和学习记录

## Day 1：LLM API 调用

### What：它是什么

LLM API 调用是 Agent 系统最底层的能力。应用程序通过 API 把用户输入、系统提示词、历史消息和工具定义发送给大模型，大模型返回自然语言、结构化数据或工具调用请求。

核心组成：

- model：使用哪个模型
- messages：上下文消息
- system prompt：系统行为约束
- user input：用户输入
- response：模型输出
- token usage：输入和输出的 token 消耗
- latency：调用耗时

最小输入：

```json
{
  "model": "your-model",
  "messages": [
    {"role": "system", "content": "You are a helpful assistant."},
    {"role": "user", "content": "什么是 Agent？"}
  ]
}
```

最小输出：

```json
{
  "content": "Agent 是能够根据目标进行推理、调用工具并完成任务的系统。"
}
```

### Why：为什么需要它

Agent 的推理、规划、工具选择、结果总结都依赖 LLM。没有稳定的 LLM 调用封装，后续 RAG、工具调用、工作流编排都很难工程化。

它解决的问题：

- 把用户自然语言输入交给模型理解
- 让模型生成回答、计划或结构化结果
- 为 tool calling 和 Agent workflow 提供推理能力
- 记录成本、延迟和错误，便于后续优化

上线时需要关注：

- 模型输出不稳定
- 接口超时
- token 成本过高
- 响应格式不符合预期
- 模型供应商切换成本

### How：如何工程实现

建议先封装一个 `LLMClient`，不要在业务代码里到处直接调用模型 API。

推荐结构：

```text
agent_project/
  app/
    llm/
      client.py
      schemas.py
    main.py
  tests/
    test_llm_client.py
  README.md
```

最小实现要做到：

- 从环境变量读取 API key
- 支持传入 messages
- 返回 content
- 记录耗时
- 捕获异常

伪代码：

```python
import time


class LLMClient:
    def __init__(self, model: str):
        self.model = model

    def chat(self, messages: list[dict]) -> dict:
        start = time.time()
        try:
            response = call_model_api(model=self.model, messages=messages)
            return {
                "content": response.content,
                "latency_ms": int((time.time() - start) * 1000),
                "model": self.model,
            }
        except Exception as exc:
            return {
                "content": "",
                "error": str(exc),
                "latency_ms": int((time.time() - start) * 1000),
                "model": self.model,
            }
```

本日产出：

- 一个可以调用模型并打印回答的脚本
- 一条运行记录
- 学习笔记：LLM API 调用的输入、输出、风险

## Day 2：Structured Output

### What：它是什么

Structured Output 是让模型按照指定结构返回结果，比如 JSON、Pydantic schema 或固定字段，而不是只返回自由文本。

普通输出：

```text
我觉得这是一个查天气的问题，需要调用天气工具。
```

结构化输出：

```json
{
  "intent": "weather_query",
  "need_tool": true,
  "tool_name": "get_weather",
  "arguments": {
    "city": "Shanghai"
  }
}
```

### Why：为什么需要它

Agent 系统不能只依赖自然语言输出。工程系统需要稳定字段来做条件判断、路由、工具调用和评测。

它解决的问题：

- 把模型输出变成程序可处理的数据
- 降低解析自由文本的脆弱性
- 支持意图识别、任务分类、工具选择
- 方便写测试和评测

适用场景：

- 意图识别
- 工具选择
- 参数抽取
- 任务规划
- 结果评估

风险：

- 模型可能输出非法 JSON
- 字段可能缺失
- 类型可能错误
- schema 过复杂会降低稳定性

### How：如何工程实现

建议使用 Pydantic 定义结构。

示例 schema：

```python
from pydantic import BaseModel


class IntentResult(BaseModel):
    intent: str
    need_tool: bool
    tool_name: str | None = None
    arguments: dict = {}
```

需要实现：

- 定义输出 schema
- 在 prompt 中明确要求输出 JSON
- 对模型输出做 JSON 解析
- 用 Pydantic 校验
- 解析失败时重试或返回错误

本日产出：

- 一个意图识别函数
- 至少 5 条测试输入
- 记录哪些输出符合 schema，哪些失败

## Day 3：Tool Calling / Function Calling

### What：它是什么

Tool Calling 是让模型根据用户目标选择外部工具，并生成工具调用参数。模型本身不真正执行工具，真实执行由应用程序完成。

典型流程：

```text
用户输入
-> 模型判断是否需要工具
-> 模型输出工具名和参数
-> 程序执行工具
-> 程序把工具结果交还给模型
-> 模型生成最终回答
```

工具可以是：

- 查询天气
- 计算器
- 搜索引擎
- 数据库查询
- CRM 查询
- 邮件草稿生成
- 工单创建

### Why：为什么需要它

LLM 自身不能访问实时数据，也不能直接执行业务操作。Tool Calling 让 Agent 从“会说话”变成“能办事”。

它解决的问题：

- 获取实时信息
- 查询企业内部系统
- 执行业务动作
- 把自然语言任务转成 API 调用
- 让 Agent 接入真实业务流程

大厂面试里经常追问：

- 工具调用失败怎么办？
- 参数错误怎么办？
- 高风险操作如何确认？
- 如何防止 Agent 乱调用工具？
- 如何记录审计日志？

### How：如何工程实现

先实现两个简单工具：

- `calculator(expression: str) -> str`
- `get_current_time() -> str`

推荐工具定义：

```python
from pydantic import BaseModel


class ToolCall(BaseModel):
    name: str
    arguments: dict


class ToolResult(BaseModel):
    name: str
    success: bool
    result: str | None = None
    error: str | None = None
```

工具注册表：

```python
TOOLS = {
    "calculator": calculator,
    "get_current_time": get_current_time,
}
```

执行逻辑：

```python
def execute_tool(tool_call: ToolCall) -> ToolResult:
    tool = TOOLS.get(tool_call.name)
    if tool is None:
        return ToolResult(
            name=tool_call.name,
            success=False,
            error="Unknown tool",
        )

    try:
        result = tool(**tool_call.arguments)
        return ToolResult(
            name=tool_call.name,
            success=True,
            result=str(result),
        )
    except Exception as exc:
        return ToolResult(
            name=tool_call.name,
            success=False,
            error=str(exc),
        )
```

本日产出：

- 一个工具注册表
- 两个可调用工具
- 一个工具执行函数
- 至少 5 个测试用例

## Day 4：Agent、Chatbot、Workflow、RAG 的区别

### What：它们分别是什么

Chatbot：

- 主要进行对话
- 输入用户问题，输出自然语言回答
- 不一定有工具调用和任务状态

Workflow：

- 预先定义好的流程
- 每一步通常由开发者固定
- 稳定、可控，但灵活性有限

RAG：

- 检索增强生成
- 从外部知识库检索上下文
- 主要解决知识注入和事实依据问题

Agent：

- 面向目标执行任务
- 可以推理、规划、调用工具、观察结果、继续行动
- 更强调动态决策和任务完成

### Why：为什么要区分

很多场景不需要 Agent，用普通 Workflow 或 RAG 更稳定。大厂面试会看你是否知道什么时候该用 Agent，什么时候不该用。

适合 Agent 的场景：

- 任务步骤不完全固定
- 需要根据中间结果做决策
- 需要调用多个工具
- 需要多轮补充信息
- 需要处理异常和恢复

不适合 Agent 的场景：

- 流程固定且要求强确定性
- 高风险交易或强合规场景
- 简单 FAQ
- 低容错的核心系统操作

### How：如何工程判断

可以用一个简单判断表：

| 问题 | 如果答案是“是” | 建议 |
| --- | --- | --- |
| 是否只需要回答知识问题？ | 是 | 优先 RAG |
| 流程是否完全固定？ | 是 | 优先 Workflow |
| 是否需要外部工具？ | 是 | 考虑 Tool Calling |
| 是否需要根据中间结果动态决策？ | 是 | 考虑 Agent |
| 是否有高风险操作？ | 是 | 加人工确认和权限控制 |

本日产出：

- 写一页笔记解释四者区别
- 为主项目说明为什么需要 Agent，而不是只用 RAG

## Day 5：LangGraph 基础概念

### What：它是什么

LangGraph 是用于构建状态化 Agent workflow 的框架。它把 Agent 流程建模为图。

核心概念：

- State：流程中的共享状态
- Node：执行某一步逻辑的函数
- Edge：节点之间的连接
- Conditional Edge：根据状态决定下一步
- Checkpoint：保存执行状态，便于恢复和多轮继续

一个最小流程：

```text
start
-> classify_intent
-> call_tool 或 answer_directly
-> final_response
```

### Why：为什么需要它

简单 Agent 可以直接用 if/else 写，但复杂 Agent 很快会变得难维护。LangGraph 的价值是把状态、流程分支、重试、人机协同和 checkpoint 显式化。

它适合：

- 多步骤 Agent
- 多轮任务
- 有条件分支的工作流
- 需要中断和恢复的流程
- 需要 human-in-the-loop 的业务场景

### How：如何工程实现

第一周只需要理解概念和写一个最小图，不追求复杂。

示例流程：

```text
用户输入
-> intent_node
-> 如果 need_tool=true，进入 tool_node
-> 如果 need_tool=false，进入 answer_node
-> final_node
```

State 示例：

```python
from typing import TypedDict


class AgentState(TypedDict):
    user_input: str
    intent: str | None
    need_tool: bool
    tool_name: str | None
    tool_result: str | None
    final_answer: str | None
```

本日产出：

- 画出最小 Agent 流程图
- 定义 `AgentState`
- 写出 3-4 个节点函数的伪代码

## 周末任务：实现最小 Agent Demo

### What：Demo 要做什么

实现一个命令行或 FastAPI 版本的最小 Agent：

- 用户输入一句话
- 模型判断是否需要工具
- 如果需要，输出工具名和参数
- 程序执行工具
- 模型基于工具结果生成最终回答
- 打印工具调用日志、耗时和最终结果

### Why：为什么这个 Demo 重要

这是后续企业知识库 + 工作流 Agent 的最小骨架。RAG、业务工具、多轮状态、评测都可以在这个骨架上继续扩展。

它能证明：

- 你能调用 LLM
- 你能约束模型输出结构
- 你能把模型决策接到真实函数
- 你理解 Agent 的基本执行循环

### How：建议实现路径

推荐目录结构：

```text
agent_project/
  app/
    llm/
      client.py
    agent/
      schemas.py
      runner.py
    tools/
      registry.py
      builtin.py
    main.py
  tests/
    test_tools.py
    test_agent_runner.py
  README.md
```

最小执行流程：

```python
def run_agent(user_input: str) -> str:
    decision = classify_intent_and_tool(user_input)

    if decision.need_tool:
        tool_result = execute_tool(decision.tool_call)
        final_answer = generate_final_answer(
            user_input=user_input,
            tool_result=tool_result,
        )
        return final_answer

    return answer_directly(user_input)
```

建议测试输入：

```text
现在几点？
帮我计算 123 * 456
什么是 Agent？
请帮我查一下客户张三的信息
帮我发一封邮件给李四
```

第一周只需要前 3 个能跑通。后 2 个可以返回“当前工具暂不支持”，为后续业务工具留接口。

## 本周 README 应该记录什么

README 至少包含：

- 项目目标
- 当前支持的能力
- 如何运行
- Agent 执行流程
- 工具列表
- 示例输入输出
- 当前限制
- 下一周计划

示例结构：

```markdown
# Enterprise Agent Demo

## 当前目标

实现一个最小 Agent，支持 LLM 调用、结构化输出和工具调用。

## 运行方式

## Agent 流程

## 支持工具

## 示例

## 当前限制

## 下一步
```

## 面试表达

### 30 秒版本

我第一步实现了一个最小 Agent，它可以接收用户输入，调用大模型判断是否需要外部工具。如果需要工具，模型会输出结构化的工具名和参数，程序执行工具后再把结果交给模型生成最终回答。这个 Demo 主要验证 Agent 的基础闭环：理解意图、选择工具、执行工具、总结结果。

### 2-3 分钟版本

这个最小 Agent 分成三层：LLM 调用层、工具执行层和 Agent runner。LLM 调用层负责和模型交互，并记录耗时和错误；工具执行层维护一个工具注册表，目前支持计算器和当前时间查询；Agent runner 负责把用户输入交给模型判断是否需要工具，然后执行工具并生成最终回答。

我没有直接解析自由文本，而是要求模型输出结构化结果，并用 schema 做校验。这样可以降低工程上的不确定性。虽然第一版只是 Demo，但它已经包含了后续企业 Agent 的核心骨架，后面可以继续接入 RAG、业务系统工具、多轮状态和评测体系。

### 可能追问

- 为什么需要 structured output？
- 如果模型输出的 JSON 解析失败怎么办？
- 工具调用失败怎么办？
- 为什么不直接让模型回答？
- Agent 和 Workflow 有什么区别？
- LangGraph 在这个项目里解决什么问题？

## 本周产出检查清单

- [ ] 能调用 LLM API
- [ ] 能输出结构化结果
- [ ] 能根据用户输入判断是否需要工具
- [ ] 实现 `calculator` 工具
- [ ] 实现 `get_current_time` 工具
- [ ] 有工具注册表
- [ ] 有工具调用失败处理
- [ ] 有最小 Agent runner
- [ ] 有 5 条测试输入
- [ ] README 记录项目目标和运行方式
- [ ] 写出 30 秒和 2-3 分钟面试表达

## 本周复盘问题

- 我能否用自己的话解释 Agent 和 Chatbot 的区别？
- 我能否解释为什么需要 tool calling？
- 我能否说清楚 structured output 在工程里的价值？
- 我能否画出最小 Agent 的执行流程？
- 我能否指出当前 Demo 的限制？
- 我能否说出下一周接入 RAG 时要改哪些模块？

