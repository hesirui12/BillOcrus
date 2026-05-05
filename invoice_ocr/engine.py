from pathlib import Path
from typing import Optional

import cv2
import numpy as np

from .config import OcrConfig


class OcrEngine:
    def __init__(self, config: Optional[OcrConfig] = None):
        self.config = config or OcrConfig()
        self._reader = None

    def _lazy_init(self):
        if self._reader is not None:
            return
        from rapidocr_onnxruntime import RapidOCR

        self._reader = RapidOCR(
            det_db_thresh=self.config.det_db_thresh,
            det_db_box_thresh=self.config.det_db_box_thresh,
            rec_batch_num=self.config.rec_batch_num,
            cpu_threads=self.config.num_workers,
            print_verbose=self.config.print_verbose,
            min_height=self.config.min_height,
            width_height_ratio=self.config.width_height_ratio,
        )

    def _format_result(self, raw_result) -> list[dict]:
        if raw_result is None:
            return []
        return [
            {"bbox": b, "text": t, "score": s}
            for b, t, s in raw_result
        ]

    def recognize(self, image_path: str | Path) -> list[dict]:
        self._lazy_init()
        img_bytes = np.fromfile(str(image_path), dtype=np.uint8)
        img = cv2.imdecode(img_bytes, cv2.IMREAD_COLOR)
        if img is None:
            raise ValueError(f"无法读取图片: {image_path}")
        result, elapse = self._reader(img)
        return self._format_result(result)

    def recognize_bytes(self, image_bytes: bytes) -> list[dict]:
        self._lazy_init()
        nparr = np.frombuffer(image_bytes, np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        result, elapse = self._reader(img)
        return self._format_result(result)

    def recognize_numpy(self, image: np.ndarray) -> list[dict]:
        self._lazy_init()
        result, elapse = self._reader(image)
        return self._format_result(result)
