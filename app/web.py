from __future__ import annotations  # 启用延迟类型注解，避免运行时前向引用问题

import json  # 导入 JSON 序列化和反序列化工具
from http import HTTPStatus  # 导入标准库 HTTP 服务组件
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer  # 导入标准库 HTTP 服务组件
from pathlib import Path  # 导入 Path 以统一处理文件路径
from urllib.parse import urlparse  # 导入 URL 解析或请求工具

from app.pipeline import IngestPipeline, QaPipeline  # 导入资料导入流程和问答流程
from app.requirements_parser import RequirementDocumentParser, format_requirement_items_markdown, normalize_requirement_text  # 导入客户需求解析和中间格式工具
from app.storage import JsonIndexStore  # 导入 JSONL 本地索引存储实现


DEFAULT_HOST = "127.0.0.1"  # 计算并保存 DEFAULT_HOST
DEFAULT_PORT = 8000  # 计算并保存 DEFAULT_PORT


def run_server(host: str = DEFAULT_HOST, port: int = DEFAULT_PORT) -> None:  # 定义 run_server 函数或方法
    server = ThreadingHTTPServer((host, port), DatasheetQaHandler)  # 计算并保存 server
    print(f"Serving Chip Datasheet QA at http://{host}:{port}")  # 将结果或服务地址输出到控制台
    server.serve_forever()  # 执行当前业务逻辑


