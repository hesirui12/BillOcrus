from pathlib import Path

import cv2
import numpy as np


def split_half(image_input: str | Path | bytes | np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    if isinstance(image_input, np.ndarray):
        img = image_input
    elif isinstance(image_input, bytes):
        nparr = np.frombuffer(image_input, np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    else:
        img_bytes = np.fromfile(str(image_input), dtype=np.uint8)
        img = cv2.imdecode(img_bytes, cv2.IMREAD_COLOR)

    if img is None:
        raise ValueError(f"无法读取图片: {image_input}")

    h, w = img.shape[:2]
    mid = w // 2

    left = img[:, :mid, :].copy()
    right = img[:, mid:, :].copy()

    return left, right


def split_half_save(
    image_input: str | Path | bytes | np.ndarray,
    left_path: str | Path,
    right_path: str | Path,
) -> tuple[str, str]:
    left, right = split_half(image_input)
    cv2.imwrite(str(left_path), left)
    cv2.imwrite(str(right_path), right)
    return str(left_path), str(right_path)
