import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from functools import lru_cache
from typing import Optional

from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from invoice_ocr.config import OcrConfig
from invoice_ocr.recognizer import InvoiceRecognizer


app = FastAPI(
    title="Invoice OCR API",
    description="发票OCR识别服务 - 基于RapidOCR的本地部署方案",
    version="1.0.0",
)


class OcrResponse(BaseModel):
    purchase_name: str = ""
    purchase_tax_id: str = ""
    seller_name: str = ""
    seller_tax_id: str = ""
    invoice_number: str = ""
    total_amount: str = ""
    raw: dict = {}


@lru_cache(maxsize=1)
def get_recognizer(mode: str = "accurate", gpu: bool = False) -> InvoiceRecognizer:
    config = OcrConfig.accurate() if mode == "accurate" else OcrConfig.fast()
    if gpu:
        config.use_gpu = True
    return InvoiceRecognizer(config)


@app.get("/")
def root():
    return {
        "service": "Invoice OCR API",
        "version": "1.0.0",
        "endpoints": {
            "POST /ocr": "上传图片进行发票OCR识别",
            "GET /health": "健康检查",
        },
    }


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/ocr", response_model=OcrResponse)
async def ocr(
    file: UploadFile = File(...),
    mode: str = "accurate",
    gpu: bool = False,
):
    if not file.content_type or not file.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail=f"不支持的文件类型: {file.content_type}，请上传图片")

    contents = await file.read()
    if not contents:
        raise HTTPException(status_code=400, detail="空文件")

    recognizer = get_recognizer(mode, gpu)

    try:
        result = recognizer.split_recognize_bytes(contents)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"OCR 识别失败: {str(e)}")

    fields = result["fields"]

    return OcrResponse(
        purchase_name=fields.get("购买方名称", ""),
        purchase_tax_id=fields.get("购买方纳税人识别号", ""),
        seller_name=fields.get("销售方名称", ""),
        seller_tax_id=fields.get("销售方纳税人识别号", ""),
        invoice_number=fields.get("发票号码", ""),
        total_amount=fields.get("含税金额", ""),
        raw=fields,
    )


def main():
    import uvicorn
    uvicorn.run(
        "invoice_ocr.server:app",
        host="0.0.0.0",
        port=8000,
        reload=False,
    )


if __name__ == "__main__":
    main()