class DatasheetQaHandler(BaseHTTPRequestHandler):  # 定义 DatasheetQaHandler 类
    server_version = "ChipDatasheetQA/0.1"  # 计算并保存 server_version

    def do_GET(self) -> None:  # 定义 do_GET 函数或方法
        parsed = urlparse(self.path)  # 计算并保存 parsed
        if parsed.path == "/":  # 检查条件：parsed.path == "/"
            self._send_text(INDEX_HTML, content_type="text/html; charset=utf-8")  # 初始化或更新对象属性 self._send_text(INDEX_HTML, content_type
            return  # 执行当前业务逻辑
        if parsed.path == "/assets/app.css":  # 检查条件：parsed.path == "/assets/app.css"
            self._send_text(APP_CSS, content_type="text/css; charset=utf-8")  # 初始化或更新对象属性 self._send_text(APP_CSS, content_type
            return  # 执行当前业务逻辑
        if parsed.path == "/assets/app.js":  # 检查条件：parsed.path == "/assets/app.js"
            self._send_text(APP_JS, content_type="application/javascript; charset=utf-8")  # 初始化或更新对象属性 self._send_text(APP_JS, content_type
            return  # 执行当前业务逻辑
        if parsed.path == "/api/status":  # 检查条件：parsed.path == "/api/status"
            chunks = JsonIndexStore().load_chunks()  # 保存当前流程中的 chunks 数据
            models = sorted({chunk.chip_model for chunk in chunks if chunk.chip_model})  # 保存当前流程中的 models 数据
            self._send_json({"chunks": len(chunks), "chip_models": models})  # 执行当前业务逻辑
            return  # 执行当前业务逻辑
        self._send_json({"error": "Not found"}, status=HTTPStatus.NOT_FOUND)  # 初始化或更新对象属性 self._send_json({"error"

    def do_POST(self) -> None:  # 定义 do_POST 函数或方法
        parsed = urlparse(self.path)  # 计算并保存 parsed
        try:  # 尝试执行可能失败的操作
            payload = self._read_json()  # 计算并保存 payload
            if parsed.path == "/api/ingest":  # 检查条件：parsed.path == "/api/ingest"
                source_path = str(payload.get("path", "")).strip()  # 计算并保存 source_path
                if not source_path:  # 检查条件：not source_path
                    self._send_json({"error": "path is required"}, status=HTTPStatus.BAD_REQUEST)  # 初始化或更新对象属性 self._send_json({"error"
                    return  # 执行当前业务逻辑
                if not Path(source_path).exists():  # 检查条件：not Path(source_path).exists()
                    self._send_json({"error": f"path does not exist: {source_path}"}, status=HTTPStatus.BAD_REQUEST)  # 初始化或更新对象属性 self._send_json({"error"
                    return  # 执行当前业务逻辑
                self._send_json(IngestPipeline().ingest(source_path))  # 执行当前业务逻辑
                return  # 执行当前业务逻辑
            if parsed.path == "/api/ask":  # 检查条件：parsed.path == "/api/ask"
                question = str(payload.get("question", "")).strip()  # 保存去除型号后的问题正文
                top_k = int(payload.get("top_k", 5))  # 计算并保存 top_k
                answer_mode = _normalize_answer_mode(str(payload.get("answer_mode", "full")))  # 读取并规范化回答模式
                if not question:  # 检查条件：not question
                    self._send_json({"error": "question is required"}, status=HTTPStatus.BAD_REQUEST)  # 初始化或更新对象属性 self._send_json({"error"
                    return  # 执行当前业务逻辑
                answer = QaPipeline().ask(question, top_k=top_k, answer_mode=answer_mode)  # 保存 answer 的处理结果
                self._send_json({"answer_markdown": answer.to_markdown(mode=answer_mode)})  # 执行当前业务逻辑
                return  # 执行当前业务逻辑
            if parsed.path == "/api/evaluate-requirements":  # 检查条件：parsed.path == "/api/evaluate-requirements"
                chip_model = str(payload.get("chip_model", "")).strip()  # 读取目标芯片型号
                requirement_text = str(payload.get("requirement_text", "")).strip()  # 读取粘贴的需求文本
                requirement_path = str(payload.get("requirement_path", "")).strip()  # 读取本地需求文件路径
                file_name = str(payload.get("file_name", "")).strip()  # 读取上传文件名
                file_content = str(payload.get("file_content_base64", "")).strip()  # 读取上传文件 base64 内容
                top_k = int(payload.get("top_k", 8))  # 读取需求评估证据数量
                answer_mode = _normalize_answer_mode(str(payload.get("answer_mode", "full")))  # 读取回答模式
                if not chip_model:  # 芯片型号为空时拒绝请求
                    self._send_json({"error": "chip_model is required"}, status=HTTPStatus.BAD_REQUEST)  # 返回缺少芯片型号错误
                    return  # 结束当前请求
                parser = RequirementDocumentParser()  # 构建客户需求文档解析器
                if file_name and file_content:  # 优先处理浏览器上传文件
                    parsed_requirement_text = parser.parse_upload(file_name, file_content)  # 解析上传文件为文本
                elif requirement_path:  # 其次处理本地文件路径
                    if not Path(requirement_path).exists():  # 检查本地路径是否存在
                        self._send_json({"error": f"path does not exist: {requirement_path}"}, status=HTTPStatus.BAD_REQUEST)  # 返回路径不存在错误
                        return  # 结束当前请求
                    parsed_requirement_text = parser.parse_path(requirement_path)  # 解析本地需求文件为文本
                elif requirement_text:  # 最后处理粘贴文本
                    parsed_requirement_text = requirement_text  # 直接使用粘贴文本作为需求内容
                else:  # 没有任何需求内容时拒绝请求
                    self._send_json({"error": "requirement text, path, or file is required"}, status=HTTPStatus.BAD_REQUEST)  # 返回缺少需求内容错误
                    return  # 结束当前请求
                requirement_items = normalize_requirement_text(parsed_requirement_text)  # 将需求文本整理为统一中间格式
                parsed_markdown = format_requirement_items_markdown(requirement_items)  # 将中间格式渲染成 Markdown 表格
                normalized_text = parsed_markdown + "\n\n原始解析文本：\n" + parsed_requirement_text  # 将中间格式和原文一并交给评估流程
                answer = QaPipeline().evaluate_requirements(chip_model, normalized_text, top_k=top_k, answer_mode=answer_mode)  # 基于中间格式评估客户需求
                self._send_json({"answer_markdown": answer.to_markdown(mode=answer_mode), "parsed_requirements_markdown": parsed_markdown, "parsed_requirements": [item.to_dict() for item in requirement_items]})  # 返回 Markdown 评估结果和中间格式
                return  # 结束当前请求
        except Exception as exc:  # 捕获并处理异常分支
            self._send_json({"error": str(exc)}, status=HTTPStatus.INTERNAL_SERVER_ERROR)  # 初始化或更新对象属性 self._send_json({"error"
            return  # 执行当前业务逻辑
        self._send_json({"error": "Not found"}, status=HTTPStatus.NOT_FOUND)  # 初始化或更新对象属性 self._send_json({"error"

    def log_message(self, format: str, *args: object) -> None:  # 定义 log_message 函数或方法
        print(f"{self.address_string()} - {format % args}")  # 将结果或服务地址输出到控制台

    def _read_json(self) -> dict:  # 定义 _read_json 函数或方法
        length = int(self.headers.get("Content-Length", "0"))  # 计算并保存 length
        if length == 0:  # 检查条件：length == 0
            return {}  # 返回 {}
        return json.loads(self.rfile.read(length).decode("utf-8"))  # 返回 json.loads(self.rfile.read(length).decod

    def _send_json(self, payload: dict, status: HTTPStatus = HTTPStatus.OK) -> None:  # 定义 _send_json 函数或方法
        data = json.dumps(payload, ensure_ascii=False).encode("utf-8")  # 计算并保存 data
        self.send_response(status)  # 执行当前业务逻辑
        self.send_header("Content-Type", "application/json; charset=utf-8")  # 初始化或更新对象属性 self.send_header("Content-Type", "application/json; charset
        self.send_header("Content-Length", str(len(data)))  # 执行当前业务逻辑
        self.end_headers()  # 执行当前业务逻辑
        self.wfile.write(data)  # 将序列化后的数据写入文件

    def _send_text(self, text: str, content_type: str, status: HTTPStatus = HTTPStatus.OK) -> None:  # 定义 _send_text 函数或方法
        data = text.encode("utf-8")  # 计算并保存 data
        self.send_response(status)  # 执行当前业务逻辑
        self.send_header("Content-Type", content_type)  # 执行当前业务逻辑
        self.send_header("Content-Length", str(len(data)))  # 执行当前业务逻辑
        self.end_headers()  # 执行当前业务逻辑
        self.wfile.write(data)  # 将序列化后的数据写入文件


