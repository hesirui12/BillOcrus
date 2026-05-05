import re
from typing import Optional


def _average_height(blocks: list[dict]) -> float:
    heights = []
    for b in blocks:
        box = b["bbox"]
        h = abs(box[3][1] - box[0][1]) + abs(box[2][1] - box[1][1])
        heights.append(h / 2)
    return sum(heights) / len(heights) if heights else 0


def _sort_blocks(blocks: list[dict]) -> list[dict]:
    line_height = _average_height(blocks) if blocks else 20
    groups = []
    used = set()
    for i, b in enumerate(blocks):
        if i in used:
            continue
        cy = (b["bbox"][0][1] + b["bbox"][2][1]) / 2
        line = [i]
        used.add(i)
        for j, c in enumerate(blocks):
            if j in used:
                continue
            cy2 = (c["bbox"][0][1] + c["bbox"][2][1]) / 2
            if abs(cy - cy2) < line_height * 0.6:
                line.append(j)
                used.add(j)
        line_blocks = [blocks[idx] for idx in line]
        line_blocks.sort(key=lambda x: x["bbox"][0][0])
        groups.append(line_blocks)
    groups.sort(key=lambda g: (g[0]["bbox"][0][1] + g[0]["bbox"][2][1]) / 2)
    return [b for g in groups for b in g]


def _line_text(blocks: list[dict]) -> str:
    return " ".join(b["text"] for b in blocks)


def _group_to_lines(blocks: list[dict]) -> list[str]:
    line_height = _average_height(blocks) if blocks else 20
    groups = []
    used = set()
    for i, b in enumerate(blocks):
        if i in used:
            continue
        cy = (b["bbox"][0][1] + b["bbox"][2][1]) / 2
        line = [(i, b)]
        used.add(i)
        for j, c in enumerate(blocks):
            if j in used:
                continue
            cy2 = (c["bbox"][0][1] + c["bbox"][2][1]) / 2
            if abs(cy - cy2) < line_height * 0.6:
                line.append((j, c))
                used.add(j)
        line.sort(key=lambda x: x[1]["bbox"][0][0])
        groups.append(" ".join(item[1]["text"] for item in line))
    return groups


def extract_vat_invoice(blocks: list[dict]) -> dict:
    sorted_blocks = _sort_blocks(blocks)
    full_text = " ".join(b["text"] for b in sorted_blocks)
    lines = _group_to_lines(blocks)

    fields = {}

    code_match = re.search(r"发票代码[：:]\s*(\S+)", full_text)
    if code_match:
        fields["发票代码"] = code_match.group(1)
    code_fallback = re.search(r"(\d{12})", full_text)
    if "发票代码" not in fields and code_fallback:
        fields["发票代码"] = code_fallback.group(1)

    num_match = re.search(r"发票号码[：:]\s*(\S+)", full_text)
    if num_match:
        fields["发票号码"] = num_match.group(1)
    num_fallback = re.search(r"发票号码[：:]?\s*(\d{8})", full_text)
    if "发票号码" not in fields and num_fallback:
        fields["发票号码"] = num_fallback.group(1)

    date_match = re.search(r"开票日期[：:]\s*(\S+)", full_text)
    if date_match:
        fields["开票日期"] = date_match.group(1)
    date_fallback = re.search(r"(\d{4}[年\-/\.]\d{1,2}[月\-/\.]\d{1,2}[日]?)", full_text)
    if "开票日期" not in fields and date_fallback:
        fields["开票日期"] = date_fallback.group(1)

    check_match = re.search(r"校验码[：:]\s*(\S+)", full_text)
    if check_match:
        fields["校验码"] = check_match.group(1)

    buyer_name = None
    seller_name = None
    for i, b in enumerate(sorted_blocks):
        text = b["text"].strip()
        if "名称" in text and "购买方" in text or "购" in text and "名" in text:
            nxt = sorted_blocks[i + 1] if i + 1 < len(sorted_blocks) else None
            if nxt:
                buyer_name = nxt["text"].strip()
            break

    buyer_match = re.search(r"购买方[名称]?[：:]\s*(\S+)", full_text)
    if buyer_match:
        buyer_name = buyer_match.group(1)
    buyer_ns_match = re.search(r"购买方.*?纳税人识别号[：:]\s*(\S+)", full_text)
    if buyer_ns_match:
        fields["购买方纳税人识别号"] = buyer_ns_match.group(1)

    seller_match = re.search(r"销售方[名称]?[：:]\s*(\S+)", full_text)
    if seller_match:
        seller_name = seller_match.group(1)
    seller_ns_match = re.search(r"销售方.*?纳税人识别号[：:]\s*(\S+)", full_text)
    if seller_ns_match:
        fields["销售方纳税人识别号"] = seller_ns_match.group(1)

    if buyer_name is None:
        for line in lines:
            if "名称" in line and "纳税人识别号" not in line:
                buyer_match_inline = re.search(r"[：:]\s*(\S+)", line)
                if buyer_match_inline:
                    buyer_name = buyer_match_inline.group(1)
                    break

    if buyer_name:
        fields["购买方名称"] = buyer_name
    if seller_name:
        fields["销售方名称"] = seller_name

    total_match = re.search(r"价税合计[（(]大写[)）]?[：:]\s*(\S+)", full_text)
    if total_match:
        fields["价税合计(大写)"] = total_match.group(1)
    total_num_match = re.search(r"价税合计[（(]小写[)）]?[：:]\s*(\S+)", full_text)
    if total_num_match:
        fields["价税合计(小写)"] = total_num_match.group(1)

    total_fallback = re.search(r"(小写)[）\)]?[：:]\s*[¥￥]?\s*(\d+\.?\d*)", full_text)
    if "价税合计(小写)" not in fields and total_fallback:
        fields["价税合计(小写)"] = total_fallback.group(2)

    amount_match = re.search(r"金额[：:]\s*[¥￥]?(\d+\.?\d*)", full_text)
    if amount_match:
        fields["金额"] = amount_match.group(1)

    tax_match = re.search(r"税额[：:]\s*[¥￥]?(\d+\.?\d*)", full_text)
    if tax_match:
        fields["税额"] = tax_match.group(1)

    rate_match = re.search(r"税率[：:]\s*(\S+)", full_text)
    if rate_match:
        fields["税率"] = rate_match.group(1)

    machine_num = re.search(r"机器编号[：:]\s*(\S+)", full_text)
    if machine_num:
        fields["机器编号"] = machine_num.group(1)

    for line in lines:
        line_stripped = line.replace(" ", "")
        tax_amt = re.search(r"(\d+\.?\d*)", line_stripped)
        if "税额" in line_stripped and tax_amt:
            fields["税额"] = tax_amt.group(1)
        if "金额" in line_stripped and not any(k.startswith("金额") for k in fields.keys()):
            amt = re.search(r"金额[：:]?\s*[¥￥]?\s*(\d+\.?\d*)", line)
            if amt:
                fields["金额"] = amt.group(1)
        if "价税合计" in line_stripped and ("大写" in line_stripped or "小写" in line_stripped):
            caps = re.search(r"价税合计[（(]大写[)）]?[：:]\s*(\S+)", line)
            if caps:
                fields["价税合计(大写)"] = caps.group(1)
            small = re.search(r"价税合计[（(]小写[)）]?[：:]\s*[¥￥]?\s*(\d+\.?\d*)", line)
            if small:
                fields["价税合计(小写)"] = small.group(1)

    return fields


