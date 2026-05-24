from __future__ import annotations  # 启用延迟类型注解，避免运行时前向引用问题

import base64  # 解码前端上传的 base64 文件内容
import csv  # 解析 CSV 需求表格
import tempfile  # 为上传文件创建临时解析路径
import xml.etree.ElementTree as ET  # 解析 docx/xlsx 内部 XML
import zipfile  # 读取 docx/xlsx 这类 zip 容器格式
from dataclasses import dataclass, field  # 定义客户需求中间格式数据结构
from pathlib import Path  # 统一处理文件路径

from app.documents.parser import DocumentParser  # 复用 PDF/TXT/MD/PPT 文档解析器
from app.text_utils import clean_text  # 清理解析文本中的非法字符


SUPPORTED_REQUIREMENT_EXTENSIONS = {".pdf", ".txt", ".md", ".docx", ".xlsx", ".xls", ".csv"}  # 定义客户需求文件支持格式


@dataclass  # 将客户需求条目声明为数据类
class RequirementItem:  # 定义统一客户需求中间格式
    item_id: str  # 保存需求条目编号
    category: str  # 保存需求分类
    name: str  # 保存需求名称
    values: list[str] = field(default_factory=list)  # 保存规格值列表
    note: str = ""  # 保存备注或解释
    raw_text: str = ""  # 保存原始解析行

    def to_dict(self) -> dict:  # 将需求条目转换为 JSON 可序列化字典
        return {"item_id": self.item_id, "category": self.category, "name": self.name, "values": self.values, "note": self.note, "raw_text": self.raw_text}  # 返回字段字典


class RequirementDocumentParser:  # 解析客户项目需求明细文档
    def parse_path(self, path: str | Path) -> str:  # 从本地路径解析需求文档
        file_path = Path(path)  # 转换为 Path 对象
        suffix = file_path.suffix.lower()  # 读取文件扩展名
        if suffix not in SUPPORTED_REQUIREMENT_EXTENSIONS:  # 检查是否为支持格式
            raise ValueError(f"Unsupported requirement file type: {file_path.suffix}")  # 抛出可读错误
        if suffix == ".docx":  # Word 文档使用 docx XML 解析
            return _parse_docx(file_path)  # 返回 docx 文本
        if suffix == ".xlsx":  # Excel 文档使用 xlsx XML 解析
            return _parse_xlsx(file_path)  # 返回 xlsx 文本
        if suffix == ".xls":  # 老版 Excel 二进制文档使用 xlrd 解析
            return _parse_xls(file_path)  # 返回 xls 文本
        if suffix == ".csv":  # CSV 表格使用 csv 标准库解析
            return _parse_csv(file_path)  # 返回 csv 文本
        pages = DocumentParser().load_pages(file_path)  # PDF/TXT/MD 复用已有解析器
        return clean_text("\n\n".join(page.text for page in pages))  # 合并所有页文本

    def parse_upload(self, file_name: str, content_base64: str) -> str:  # 从前端上传内容解析需求文档
        suffix = Path(file_name).suffix.lower()  # 读取上传文件扩展名
        if suffix not in SUPPORTED_REQUIREMENT_EXTENSIONS:  # 检查上传文件类型
            raise ValueError(f"Unsupported requirement file type: {suffix}")  # 抛出可读错误
        content = base64.b64decode(content_base64)  # 解码前端上传的 base64 文件内容
        with tempfile.TemporaryDirectory() as temp_dir:  # 使用临时目录保存上传文件
            temp_path = Path(temp_dir) / Path(file_name).name  # 构造临时文件路径
            temp_path.write_bytes(content)  # 写入上传文件字节
            return self.parse_path(temp_path)  # 按路径解析临时文件


def normalize_requirement_text(text: str) -> list[RequirementItem]:  # 将解析文本整理为统一需求中间格式
    items: list[RequirementItem] = []  # 保存规范化需求条目
    current_category = "通用需求"  # 保存当前分类
    for raw_line in text.splitlines():  # 遍历解析文本中的每一行
        line = raw_line.strip()  # 清理行首尾空白
        if not line:  # 空行直接跳过
            continue  # 继续下一行
        parts = [part.strip() for part in line.split("|") if part.strip()]  # 使用竖线拆分表格列并清理空值
        if not parts:  # 没有有效列时跳过
            continue  # 继续下一行
        if len(parts) == 1 and not _looks_like_requirement_value(parts[0]):  # 单列标题行视为分类
            current_category = parts[0]  # 更新当前分类
            continue  # 标题行不作为需求条目
        name = parts[0]  # 第一列作为需求名称
        values = parts[1:]  # 后续列作为规格值和备注
        if len(parts) == 1 and _looks_like_requirement_value(parts[0]):  # 单列但像具体规格时保留为需求条目
            name = parts[0]  # 将整行作为需求名称
            values = []  # 没有额外规格值
        note = _extract_note(values)  # 从规格值中提取备注说明
        item = RequirementItem(  # 构造统一需求条目
            item_id=f"REQ-{len(items) + 1:03d}",  # 生成稳定编号
            category=current_category,  # 保存当前分类
            name=name,  # 保存需求名称
            values=values,  # 保存规格值
            note=note,  # 保存备注
            raw_text=line,  # 保存原始行
        )  # 结束需求条目构造
        items.append(item)  # 追加需求条目
    return items  # 返回统一需求条目列表