def _normalize_answer_mode(value: str) -> str:  # 将前端传来的回答模式规范化
    return "simple" if value == "simple" else "full"  # 只允许 simple，其余都回退完整解释


INDEX_HTML = """<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Chip Datasheet QA</title>
  <link rel="stylesheet" href="/assets/app.css">
</head>
<body>
  <main class="shell">
    <section class="workspace">
      <div class="topbar">
        <div>
          <h1>Chip Datasheet QA</h1>
          <p>本地芯片资料问答。先导入 datasheet，再按芯片型号提问。</p>
        </div>
        <div class="status" id="status">索引加载中...</div>
      </div>

      <div class="grid">
        <section class="panel">
          <div class="panel-heading">
            <h2>资料导入</h2>
            <span>PDF / PPT / TXT / MD</span>
          </div>
          <label for="pathInput">本地文件或目录路径</label>
          <div class="row">
            <input id="pathInput" type="text" value="data/datasheet" spellcheck="false">
            <button id="ingestButton" type="button">导入</button>
          </div>
          <pre id="ingestResult" class="result-box">等待导入资料。</pre>
        </section>

        <section class="panel">
          <div class="panel-heading">
            <h2>芯片问答</h2>
            <span>先结论，后证据</span>
          </div>
          <label for="questionInput">问题</label>
          <textarea id="questionInput" rows="7" spellcheck="false">芯片型号：CV1800B 问题：工作电压范围是多少？</textarea>
          <div class="actions">
            <div class="mode-toggle" role="group" aria-label="回答模式">
              <label>
                <input type="radio" name="answerMode" value="simple" checked>
                <span>简单回答</span>
              </label>
              <label>
                <input type="radio" name="answerMode" value="full">
                <span>完整解释</span>
              </label>
            </div>
            <label class="topk-label" for="topKInput">证据数</label>
            <input id="topKInput" type="number" min="1" max="10" value="5">
            <button id="askButton" type="button">提问</button>
          </div>
        </section>
      </div>

      <section class="answer-area">
        <div class="panel-heading">
          <h2>芯片问答结果</h2>
          <span id="qaAnswerState">等待问题。</span>
        </div>
        <article id="qaAnswerOutput" class="answer-output"></article>
      </section>

      <section class="panel requirement-panel">
        <div class="panel-heading">
          <h2>客户需求评估</h2>
          <span>DOCX / XLS / XLSX / CSV / PDF / TXT / MD</span>
        </div>
        <div class="requirement-grid">
          <div>
            <label for="requirementChipInput">目标芯片型号</label>
            <input id="requirementChipInput" type="text" value="CV1843H" spellcheck="false">
          </div>
          <div>
            <label for="requirementFileInput">上传客户需求文件</label>
            <input id="requirementFileInput" type="file" accept=".docx,.xls,.xlsx,.csv,.pdf,.txt,.md">
          </div>
        </div>
        <label for="requirementPathInput">或填写本地需求文件路径</label>
        <input id="requirementPathInput" type="text" placeholder="例如 data/requirements/customer_requirements.docx" spellcheck="false">
        <label for="requirementTextInput">或直接粘贴客户需求明细</label>
        <textarea id="requirementTextInput" rows="6" spellcheck="false" placeholder="例如：2路5MP sensor@25fps；H.265编码；支持音频输入输出；支持以太网..."></textarea>
        <div class="actions">
          <button id="evaluateButton" type="button">评估需求</button>
        </div>
        <label for="requirementParsedOutput">需求解析中间格式</label>
        <pre id="requirementParsedOutput" class="result-box">等待解析客户需求。</pre>
      </section>

      <section class="answer-area">
        <div class="panel-heading">
          <h2>客户需求评估结果</h2>
          <span id="requirementAnswerState">等待客户需求。</span>
        </div>
        <article id="requirementAnswerOutput" class="answer-output"></article>
      </section>
    </section>
  </main>
  <script src="/assets/app.js"></script>
</body>
</html>
"""