def extract_general_invoice(blocks: list[dict]) -> dict:
    sorted_blocks = _sort_blocks(blocks)
    full_text = " ".join(b["text"] for b in sorted_blocks)

    fields = {}

    if "invoice" in full_text.lower() or "receipt" in full_text.lower():
        num_match = re.search(r"(?:INV|Invoice|No[.:]?)\s*[-#]?\s*(\S+)", full_text)
        if num_match:
            fields["Invoice Number"] = num_match.group(1)

        date_match = re.search(r"Date[.:]?\s*(\S+)", full_text)
        if date_match:
            fields["Date"] = date_match.group(1)

        total_match = re.search(r"Total[.:]?\s*[$]?\s*(\d+\.?\d*)", full_text)
        if total_match:
            fields["Total Amount"] = total_match.group(1)

    return fields


def _extract_name_and_tax_id(blocks: list[dict], side_label: str) -> dict:
    full_text = " ".join(b["text"] for b in blocks)
    fields = {}

    name_match = re.search(r"(?:名称|名\s*称)\s*[：:]\s*(.+?)(?:\s+(?:纳税人|地址|电话|开户))", full_text)
    if not name_match:
        name_match = re.search(r"(?:名称|名\s*称)\s*[：:]\s*(\S+)", full_text)
    if name_match:
        val = name_match.group(1).strip()
        if val and not any(kw in val for kw in ("纳税人", "识别号", "地址", "电话", "开户")):
            fields[f"{side_label}名称"] = val
        else:
            fallback = re.search(r"(?:名称|名\s*称)\s*[：:]\s*(\S+)", full_text)
            if fallback:
                fields[f"{side_label}名称"] = fallback.group(1).strip()

    nsr_match = re.search(
        r"(?:纳税人识别号|识别号|纳税人)\s*[：:]\s*(\w+)",
        full_text,
    )
    if nsr_match:
        val = nsr_match.group(1).strip()
        if re.match(r'^[\w\(\)\（\）]+$', val) and len(val) >= 8:
            fields[f"{side_label}纳税人识别号"] = val
    nsr_fallback = re.search(r"(\d{15,20})", full_text)
    if f"{side_label}纳税人识别号" not in fields and nsr_fallback:
        fields[f"{side_label}纳税人识别号"] = nsr_fallback.group(1)

    if f"{side_label}名称" not in fields:
        for b in blocks:
            t = b["text"].strip()
            if t and not any(kw in t for kw in ("发票", "识别号", "密码", "电话", "开户", "地址", "代码", "号码", "日期", "校验")):
                fields[f"{side_label}名称"] = t
                break

    return fields


def extract_block_fields(blocks: list[dict], side_label: str) -> dict:
    return _extract_name_and_tax_id(blocks, side_label)


def extract_split(left_blocks: list[dict], right_blocks: list[dict]) -> dict:
    fields = {}
    fields.update(_extract_name_and_tax_id(left_blocks, "购买方"))
    fields.update(_extract_name_and_tax_id(right_blocks, "销售方"))

    all_text = " ".join(b["text"] for b in left_blocks + right_blocks)

    num_match = re.search(r"发票号码[：:]\s*(\S+)", all_text)
    if num_match:
        fields["发票号码"] = num_match.group(1)
    code_match = re.search(r"发票代码[：:]\s*(\S+)", all_text)
    if code_match:
        fields["发票代码"] = code_match.group(1)

    total_match = re.search(r"价税合计[（(]小写[)）]?\s*[：:]?\s*[¥￥]?\s*(\d+\.?\d*)", all_text)
    if total_match:
        fields["含税金额"] = total_match.group(1)
    else:
        total_fallback = re.search(r"[（(]小写[)）]\s*[¥￥]?\s*(\d+\.?\d*)", all_text)
        if total_fallback:
            fields["含税金额"] = total_fallback.group(1)

    return fields


def extract(blocks: list[dict], invoice_type: str = "vat") -> dict:
    if invoice_type == "vat":
        return extract_vat_invoice(blocks)
    else:
        return extract_general_invoice(blocks)
