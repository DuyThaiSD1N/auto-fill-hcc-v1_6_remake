"""Nhánh Qwen JSON: ảnh đã tiền xử lý (app/services/qwen_doc_giay) → Qwen trả THẲNG JSON các field kết hôn,
không qua chữ OCR.

Cả hồ sơ gửi MỘT lượt để model đối chiếu được tờ khai với thẻ. Prompt = base_prompt + luật của thủ tục kết hôn (cùng bản
với lượt trích từ chữ OCR), chỉ thay khối đầu vào bằng bản "đầu vào là ảnh".

Trang chứa ≥ 2 thẻ (đã tìm MỘT lần ở tach_the.cat, dùng chung với nhánh Vintern) gửi từng thẻ đã cắt, tự xoay riêng
từng thẻ, thay cho ảnh trang + dải phóng to: ít ảnh hơn, chữ trên thẻ to hơn.
"""
from __future__ import annotations

import time
from concurrent.futures import ThreadPoolExecutor

from app.config import settings
from app.pipelines._shared.compact_agent import runner as compact_runner
from app.pipelines.ket_hon.process import base_prompt
from app.pipelines.ket_hon.process.prompt import EXTRA_RULES
from app.pipelines.ket_hon.process.schema import ALIASES, ALLOWED, COMPACT_COMP_BY_NAME, FIELDS
from app.services.llm import client
from app.services.qwen_doc_giay import chuan_bi_anh as cb
from app.services.qwen_doc_giay import goi_qwen as gq
from app.services.qwen_doc_giay import tien_xu_ly as tx
from app.services.qwen_doc_giay import tao_cau_hinh
from app.services.qwen_doc_giay.chung import MayChuQwen
from app.services.qwen_doc_giay.doc_tep import apply_rotation

_TOI_DA_ANH = 24            # cả hồ sơ một lượt; máy chủ nhận được tới 40 ảnh, chừa khoảng cho token
_MAX_TOKENS = 3000
_PHONG_THE_TOI_DA = 2.5     # thẻ cắt từ bản scan nhỏ: phóng tối đa 2,5 lần để chữ cao khoảng như dải phóng to


def _base_url() -> str:
    url = (settings.ocr_qwen_base_url or settings.llm_base_url).rstrip("/")
    return url if url.endswith("/v1") else url + "/v1"


def _cau_hinh() -> dict:
    prompt = base_prompt.build_system_prompt(FIELDS, EXTRA_RULES, dau_vao=base_prompt.DAU_VAO_ANH)
    return tao_cau_hinh(base_url=_base_url(), model=settings.ocr_qwen_model or settings.llm_model,
                        prompt_he_thong=prompt, max_tokens=_MAX_TOKENS)


def _lap_json(text: str) -> bool:
    """JSON trả trên MỘT dòng dài 2–3 nghìn ký tự là bình thường: bộ chặn lặp của OCR (cắt dòng > 2000 ký tự) cắt
    cụt JSON. Nhánh này chỉ dừng khi một cụm ký tự lặp liền nhau thật."""
    return bool(gq._fragment_loop(text[-2500:]))


def _anh_the(crop, label: str, prep: dict, spec: dict) -> cb.Shot:
    o = tx.detect_orientation(crop) if prep.get("auto_orient") else {}
    thang = apply_rotation(crop, o.get("deg", 0)) if o.get("deg") else crop
    scale = cb.fit_scale(thang.width, thang.height, spec, max_up=_PHONG_THE_TOI_DA)
    return cb.Shot(label, tx.to_pil(tx.finish_tile(tx.to_bgr(thang), prep, scale)))


def _chuan_bi(files: list[dict], da_cat: list[list[tuple]], cfg: dict, may: MayChuQwen) -> tuple[list, int]:
    """→ (các Shot theo thứ tự tài liệu/trang, số trang)."""
    trang = [(ti, f.get("name"), i, len(tep), p, khung)
             for ti, (f, tep) in enumerate(zip(files, da_cat), 1)
             for i, (p, khung) in enumerate(tep, 1)]
    so_anh_trang = sum(len(k) if k else 1 for *_, k in trang)
    moi_trang = max(1, min(int(cfg["max_images"]), _TOI_DA_ANH // max(1, so_anh_trang)))

    def _mot(item):
        ti, name, i, n, img, khung = item
        label = f"Tài liệu {ti} (tên file: {name}) – trang {i}/{n}"
        if khung:
            return [_anh_the(img.crop(b), f"{label}: thẻ {k}/{len(khung)} cắt riêng từ trang", cfg["prep"], may.spec)
                    for k, b in enumerate(khung, 1)]
        page, info = tx.chuan_bi_trang(img, cfg["prep"])
        return cb.page_shots(page, label, cfg["zoom"], may.spec, cfg["prep"], max_images=moi_trang,
                             text=info.get("text"))

    with ThreadPoolExecutor(max_workers=4) as pool:
        res = list(pool.map(_mot, trang))
    return [s for shots in res for s in shots], len(trang)


def doc(files: list[dict], da_cat: list[list[tuple]]) -> dict:
    """Chạy đồng bộ (gọi qua asyncio.to_thread). files: [{name, type, dataUrl}]; da_cat: kết quả tach_the.cat.
    → {raw: {field: value} đã validate, text, usage, so_anh, ms}; lỗi → {raw: {}, error}."""
    t0 = time.monotonic()
    cfg = _cau_hinh()
    may = MayChuQwen(cfg)
    shots, so_trang = _chuan_bi(files, da_cat, cfg, may)
    if not shots:
        return {"raw": {}, "error": "không đọc được trang ảnh nào", "ms": int((time.monotonic() - t0) * 1000)}
    req = cb.build_content(shots, f"Trên đây là toàn bộ {len(shots)} ảnh của hồ sơ ({len(files)} tài liệu, "
                                  f"{so_trang} trang). Trích các field theo quy tắc, chỉ trả JSON.", cfg["image_format"])
    text, usage = "", {}
    for ev in gq.stream_openai(cfg["base_url"], cfg.get("api_key", ""), cfg["model"], may.system, req.content,
                               cfg["temperature"], min(_MAX_TOKENS, cfg["max_tokens"]),
                               cfg.get("disable_thinking", True), cfg.get("repetition_penalty", 1.0),
                               stop_check=_lap_json):
        if ev["type"] == "text":
            text += ev["text"]
        elif ev["type"] == "usage":
            usage = ev
    out = {"text": gq.clean_output(text), "usage": usage, "so_anh": req.image_count,
           "ms": int((time.monotonic() - t0) * 1000)}
    try:
        parsed = client.extract_json_block(text)
        fields = compact_runner.validate(parsed.get("fields"), ALLOWED, COMPACT_COMP_BY_NAME, ALIASES)
        out["raw"] = {f["name"]: f.get("value") for f in fields if f.get("name")}
    except Exception as e:  # noqa: BLE001
        out["raw"], out["error"] = {}, f"json: {e}"
    return out
