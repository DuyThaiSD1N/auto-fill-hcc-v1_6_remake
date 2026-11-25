"""Đính kèm 1.115591 (Lai Châu) — chế độ TÁCH giấy tờ (cài đặt "Tách giấy tờ" bật, ``splitDocuments is True``).

Cổng Lai Châu chưa có bộ chia trang riêng → dùng lại bộ chia trang chung của thủ tục đất đai
(``_shared/lao_cai_tach_giay_to.plan_with_split``): OCR tệp gốc một lần, LLM chia mọi tệp thành từng giấy theo trang trong
MỘT lượt (không sót trang, hai mặt CCCD cùng người là một giấy), cắt PDF con rồi chạy planner đính nguyên tệp
(dinh_kem_khong_tach) trên các PDF con → văn bản đề nghị Mẫu số 30 và mảnh trích đo scan chung một bản vào đúng dòng 2 /
dòng 1; kế hoạch trả về tệp gốc bằng ``sourceSegments`` (extension tự cắt trang). LLM chia giấy lỗi → planner chạy trên
tệp gốc (đính nguyên tệp) + cảnh báo.

Chạy thật 25/11/2026 với văn bản đề nghị 2 trang: bộ chia trang mở giấy mới ở trang 2 (bắt đầu bằng "8a. Hình thức giao
đất…", không có tiêu đề) → cùng dòng Mẫu số 30 thành hai tệp. Các đoạn LIỀN TRANG cùng tệp gốc, cùng loại văn bản đề
nghị / trích lục, cùng dòng được gộp lại thành một tệp (căn cước không gộp: hai thẻ liền nhau có thể của hai người).
"""

from app.pipelines._shared.lao_cai_tach_giay_to import plan_with_split as _chia_trang
from app.process.schemas import FileItem

from ..dinh_kem_khong_tach import planner as _khong_tach
from ..dinh_kem_khong_tach.planner import plan as plan_without_split

_GOP_DUOC = {_khong_tach._T_VAN_BAN, _khong_tach._T_TRICH_LUC}


def _mot_doan(item: dict | None) -> dict | None:
    segments = (item or {}).get("sourceSegments") or []
    if len(segments) == 1 and segments[0].get("pageIndexes"):
        return segments[0]
    return None


def gop_doan_lien_trang(attachments: list[dict]) -> list[dict]:
    """Gộp mục kế hoạch liền nhau: cùng dòng, cùng loại (văn bản đề nghị / trích lục), cùng tệp gốc, trang nối tiếp."""
    out: list[dict] = []
    for item in attachments:
        prev = out[-1] if out else None
        doan, doan_truoc = _mot_doan(item), _mot_doan(prev)
        if (
            prev is not None and doan and doan_truoc
            and item.get("target") == prev.get("target") == "fixed-slot"
            and item.get("detectedType") == prev.get("detectedType")
            and item.get("detectedType") in _GOP_DUOC
            and item.get("slotIndex") == prev.get("slotIndex")
            and doan["fileIndex"] == doan_truoc["fileIndex"]
            and doan["pageIndexes"][0] == doan_truoc["pageIndexes"][-1] + 1
        ):
            prev["sourceSegments"] = [{"fileIndex": doan["fileIndex"],
                                       "pageIndexes": [*doan_truoc["pageIndexes"], *doan["pageIndexes"]]}]
            continue
        out.append(dict(item))
    return out


async def plan(files: list[FileItem], options: dict | None = None, session: dict | None = None) -> dict:
    # Extension không cắt được trang (trợ lý bản cũ) → đính nguyên tệp, không chia.
    if (options or {}).get("supportsSourceSegments") is False:
        return await plan_without_split(files, options, session)
    result = await _chia_trang(plan_without_split, files, options, session)
    result["attachments"] = gop_doan_lien_trang(result.get("attachments") or [])
    return result
