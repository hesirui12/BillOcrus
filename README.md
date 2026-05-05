# Invoice OCR

基于 **RapidOCR**（PP-OCRv4 模型）的本地发票识别工具。纯离线运行，无需联网，中文路径兼容。

---

## 特性

- **纯本地推理** — 基于 ONNX Runtime，不依赖任何云端 API
- **中文路径兼容** — 支持 `发票.png` 等含中文的文件路径
- **Split 算法** — 图片垂直对半分割，左右分别 OCR，精准提取购销方信息
- **REST API** — 内置 FastAPI 服务，可集成到业务系统
- **高效准确** — PP-OCRv4 模型，CPU 推理速度快，识别精度高
- **GPU 加速** — 可选 DirectML/CUDA 加速

---

## 快速开始

### 1. 安装

```bash
# 克隆项目后
uv venv
.venv\Scripts\activate
uv pip install -r requirements.txt
```

### 2. CLI 方式

```bash
# 识别单张发票（默认 split 模式）
python -m invoice_ocr 发票.jpg


# 批量识别
python -m invoice_ocr 发票1.jpg 发票2.jpg 发票3.jpg

# 识别整个目录
python -m invoice_ocr ./发票目录 --batch-dir

# 输出为 JSON
python -m invoice_ocr 发票.jpg -f json

# 保存到文件
python -m invoice_ocr 发票.jpg -o result.json

# 快速模式（更快但精度略低）
python -m invoice_ocr 发票.jpg --mode fast

# 全量识别模式（提取所有字段，不分割图片）
python -m invoice_ocr 发票.jpg --full

# GPU 加速
python -m invoice_ocr 发票.jpg --gpu
```

### 3. REST API 方式

```bash
# 启动服务
python -m invoice_ocr.server

# 或指定端口
python -c "from invoice_ocr.server import main; main()"
```

服务默认启动在 `http://localhost:8000`

#### API 文档

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/` | 服务信息 |
| GET | `/health` | 健康检查 |
| POST | `/ocr` | 发票 OCR 识别 |

#### 调用示例

```bash
# 使用 curl
curl -X POST http://localhost:8000/ocr \
  -F "file=@发票.jpg" \
  -F "mode=accurate"

# 使用 Python requests
import requests
resp = requests.post(
    "http://localhost:8000/ocr",
    files={"file": open("发票.jpg", "rb")},
    data={"mode": "accurate"},
)
print(resp.json())
```

#### 响应格式

```json
{
  "purchase_name": "",
  "purchase_tax_id": "",
  "seller_name": "",
  "seller_tax_id": "",
  "invoice_number": "",
  "raw": {
    "购买方名称": "",
    "购买方纳税人识别号": "",
    "销售方名称": "",
    "销售方纳税人识别号": "",
    "发票号码": ""
  }
}
```

---

## 算法说明

### Split 模式（默认）

```
┌──────────────────────┬──────────────────────┐
│                      │                      │
│    左半边 (OCR)      │    右半边 (OCR)      │
│    ────────────      │    ────────────      │
│    购买方名称         │    销售方名称         │
│    购买方纳税识别号    │    销售方纳税识别号   │
│                      │                      │
└──────────────────────┴──────────────────────┘
         ↓                        ↓
  提取购买方信息            提取销售方信息

  发票号码 ← 扫描左右两边结果
```

流程：
1. 图片垂直切为左右两半
2. 对两半分别做 OCR
3. 左半 → 提取 购买方名称 + 纳税人识别号
4. 右半 → 提取 销售方名称 + 纳税人识别号
5. 合并左右 OCR 文本 → 提取 发票号码

### 全量模式 (`--full`)

对整个图片做一次完整 OCR，提取增值税发票的全部字段（包括代码、号码、日期、购销方、金额、税额、价税合计等）。

---

## 项目结构

```
invoice-ocr/
├── invoice_ocr/              # 核心包
│   ├── __init__.py
│   ├── __main__.py           # python -m 入口
│   ├── cli.py                # 命令行界面
│   ├── config.py             # 配置（fast/accurate 预设）
│   ├── engine.py             # RapidOCR 引擎封装
│   ├── recognizer.py         # 识别器（split + 全量）
│   ├── extractor.py          # 字段提取（规则引擎）
│   ├── splitter.py           # 图片对半分割
│   └── server.py             # FastAPI REST 服务
├── requirements.txt
└── README.md
```

---

## 性能

| 模式 | 速度（单张 CPU） | 精度 |
|------|------------------|------|
| `--mode fast`   | ~1-2s | 中等 |
| `--mode accurate` (默认) | ~2-4s | 高 |
| `--gpu`         | ~0.5-1s | 高 |

> 以上为 i7-12700 CPU 测试参考值，实际速度因图片大小和硬件而异。

---

## 技术栈

| 组件 | 选型 | 说明 |
|------|------|------|
| OCR 引擎 | RapidOCR (PP-OCRv4) | 百度自研 OCR 模型，ONNX Runtime 推理 |
| 图像处理 | OpenCV | 图片编解码、分割 |
| REST 框架 | FastAPI | 高性能异步 Web 框架 |
| 运行环境 | Python 3.12+ | |
