from pathlib import Path
from typing import Optional

from .config import OcrConfig
from .engine import OcrEngine
from .extractor import extract as extract_fields
from .extractor import extract_split as extract_split_fields
from .splitter import split_half


class InvoiceRecognizer:
    def __init__(self, config: Optional[OcrConfig] = None):
        self._engine = OcrEngine(config)

    def recognize(self, image_path: str | Path) -> list[dict]:
        return self._engine.recognize(image_path)

    def recognize_bytes(self, image_bytes: bytes) -> list[dict]:
        return self._engine.recognize_bytes(image_bytes)

    def recognize_with_fields(
        self, image_path: str | Path, invoice_type: str = "vat"
    ) -> dict:
        blocks = self._engine.recognize(image_path)
        fields = extract_fields(blocks, invoice_type)
        return {"blocks": blocks, "fields": fields}

    def batch_recognize(
        self, image_paths: list[str | Path], invoice_type: str = "vat"
    ) -> list[dict]:
        results = []
        for path in image_paths:
            blocks = self._engine.recognize(path)
            fields = extract_fields(blocks, invoice_type)
            results.append({"path": str(path), "blocks": blocks, "fields": fields})
        return results

    def split_recognize(self, image_path: str | Path) -> dict:
        left_img, right_img = split_half(image_path)
        left_blocks = self._engine.recognize_numpy(left_img)
        right_blocks = self._engine.recognize_numpy(right_img)
        fields = extract_split_fields(left_blocks, right_blocks)
        return {
            "left_blocks": left_blocks,
            "right_blocks": right_blocks,
            "fields": fields,
        }

    def split_recognize_bytes(self, image_bytes: bytes) -> dict:
        import numpy as np
        import cv2
        nparr = np.frombuffer(image_bytes, np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        if img is None:
            raise ValueError("无法解码图片")
        left_img, right_img = split_half(img)
        left_blocks = self._engine.recognize_numpy(left_img)
        right_blocks = self._engine.recognize_numpy(right_img)
        fields = extract_split_fields(left_blocks, right_blocks)
        return {
            "left_blocks": left_blocks,
            "right_blocks": right_blocks,
            "fields": fields,
        }