def format_requirement_items_markdown(items: list[RequirementItem]) -> str:  # 将统一需求中间格式渲染为 Markdown 表格
    if not items:  # 没有需求条目时返回占位文本
        return "未解析出可评估的客户需求条目。"  # 返回无条目说明
    lines = ["| ID | 分类 | 需求项 | 规格值 | 备注 |", "|---|---|---|---|---|"]  # 初始化 Markdown 表头
    for item in items:  # 遍历需求条目
        values = "<br>".join(item.values) if item.values else "-"  # 将多个规格值合并为单元格
        note = item.note or "-"  # 没有备注时使用占位符
        lines.append(f"| {item.item_id} | {_escape_table(item.category)} | {_escape_table(item.name)} | {_escape_table(values)} | {_escape_table(note)} |")  # 追加 Markdown 表格行
    return "\n".join(lines)  # 返回 Markdown 表格文本


def _looks_like_requirement_value(text: str) -> bool:  # 判断单列文本是否像具体需求而不是标题
    keywords = ["支持", "接口", "以太网", "wifi", "bluetooth", "nfc", "usb", "uart", "iic", "spi", "gpio", "mipi", "dvp", "mb", "gb", "fps"]  # 定义规格关键词
    text_lower = text.lower()  # 转为小写匹配英文关键词
    return any(keyword in text_lower or keyword in text for keyword in keywords) or any(char.isdigit() for char in text)  # 命中关键词或数字则视为具体需求


def _extract_note(values: list[str]) -> str:  # 从规格值中提取备注
    if not values:  # 没有规格值时返回空
        return ""  # 返回空备注
    note_candidates = [value for value in values if any(keyword in value for keyword in ["备注", "功能", "要求", "接口", "实现", "模组"])]  # 选择更像备注的值
    return "；".join(note_candidates)  # 合并备注候选


def _escape_table(value: str) -> str:  # 转义 Markdown 表格中的特殊字符
    return value.replace("|", "\\|").replace("\n", "<br>")  # 转义竖线并替换换行


def _parse_docx(path: Path) -> str:  # 从 docx 文件中提取段落和表格文本
    with zipfile.ZipFile(path) as archive:  # 打开 docx zip 容器
        xml_bytes = archive.read("word/document.xml")  # 读取主文档 XML
    root = ET.fromstring(xml_bytes)  # 解析 XML 根节点
    namespace = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}  # 定义 WordprocessingML 命名空间
    paragraphs: list[str] = []  # 保存段落文本
    for paragraph in root.findall(".//w:p", namespace):  # 遍历 Word 段落
        text = "".join(node.text or "" for node in paragraph.findall(".//w:t", namespace)).strip()  # 合并段落文本节点
        if text:  # 非空段落才保留
            paragraphs.append(text)  # 保存段落文本
    return clean_text("\n".join(paragraphs))  # 返回清理后的 docx 文本


def _parse_xlsx(path: Path) -> str:  # 从 xlsx 文件中提取所有工作表文本
    with zipfile.ZipFile(path) as archive:  # 打开 xlsx zip 容器
        shared_strings = _load_shared_strings(archive)  # 读取共享字符串表
        sheet_names = sorted(name for name in archive.namelist() if name.startswith("xl/worksheets/sheet") and name.endswith(".xml"))  # 找出工作表 XML
        rows: list[str] = []  # 保存所有工作表行文本
        for sheet_name in sheet_names:  # 遍历每个工作表
            rows.extend(_parse_xlsx_sheet(archive, sheet_name, shared_strings))  # 解析并追加工作表行
    return clean_text("\n".join(rows))  # 返回清理后的 xlsx 文本


