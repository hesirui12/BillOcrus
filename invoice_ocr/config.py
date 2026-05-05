from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class OcrConfig:
    model_dir: str = ""
    use_gpu: bool = False
    gpu_id: int = 0
    num_workers: int = 4
    det_db_thresh: float = 0.3
    det_db_box_thresh: float = 0.5
    rec_batch_num: int = 6
    lang: str = "ch"
    print_verbose: bool = False
    min_height: int = 30
    width_height_ratio: float = -1.0

    @classmethod
    def fast(cls) -> "OcrConfig":
        return cls(
            det_db_thresh=0.3,
            det_db_box_thresh=0.4,
            rec_batch_num=8,
            num_workers=4,
        )

    @classmethod
    def accurate(cls) -> "OcrConfig":
        return cls(
            det_db_thresh=0.2,
            det_db_box_thresh=0.3,
            rec_batch_num=4,
        )

    def validate(self):
        if self.model_dir and not Path(self.model_dir).exists():
            raise ValueError(f"模型目录不存在: {self.model_dir}")