APP_CSS = """
:root {
  color-scheme: light;
  font-family: "Segoe UI", "Microsoft YaHei", Arial, sans-serif;
  background: #f5f7f8;
  color: #172026;
}

* { box-sizing: border-box; }
body { margin: 0; min-height: 100vh; background: #f5f7f8; }
button, input, textarea { font: inherit; }

.shell {
  width: min(1180px, calc(100vw - 32px));
  margin: 0 auto;
  padding: 28px 0 40px;
}

.workspace { display: grid; gap: 18px; }

.topbar {
  display: flex;
  align-items: flex-end;
  justify-content: space-between;
  gap: 16px;
  padding-bottom: 10px;
  border-bottom: 1px solid #d6dde2;
}

h1, h2, p { margin: 0; }
h1 { font-size: 28px; line-height: 1.15; color: #0f1720; }
h2 { font-size: 17px; line-height: 1.25; }
p { margin-top: 6px; color: #5e6b75; font-size: 14px; }

.status {
  min-width: 210px;
  padding: 9px 12px;
  border: 1px solid #cbd6dc;
  border-radius: 8px;
  background: #ffffff;
  color: #31414c;
  font-size: 13px;
  text-align: right;
}

.grid {
  display: grid;
  grid-template-columns: minmax(300px, 0.9fr) minmax(360px, 1.1fr);
  gap: 18px;
}

.requirement-grid {
  display: grid;
  grid-template-columns: minmax(180px, 0.45fr) minmax(260px, 0.55fr);
  gap: 14px;
  margin-bottom: 12px;
}

.panel, .answer-area {
  border: 1px solid #d6dde2;
  border-radius: 8px;
  background: #ffffff;
  padding: 16px;
}

.panel-heading {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 14px;
}

.panel-heading span { color: #667782; font-size: 13px; }

label {
  display: block;
  margin-bottom: 8px;
  color: #31414c;
  font-size: 13px;
  font-weight: 600;
}

.row, .actions { display: flex; align-items: center; gap: 10px; }
input, textarea {
  width: 100%;
  border: 1px solid #c8d2d9;
  border-radius: 7px;
  background: #fbfcfd;
  color: #172026;
  outline: none;
}

input { height: 40px; padding: 0 11px; }
input[type="file"] { padding: 8px 11px; }
textarea { resize: vertical; min-height: 150px; padding: 11px; line-height: 1.55; }

input:focus, textarea:focus {
  border-color: #2f6f9f;
  box-shadow: 0 0 0 3px rgba(47, 111, 159, 0.14);
}

button {
  height: 40px;
  min-width: 86px;
  border: 1px solid #255d86;
  border-radius: 7px;
  background: #2f6f9f;
  color: white;
  cursor: pointer;
}

button:disabled { border-color: #9caab3; background: #9caab3; cursor: wait; }

.result-box {
  min-height: 94px;
  margin: 14px 0 0;
  padding: 12px;
  overflow: auto;
  border: 1px solid #e1e7eb;
  border-radius: 7px;
  background: #f8fafb;
  color: #31414c;
  font-size: 12px;
  line-height: 1.5;
}

.actions { justify-content: flex-end; margin-top: 12px; }
.topk-label { margin: 0; white-space: nowrap; }
#topKInput { width: 72px; }

.mode-toggle {
  display: inline-flex;
  overflow: hidden;
  border: 1px solid #c8d2d9;
  border-radius: 7px;
  background: #fbfcfd;
}

.mode-toggle label {
  display: flex;
  align-items: center;
  min-height: 38px;
  margin: 0;
  cursor: pointer;
}

.mode-toggle input { position: absolute; opacity: 0; pointer-events: none; }

.mode-toggle span {
  display: flex;
  align-items: center;
  height: 38px;
  padding: 0 12px;
  color: #31414c;
  font-size: 13px;
  font-weight: 600;
}

.mode-toggle label + label { border-left: 1px solid #c8d2d9; }
.mode-toggle input:checked + span { background: #2f6f9f; color: #ffffff; }

.answer-output {
  min-height: 260px;
  padding: 4px 2px;
  color: #172026;
  line-height: 1.72;
}

.answer-output h2 {
  margin: 18px 0 8px;
  padding-top: 8px;
  border-top: 1px solid #edf1f3;
  font-size: 18px;
}

.answer-output h2:first-child { margin-top: 0; border-top: 0; }
.answer-output h3 { margin: 14px 0 6px; font-size: 15px; }
.answer-output p, .answer-output li { font-size: 14px; }
.answer-output ul, .answer-output ol { padding-left: 22px; }
.answer-output code { padding: 2px 5px; border-radius: 5px; background: #eef3f6; }
.error { color: #a73535; }

@media (max-width: 800px) {
  .topbar, .grid, .requirement-grid { grid-template-columns: 1fr; display: grid; }
  .status { width: 100%; text-align: left; }
  .row, .actions { align-items: stretch; flex-direction: column; }
  button, #topKInput { width: 100%; }
}
"""


