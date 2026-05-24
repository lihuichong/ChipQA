from __future__ import annotations  # 启用延迟类型注解，避免运行时前向引用问题

import json  # 编解码 JSON 请求和响应
from urllib.error import HTTPError, URLError  # 捕获 HTTP 请求异常
from urllib.request import Request, urlopen  # 使用标准库发送 HTTP 请求


def post_json(url: str, headers: dict[str, str], payload: dict, timeout_seconds: int) -> dict:  # 发送 JSON POST 请求并返回字典响应
    data = json.dumps(payload, ensure_ascii=False).encode("utf-8")  # 将请求体序列化为 UTF-8 JSON 字节
    request = Request(url, data=data, headers=headers, method="POST")  # 构造 POST 请求对象
    try:  # 捕获网络错误并转换为可读异常
        with urlopen(request, timeout=timeout_seconds) as response:  # 发起请求并自动关闭响应对象
            return json.loads(response.read().decode("utf-8"))  # 解析并返回 JSON 响应
    except HTTPError as exc:  # 处理 HTTP 状态码错误
        error_body = exc.read().decode("utf-8", errors="replace")  # 读取错误响应体用于排查配置问题
        raise RuntimeError(f"HTTP {exc.code} from {url}: {error_body}") from exc  # 抛出包含服务端信息的异常
    except URLError as exc:  # 处理 DNS、代理、网络不可达等错误
        raise RuntimeError(f"Network error calling {url}: {exc.reason}") from exc  # 抛出包含底层原因的异常


def get_json(url: str, headers: dict[str, str], timeout_seconds: int) -> dict:  # 发送 JSON GET 请求并返回字典响应
    request = Request(url, headers=headers, method="GET")  # 构造 GET 请求对象
    try:  # 捕获网络错误并转换为可读异常
        with urlopen(request, timeout=timeout_seconds) as response:  # 发起请求并自动关闭响应对象
            return json.loads(response.read().decode("utf-8"))  # 解析并返回 JSON 响应
    except HTTPError as exc:  # 处理 HTTP 状态码错误
        error_body = exc.read().decode("utf-8", errors="replace")  # 读取错误响应体用于排查配置问题
        raise RuntimeError(f"HTTP {exc.code} from {url}: {error_body}") from exc  # 抛出包含服务端信息的异常
    except URLError as exc:  # 处理 DNS、代理、网络不可达等错误
        raise RuntimeError(f"Network error calling {url}: {exc.reason}") from exc  # 抛出包含底层原因的异常
