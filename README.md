# Chip Datasheet QA

本项目是一个本地芯片资料问答 MVP。它支持导入 PDF / PPT / PPTX / TXT / MD 文档，按芯片型号过滤检索，并输出“先结论、后论据”的 Markdown 答案。

当前版本默认离线运行；配置 API key 后，可以启用 Embedding、Reranker、LLM Reader 和联网搜索，用于更复杂的芯片能力判断和产品需求评估。

## 安装依赖

```powershell
pip install -r requirements.txt
```

当前测试不依赖第三方库；真实 PDF/PPT 导入需要安装依赖后使用。

## 导入资料

```powershell
python -m app.cli ingest data/datasheet
```

也可以导入单个文件：

```powershell
python -m app.cli ingest data/datasheet/example.pdf
```

## 提问

```powershell
python -m app.cli ask "芯片型号：CV1800B 问题：这个芯片的工作电压范围是多少？"
```

命令行也支持回答模式：

```powershell
python -m app.cli ask "芯片型号：CV1800B 问题：这个芯片的工作电压范围是多少？" --mode simple
python -m app.cli ask "芯片型号：CV1800B 问题：这个芯片的工作电压范围是多少？" --mode full
```

## 增强 RAG 配置

默认不调用外部服务。需要启用真实 LLM Reader 时，在 PowerShell 中配置环境变量：

```powershell
$env:QA_USE_LLM_READER="1"
$env:QA_LLM_API_KEY="你的 API key"
$env:QA_LLM_BASE_URL="https://api.deepseek.com"
$env:QA_LLM_MODEL="deepseek-chat"
```

Embedding 和 Reranker 可选配置：

```powershell
$env:QA_EMBEDDING_API_KEY="你的 embedding key"
$env:QA_EMBEDDING_BASE_URL="https://your-embedding-endpoint"
$env:QA_EMBEDDING_MODEL="bge-m3"

$env:QA_RERANKER_API_KEY="你的 reranker key"
$env:QA_RERANKER_BASE_URL="https://your-reranker-endpoint"
$env:QA_RERANKER_MODEL="bge-reranker-v2-m3"
```

如果使用 SophNet 的 EasyLLM Embedding 接口，可以这样配置；`QA_EMBEDDING_API_KEY` 未单独填写时会复用 `QA_LLM_API_KEY`：

```powershell
$env:QA_EMBEDDING_PROVIDER="sophnet"
$env:QA_EMBEDDING_BASE_URL="https://www.sophnet.com/api/open-apis"
$env:QA_EMBEDDING_PROJECT_ID="你的 SophNet project_id"
$env:QA_EMBEDDING_EASYLLM_ID="你的 embedding easyllm_id"
$env:QA_EMBEDDING_MODEL="你的 embedding easyllm_id"
$env:QA_EMBEDDING_DIMENSIONS="1024"
```

配置 Embedding 后，导入资料时会把 chunk embedding 保存到 `data/index/embeddings.jsonl`。如果已有索引需要补齐或刷新 embedding，可以运行：

```powershell
python -m app.cli rebuild-embeddings
```

问答阶段只会读取 `embeddings.jsonl` 中和当前 chunk、来源文件修改时间、embedding 模型都匹配的向量，不会再为 chunk 临时生成 embedding。若 `data/datasheet` 中的文档有更新，请重新执行 `ingest`，系统会替换该文件旧 chunk 并重新生成对应 embedding。

联网搜索可选配置：

```powershell
$env:QA_ENABLE_WEB_SEARCH="1"
$env:QA_WEB_SEARCH_PROVIDER="bing"
$env:QA_WEB_SEARCH_API_KEY="你的搜索 API key"
```

支持的搜索 provider：`bing`、`tavily`、`serpapi`。如果没有配置搜索 key，系统会自动跳过联网搜索，只使用本地 datasheet。

复杂产品需求可以直接按需求清单提问，例如：

```powershell
python -m app.cli ask "芯片型号：CV1800B 问题：评估是否能做双摄门铃，要求2路200万摄像头、H.264编码、音频输入输出、低功耗和Wi-Fi连接。"
```

## 启动网页界面

```powershell
python -m app.cli serve
```

启动后打开：

```text
http://127.0.0.1:8000
```

网页界面支持：

- 输入本地文件或目录路径并导入资料
- 查看当前索引片段数和芯片型号
- 输入芯片型号和问题
- 在“简单回答”和“完整解释”之间切换
- 上传或粘贴客户项目需求明细，评估目标芯片是否满足
- 展示 Markdown 回答、原文证据和不确定性说明

## 客户需求评估

网页界面支持上传 `.docx`、`.xls`、`.xlsx`、`.csv`、`.pdf`、`.txt`、`.md` 形式的客户需求明细。系统会先解析需求文档，再基于目标芯片 datasheet 检索相关规格，输出满足或不满足的结论。

命令行也可以使用：

```powershell
python -m app.cli evaluate --chip CV1843H --requirements-file data/requirements/customer_requirements.docx
python -m app.cli evaluate --chip CV1843H --requirements-text "客户需求：2路5MP sensor，25fps，H.265编码"
```

如果可以满足，结论会使用类似“CV1843H型号的芯片可以满足客户的要求”；如果不能满足，会指出客户需求中具体哪项规格或应用不满足，并给出 datasheet 证据。

## 回答格式

回答包含：

- 结论
- 本地资料证据
- 芯片常识与推导
- 不确定性与限制
- 建议

## 当前限制

- 不做 OCR，图片和扫描版 PDF 可能无法解析。
- 不做复杂表格结构恢复，只使用可提取文本。
- 联网搜索默认关闭，需要配置搜索 API key 后启用。
- 默认回答生成器不会编造没有证据的答案。

## 验证

```powershell
python -m compileall app tests
python -m unittest discover -s tests
```

如果安装了 pytest，也可以运行：

```powershell
python -m pytest
```
