"""Đính kèm 1.115692 Lào Cai cổng iGate mới — chế độ TÁCH giấy tờ (cài đặt "Tách giấy tờ" bật, ``splitDocuments is True``).

Dùng lại bộ chia trang của cổng Lào Cai (``_shared/lao_cai_tach_giay_to.plan_with_split``, như 1.115683/1.115684): OCR tệp
gốc một lần, LLM chia mọi tệp thành từng giấy theo trang trong MỘT lượt (không sót trang, hai mặt CCCD cùng người là một
giấy), cắt PDF con rồi chạy planner đính nguyên tệp (dinh_kem_khong_tach) trên các PDF con → tệp gộp kiểu "BoA_TronBo.pdf"
(Đơn tr.1–2, GCN tr.3–6, Giấy ủy quyền tr.7–9) vào đúng dòng 1/2/3 (hoặc Đơn + Thông báo vào dòng 4/5); kế hoạch trả về
tệp gốc bằng ``sourceSegments``. LLM chia giấy lỗi → planner chạy trên tệp gốc (đính nguyên tệp) + cảnh báo.

Bộ chia trang có thể mở giấy mới ở trang sơ đồ / những thay đổi của GCN, trang lời chứng của Giấy ủy quyền, trang 2
của Đơn → các đoạn LIỀN TRANG cùng tệp gốc, cùng loại, cùng dòng được gộp lại thành một tệp (ảnh ánh xạ: mỗi giấy một
tệp nguyên vẹn).
"""

from app.pipelines._shared.lao_cai_tach_giay_to import always_split
from app.pipelines._shared.lao_cai_tach_giay_to import plan_with_split as _chia_trang
from app.pipelines.cho_thue_dat_thue_rung_igate_lao_cai.attach import planner as _igate
from app.process.schemas import FileItem

from ..dinh_kem_khong_tach import planner as _khong_tach
from ..dinh_kem_khong_tach.planner import plan as plan_without_split

_GOP_DUOC = {_khong_tach._T_DON, _khong_tach._T_GCN, _khong_tach._T_DAI_DIEN, _khong_tach._T_THONG_BAO}


def _mot_doan(item: dict) -> dict | None:
    segments = item.get("sourceSegments") or []
    if len(segments) == 1 and segments[0].get("pageIndexes"):
        return segments[0]
    return None


def gop_doan_lien_trang(attachments: list[dict]) -> list[dict]:
    """Gộp mục kế hoạch liền nhau: cùng dòng, cùng loại giấy thành phần, cùng tệp gốc, trang nối tiếp."""
    out: list[dict] = []
    gop = False
    for item in attachments:
        prev = out[-1] if out else None
        doan, doan_truoc = _mot_doan(item), _mot_doan(prev) if prev else None
        if (
            prev is not None and doan and doan_truoc
            and item.get("target") == prev.get("target") == "attp-row"
            and item.get("detectedType") == prev.get("detectedType")
            and item.get("detectedType") in _GOP_DUOC
            and item.get("componentIndex") == prev.get("componentIndex")
            and doan["fileIndex"] == doan_truoc["fileIndex"]
            and doan["pageIndexes"][0] == doan_truoc["pageIndexes"][-1] + 1
        ):
            prev["sourceSegments"] = [{"fileIndex": doan["fileIndex"],
                                       "pageIndexes": [*doan_truoc["pageIndexes"], *doan["pageIndexes"]]}]
            gop = True
            continue
        out.append(dict(item))
    if gop:
        # Tên tài liệu đã đánh số "(1)", "(2)" theo số đoạn trước khi gộp → đặt lại tên gốc rồi đánh số lại.
        hang = [i for i in out if i.get("target") == "attp-row" and "componentIndex" in i]
        for item in hang:
            item["documentName"] = _khong_tach._TEN.get(item.get("detectedType"), item["documentName"])
        _igate._dedupe_document_names(hang)
    return out


async def plan(files: list[FileItem], options: dict | None = None, session: dict | None = None) -> dict:
    opts = options or {}
    # Router đã chia trang (tài khoản luôn tách) hoặc extension không cắt được trang → đính nguyên tệp, không chia lần hai.
    if always_split(opts) or opts.get("supportsSourceSegments") is False:
        return await plan_without_split(files, options, session)
    result = await _chia_trang(plan_without_split, files, options, session)
    result["attachments"] = gop_doan_lien_trang(result.get("attachments") or [])
    return result