def _load_shared_strings(archive: zipfile.ZipFile) -> list[str]:  # 读取 xlsx 共享字符串表
    if "xl/sharedStrings.xml" not in archive.namelist():  # 没有共享字符串时返回空列表
        return []  # 返回空共享字符串表
    root = ET.fromstring(archive.read("xl/sharedStrings.xml"))  # 解析共享字符串 XML
    namespace = {"s": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}  # 定义 SpreadsheetML 命名空间
    values: list[str] = []  # 保存共享字符串
    for item in root.findall(".//s:si", namespace):  # 遍历共享字符串项
        text = "".join(node.text or "" for node in item.findall(".//s:t", namespace))  # 合并富文本节点
        values.append(text)  # 保存共享字符串
    return values  # 返回共享字符串表


def _parse_xlsx_sheet(archive: zipfile.ZipFile, sheet_name: str, shared_strings: list[str]) -> list[str]:  # 解析单个 xlsx 工作表
    root = ET.fromstring(archive.read(sheet_name))  # 解析工作表 XML
    namespace = {"s": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}  # 定义 SpreadsheetML 命名空间
    rows: list[str] = []  # 保存工作表行文本
    for row in root.findall(".//s:row", namespace):  # 遍历工作表行
        cells = [_read_xlsx_cell(cell, shared_strings, namespace) for cell in row.findall("s:c", namespace)]  # 读取行内单元格
        values = [value for value in cells if value]  # 去掉空单元格
        if values:  # 非空行才保留
            rows.append(" | ".join(values))  # 用竖线保留表格列边界
    return rows  # 返回工作表行文本


def _read_xlsx_cell(cell: ET.Element, shared_strings: list[str], namespace: dict[str, str]) -> str:  # 读取 xlsx 单元格文本
    value_node = cell.find("s:v", namespace)  # 读取普通单元格值节点
    inline_node = cell.find(".//s:t", namespace)  # 读取 inlineStr 文本节点
    if inline_node is not None and inline_node.text:  # inlineStr 单元格直接返回文本
        return inline_node.text.strip()  # 返回 inlineStr 文本
    if value_node is None or value_node.text is None:  # 没有值节点时返回空
        return ""  # 返回空字符串
    raw_value = value_node.text.strip()  # 读取原始单元格值
    if cell.attrib.get("t") == "s":  # 共享字符串单元格需要按索引查表
        index = int(raw_value)  # 将共享字符串索引转为整数
        return shared_strings[index] if 0 <= index < len(shared_strings) else ""  # 返回共享字符串
    return raw_value  # 数字或普通字符串直接返回


def _parse_csv(path: Path) -> str:  # 解析 CSV 需求表格
    rows: list[str] = []  # 保存 CSV 行文本
    with path.open("r", encoding="utf-8-sig", newline="") as file:  # 用 utf-8-sig 兼容 BOM
        for row in csv.reader(file):  # 遍历 CSV 行
            values = [cell.strip() for cell in row if cell.strip()]  # 清理空单元格
            if values:  # 非空行才保留
                rows.append(" | ".join(values))  # 用竖线保留列边界
    return clean_text("\n".join(rows))  # 返回清理后的 CSV 文本


def _parse_xls(path: Path) -> str:  # 解析老版 Excel xls 需求表格
    try:  # xlrd 是解析二进制 xls 的可选依赖
        import xlrd  # type: ignore  # 导入 xlrd 读取 .xls 工作簿
    except ImportError as exc:  # 缺少依赖时给出明确安装提示
        raise RuntimeError("xlrd is required to load .xls requirement files. Run: pip install -r requirements.txt") from exc  # 抛出可读错误
    workbook = xlrd.open_workbook(str(path))  # 打开 xls 工作簿
    rows: list[str] = []  # 保存所有工作表行文本
    for sheet in workbook.sheets():  # 遍历每个工作表
        for row_index in range(sheet.nrows):  # 遍历工作表行
            values = [_format_xls_cell(sheet.cell_value(row_index, col_index)) for col_index in range(sheet.ncols)]  # 读取并格式化行内单元格
            non_empty_values = [value for value in values if value]  # 去掉空单元格
            if non_empty_values:  # 非空行才保留
                rows.append(" | ".join(non_empty_values))  # 用竖线保留列边界
    return clean_text("\n".join(rows))  # 返回清理后的 xls 文本


def _format_xls_cell(value) -> str:  # 将 xls 单元格值格式化为文本
    if value is None:  # 空值返回空字符串
        return ""  # 返回空字符串
    if isinstance(value, float) and value.is_integer():  # 整数形式的浮点数去掉 .0
        return str(int(value))  # 返回整数文本
    return str(value).strip()  # 返回清理后的普通文本
