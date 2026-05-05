import argparse
import json
import sys
from pathlib import Path

from .config import OcrConfig
from .recognizer import InvoiceRecognizer


REQUIRED_FIELDS = [
    "购买方名称",
    "购买方纳税人识别号",
    "销售方名称",
    "销售方纳税人识别号",
    "发票号码",
    "含税金额",
]


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="invoice-ocr",
        description="本地 OCR 发票识别工具 - 基于 RapidOCR，纯离线运行",
    )

    parser.add_argument(
        "images",
        nargs="+",
        help="图片文件路径，支持多个文件或目录",
    )
    parser.add_argument(
        "-o", "--output",
        help="输出结果到JSON文件",
    )
    parser.add_argument(
        "-f", "--format",
        choices=["text", "json"],
        default="text",
        help="输出格式：text(默认)-人类可读, json-原始JSON",
    )
    parser.add_argument(
        "--mode",
        choices=["fast", "accurate"],
        default="accurate",
        help="识别模式：fast-快速, accurate-高精度(默认)",
    )
    parser.add_argument(
        "--gpu",
        action="store_true",
        help="启用GPU加速（需安装onnxruntime-gpu）",
    )
    parser.add_argument(
        "--gpu-id",
        type=int,
        default=0,
        help="GPU设备ID，默认0",
    )
    parser.add_argument(
        "--workers",
        type=int,
        default=4,
        help="CPU线程数，默认4",
    )
    parser.add_argument(
        "--batch-dir",
        help="批量识别目录中的所有图片",
    )
    parser.add_argument(
        "--model-dir",
        help="自定义模型目录路径（若不指定则使用内置模型）",
    )
    parser.add_argument(
        "--full",
        action="store_true",
        help="全量识别模式（提取所有字段，不分割图片）",
    )

    return parser.parse_args(argv)


def _find_images(paths: list[str]) -> list[Path]:
    exts = {".jpg", ".jpeg", ".png", ".bmp", ".tiff", ".tif", ".webp"}
    images = []
    for p in paths:
        path = Path(p)
        if path.is_dir():
            images.extend(
                f for f in path.iterdir() if f.is_file() and f.suffix.lower() in exts
            )
        elif path.is_file() and path.suffix.lower() in exts:
            images.append(path)
    return images


def _format_fields(fields: dict) -> str:
    lines = []
    for key in REQUIRED_FIELDS:
        val = fields.get(key, "")
        lines.append(f"  {key}: {val}")
    extra = {k: v for k, v in fields.items() if k not in REQUIRED_FIELDS}
    for key, val in extra.items():
        lines.append(f"  {key}: {val}")
    return "\n".join(lines)


def main(argv: list[str] | None = None):
    args = parse_args(argv)

    if args.mode == "fast":
        config = OcrConfig.fast()
    else:
        config = OcrConfig.accurate()

    if args.gpu:
        config.use_gpu = True
        config.gpu_id = args.gpu_id
    if args.workers:
        config.num_workers = args.workers
    if args.model_dir:
        config.model_dir = args.model_dir

    try:
        config.validate()
    except ValueError as e:
        print(f"[错误] {e}", file=sys.stderr)
        sys.exit(1)

    recognizer = InvoiceRecognizer(config)

    if args.batch_dir:
        image_paths = _find_images([args.batch_dir])
        if not image_paths:
            print(f"[警告] 目录中未找到图片: {args.batch_dir}", file=sys.stderr)
            sys.exit(1)
    else:
        image_paths = _find_images(args.images)
        if not image_paths:
            print("[警告] 未找到可识别的图片文件", file=sys.stderr)
            sys.exit(1)

    print(f"共找到 {len(image_paths)} 个图片文件\n")

    all_results = []
    for i, img_path in enumerate(image_paths, 1):
        print(f"[{i}/{len(image_paths)}] 正在识别: {img_path.name}...", file=sys.stderr)
        try:
            if args.full:
                result = recognizer.recognize_with_fields(str(img_path))
                blocks, fields = result["blocks"], result["fields"]
                all_results.append({"path": str(img_path), "blocks": blocks, "fields": fields})
            else:
                result = recognizer.split_recognize(str(img_path))
                fields = result["fields"]
                all_results.append({"path": str(img_path), "fields": fields})

            fields = result["fields"]

            if args.format == "json":
                print(json.dumps(fields, ensure_ascii=False, indent=2))
            else:
                print(f"文件: {img_path}")
                print("=" * 50)
                print(_format_fields(fields))
                print("=" * 50)

        except Exception as e:
            print(f"[错误] {img_path.name}: {e}", file=sys.stderr)

        if i < len(image_paths):
            print()

    if args.output and all_results:
        Path(args.output).write_text(
            json.dumps(all_results, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        print(f"\n结果已保存到: {args.output}", file=sys.stderr)


if __name__ == "__main__":
    main()