APP_JS = """
const statusEl = document.querySelector("#status");
const pathInput = document.querySelector("#pathInput");
const ingestButton = document.querySelector("#ingestButton");
const ingestResult = document.querySelector("#ingestResult");
const questionInput = document.querySelector("#questionInput");
const topKInput = document.querySelector("#topKInput");
const answerModeInputs = document.querySelectorAll("input[name='answerMode']");
const askButton = document.querySelector("#askButton");
const requirementChipInput = document.querySelector("#requirementChipInput");
const requirementFileInput = document.querySelector("#requirementFileInput");
const requirementPathInput = document.querySelector("#requirementPathInput");
const requirementTextInput = document.querySelector("#requirementTextInput");
const evaluateButton = document.querySelector("#evaluateButton");
const requirementParsedOutput = document.querySelector("#requirementParsedOutput");
const qaAnswerOutput = document.querySelector("#qaAnswerOutput");
const qaAnswerState = document.querySelector("#qaAnswerState");
const requirementAnswerOutput = document.querySelector("#requirementAnswerOutput");
const requirementAnswerState = document.querySelector("#requirementAnswerState");

async function api(path, payload) {
  const response = await fetch(path, {
    method: "POST",
    headers: {"Content-Type": "application/json"},
    body: JSON.stringify(payload),
  });
  const data = await response.json();
  if (!response.ok) {
    throw new Error(data.error || "请求失败");
  }
  return data;
}

async function refreshStatus() {
  try {
    const response = await fetch("/api/status");
    const data = await response.json();
    const models = data.chip_models.slice(0, 5).join(", ");
    statusEl.textContent = `${data.chunks} 个片段 · ${data.chip_models.length} 个型号${models ? " · " + models : ""}`;
  } catch (error) {
    statusEl.textContent = "索引状态不可用";
  }
}

function markdownToHtml(markdown) {
  const escaped = markdown
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;");
  const lines = escaped.split("\\n");
  const html = [];
  let inList = false;
  for (const line of lines) {
    if (line.startsWith("### ")) {
      if (inList) { html.push("</ul>"); inList = false; }
      html.push(`<h3>${line.slice(4)}</h3>`);
    } else if (line.startsWith("## ")) {
      if (inList) { html.push("</ul>"); inList = false; }
      html.push(`<h2>${line.slice(3)}</h2>`);
    } else if (line.startsWith("- ")) {
      if (!inList) { html.push("<ul>"); inList = true; }
      html.push(`<li>${line.slice(2)}</li>`);
    } else if (line.trim()) {
      if (inList) { html.push("</ul>"); inList = false; }
      html.push(`<p>${line}</p>`);
    }
  }
  if (inList) { html.push("</ul>"); }
  return html.join("");
}

function fileToBase64(file) {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => resolve(String(reader.result).split(",")[1] || "");
    reader.onerror = () => reject(reader.error || new Error("文件读取失败"));
    reader.readAsDataURL(file);
  });
}

function selectedAnswerMode() {
  const selected = Array.from(answerModeInputs).find((input) => input.checked);
  return selected ? selected.value : "full";
}

ingestButton.addEventListener("click", async () => {
  ingestButton.disabled = true;
  ingestResult.textContent = "正在导入...";
  try {
    const result = await api("/api/ingest", {path: pathInput.value});
    ingestResult.textContent = JSON.stringify(result, null, 2);
    await refreshStatus();
  } catch (error) {
    ingestResult.textContent = error.message;
  } finally {
    ingestButton.disabled = false;
  }
});

askButton.addEventListener("click", async () => {
  askButton.disabled = true;
  const answerMode = selectedAnswerMode();
  qaAnswerState.textContent = answerMode === "simple" ? "正在生成简单回答..." : "正在生成完整解释...";
  qaAnswerOutput.innerHTML = "";
  try {
    const result = await api("/api/ask", {
      question: questionInput.value,
      top_k: Number(topKInput.value || 5),
      answer_mode: answerMode,
    });
    qaAnswerOutput.innerHTML = markdownToHtml(result.answer_markdown);
    qaAnswerState.textContent = "已生成回答。";
  } catch (error) {
    qaAnswerOutput.innerHTML = `<p class="error">${error.message}</p>`;
    qaAnswerState.textContent = "请求失败。";
  } finally {
    askButton.disabled = false;
  }
});

evaluateButton.addEventListener("click", async () => {
  evaluateButton.disabled = true;
  const answerMode = selectedAnswerMode();
  requirementAnswerState.textContent = "正在解析客户需求并评估...";
  requirementAnswerOutput.innerHTML = "";
  requirementParsedOutput.textContent = "正在解析客户需求...";
  try {
    const file = requirementFileInput.files[0];
    const hasRequirementInput = Boolean(file || requirementPathInput.value.trim() || requirementTextInput.value.trim());
    if (!hasRequirementInput) {
      throw new Error("请上传客户需求文件、填写本地需求文件路径，或粘贴客户需求明细。");
    }
    const payload = {
      chip_model: requirementChipInput.value,
      requirement_text: requirementTextInput.value,
      requirement_path: requirementPathInput.value,
      top_k: Number(topKInput.value || 8),
      answer_mode: answerMode,
    };
    if (file) {
      payload.file_name = file.name;
      payload.file_content_base64 = await fileToBase64(file);
    }
    const result = await api("/api/evaluate-requirements", payload);
    requirementParsedOutput.textContent = result.parsed_requirements_markdown || "未返回需求中间格式。";
    requirementAnswerOutput.innerHTML = markdownToHtml(result.answer_markdown);
    requirementAnswerState.textContent = "已生成客户需求评估。";
  } catch (error) {
    requirementParsedOutput.textContent = "解析失败。";
    requirementAnswerOutput.innerHTML = `<p class="error">${error.message}</p>`;
    requirementAnswerState.textContent = "评估失败。";
  } finally {
    evaluateButton.disabled = false;
  }
});

refreshStatus();
"""
