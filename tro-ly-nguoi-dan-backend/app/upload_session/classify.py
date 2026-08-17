"""Phân loại ảnh giấy tờ REALTIME khi người dân chụp (docs/05 §2).

Chiến lược: OCR (provider raw — nhanh) → phân loại TẤT ĐỊNH theo từ khóa fold dấu.
KHÔNG dùng LLM ở đây: 3 loại giấy tờ khai sinh phân biệt được chắc chắn bằng keyword,
và tất định thì không dính bug index LLM (memory llm-classify-index-order-mapping).
Ảnh không nhận ra → doc_key=None, mobile cho người dân chọn tay (hint doc_key khi chụp
theo từng dòng checklist được ƯU TIÊN nếu OCR không phủ quyết).
"""
import re
import unicodedata

from app.services import ocr


def _fold(s: str) -> str:
    s = unicodedata.normalize("NFD", str(s or ""))
    s = "".join(ch for ch in s if unicodedata.category(ch) != "Mn")
    return re.sub(r"\s+", " ", s.replace("Đ", "D").replace("đ", "d")).strip().lower()


def classify_text(text: str) -> dict:
    """→ {doc_type: 'cccd'|'chung_sinh'|None, side: 'front'|'back'|None, gender: 'nam'|'nu'|None}"""
    t = _fold(text)
    out: dict = {"doc_type": None, "side": None, "gender": None}
    if not t:
        return out

    if "giay chung sinh" in t or ("chung sinh" in t and "so" in t):
        out["doc_type"] = "chung_sinh"
        return out

    # Tờ khai xét TRƯỚC giấy hộ tịch: "Tờ khai cấp bản sao trích lục..." cũng chứa "trích lục".
    if "to khai" in t and ("ket hon" in t or "dang ky" in t or "ban sao" in t or "trich luc" in t):
        out["doc_type"] = "to_khai"
        return out
    if "cam doan" in t:
        out["doc_type"] = "cam_doan"
        return out

    # Giấy báo tử / giấy chứng tử (khai tử). KHÔNG bắt "bao tu" trần — "thông báo từ chối"
    # fold dấu cũng chứa chuỗi đó; nhận theo cụm đầy đủ hoặc nhãn thời điểm tử vong.
    if ("giay bao tu" in t or "giay chung tu" in t or "bao tu so" in t
            or "tu vong luc" in t or "tu vong vao luc" in t or "da chet vao luc" in t):
        out["doc_type"] = "bao_tu"
        return out

    # GCN kết hôn (xét TRƯỚC ho_tich): nguồn thông tin CHA/MẸ cho khai sinh liên thông
    # (slot ket_hon_cha_me), HOẶC giấy hộ tịch gốc cho cấp bản sao (slot ho_tich) — route theo
    # thủ tục. "Tờ khai đăng ký kết hôn" đã bị nhánh to_khai bắt ở trên nên không lọt vào đây.
    if "ket hon" in t and ("chung nhan" in t or "trich luc" in t):
        out["doc_type"] = "ket_hon"
        return out
    # Giấy tờ hộ tịch gốc khác (giấy khai sinh / trích lục khác): cần cấp bản sao.
    if ("giay khai sinh" in t or "khai sanh" in t or "trich luc" in t
            or "trich y so bo" in t):
        out["doc_type"] = "ho_tich"
        return out

    is_cccd = ("can cuoc" in t or "citizen identity" in t or "cuoc cong dan" in t
               or "idvnm" in t)
    if is_cccd:
        out["doc_type"] = "cccd"
        # Mặt sau: MRZ IDVNM / nơi cấp / đặc điểm nhận dạng — mặt trước: họ tên + ngày sinh.
        if "idvnm" in t or "cuc truong" in t or "dac diem nhan dang" in t or "cuc canh sat" in t:
            out["side"] = "back"
        elif "ho va ten" in t or "full name" in t or "ngay sinh" in t or "date of birth" in t:
            out["side"] = "front"
        m = re.search(r"gioi tinh[^a-z]*(nam|nu)", t)
        if m:
            out["gender"] = m.group(1)
    return out


def route_to_slot(info: dict, required_docs: list[dict], files: list[dict],
                  hint_doc_key: str | None) -> tuple[str | None, str | None, str]:
    """Gán ảnh vào ô checklist → (doc_key, side, note).

    Ưu tiên: (1) giới tính trên CCCD (nam→cha, nữ→mẹ — tất định); (2) hint từ nút chụp
    theo dòng; (3) ô CCCD còn thiếu (mặt sau không có tên/giới tính → gán ô thiếu kế tiếp).
    """
    keys = {d["key"] for d in required_docs}
    counts = {d["key"]: sum(1 for f in files if f.get("doc_key") == d["key"]) for d in required_docs}
    sides = {d["key"]: d["sides"] for d in required_docs}
    repeatable = {d["key"] for d in required_docs if d.get("repeatable")}

    def free(key: str) -> bool:
        return key in keys and (key in repeatable or counts.get(key, 0) < sides.get(key, 0))

    if info["doc_type"] == "chung_sinh":
        if free("chung_sinh"):
            return "chung_sinh", None, ""
        if "chung_sinh" in keys:
            return None, None, "Giấy chứng sinh đã đủ"
        # Thủ tục không có slot chứng sinh riêng (vd nhận cha mẹ con) → rơi xuống
        # nhánh chung cuối hàm (hint / "khác") như các loại khác.

    if info["doc_type"] == "cccd":
        # Slot CCCD theo GIỚI TÍNH — generic cho mọi thủ tục: khai sinh (cccd_cha/cccd_me),
        # kết hôn (cccd_nam/cccd_nu)... — khớp theo hậu tố key, không hardcode thủ tục.
        cccd_keys = [d["key"] for d in required_docs if d["key"].startswith("cccd")]
        if cccd_keys:  # thủ tục CÓ ô CCCD riêng → route theo giới tính / ô còn thiếu
            male_key = next((k for k in cccd_keys if any(t in k for t in ("cha", "nam", "chong"))), None)
            female_key = next((k for k in cccd_keys if any(t in k for t in ("_me", "_nu", "vo"))), None)
            if info["gender"] == "nam" and male_key and free(male_key):
                return male_key, info["side"] or "front", ""
            if info["gender"] == "nu" and female_key and free(female_key):
                return female_key, info["side"] or "front", ""
            if hint_doc_key and free(hint_doc_key):
                return hint_doc_key, info["side"], ""

            # Một thủ tục chỉ có một nhóm CCCD thì không cần suy đoán vai trò.
            if len(cccd_keys) == 1 and free(cccd_keys[0]):
                return cccd_keys[0], info["side"], "CCCD theo nhóm duy nhất"

            # Ảnh mặt sau thường không có giới tính. Ghép nó với ảnh mặt trước vừa
            # nhận để không dồn tất cả CCCD repeatable vào nhóm của cha.
            if info["side"] == "back":
                for uploaded in reversed(files):
                    key = uploaded.get("doc_key")
                    if key in cccd_keys and uploaded.get("side") == "front" and free(key):
                        return key, "back", "CCCD mặt sau theo mặt trước liền trước"

            # Giữ cách lấp ô cũ cho các thủ tục có slot CCCD hữu hạn. Với nhiều
            # slot repeatable, CCCD chưa rõ cha/mẹ phải rơi xuống "khác" thay vì
            # luôn bị gán vào slot đầu tiên.
            if not any(key in repeatable for key in cccd_keys):
                for key in cccd_keys:
                    if free(key):
                        return key, info["side"] or "back", "gán theo ô còn thiếu"
                return None, info["side"], "Các ô CCCD đã đủ"
        # Thủ tục KHÔNG có ô CCCD riêng (vd đăng ký lại khai sinh: CCCD dồn vào "Giấy tờ khác")
        # → rơi xuống hint/"khac" cuối hàm như loại chưa nhận ra.

    # GCN kết hôn → slot cha/mẹ (khai sinh liên thông) HOẶC slot ho_tich (cấp bản sao).
    if info["doc_type"] == "ket_hon":
        for key in ("ket_hon_cha_me", "ho_tich"):
            if key in keys and free(key):
                return key, None, ""
        # slot đã đủ / thủ tục không có → rơi xuống hint/"khác" cuối hàm.

    # Tờ khai / bản cam đoan / giấy hộ tịch / giấy báo tử → slot cùng tên nếu thủ tục có
    # khai; không có slot thì rơi xuống hint/"khác" như loại chưa nhận ra.
    if info["doc_type"] in ("to_khai", "cam_doan", "ho_tich", "bao_tu") and free(info["doc_type"]):
        return info["doc_type"], None, ""

    # Không nhận ra loại → tin hint nếu ô còn trống.
    if hint_doc_key and free(hint_doc_key):
        return hint_doc_key, None, "theo lựa chọn của bà con (OCR chưa nhận ra)"
    # Có slot "Giấy tờ khác" → xếp vào đó thay vì từ chối.
    if free("khac"):
        return "khac", None, "xếp vào Giấy tờ khác"
    return None, None, "chưa nhận ra loại giấy tờ"


async def classify_files(payload_files: list[dict], required_docs: list[dict],
                         existing_files: list[dict], hint_doc_key: str | None,
                         procedure_key: str = "") -> list[dict]:
    """OCR + phân loại 1 lô ảnh. Map kết quả theo THỨ TỰ MẢNG (không tin index nào khác).

    → [{doc_key, side, note, ocr_ok}] cùng độ dài payload_files.
    """
    # Thủ tục attach-only chỉ có MỘT loại nhận lặp (vd Chứng thực bản sao): mọi tệp chắc chắn
    # thuộc cùng loại nên gán thẳng bằng logic. Tuyệt đối không gọi OCR/LLM gây chậm vô ích.
    single_copy_certification = procedure_key == "chung-thuc-ban-sao"
    single_repeatable = len(required_docs) == 1 and required_docs[0].get("repeatable")
    if single_copy_certification or single_repeatable:
        # Khóa theo procedure_key để cả phiên đã tạo trước lúc thêm cờ repeatable vẫn đúng.
        doc_key = required_docs[0]["key"] if required_docs else "khac"
        return [
            {"doc_key": doc_key, "side": None,
             "note": "một loại giấy tờ duy nhất", "ocr_ok": False}
            for _ in payload_files
        ]

    # ÉP provider raw (Google Vision): classify realtime chỉ cần text nhanh để bắt keyword —
    # không ép thì cờ OCR_BY_TIENGNOI kéo sang vintern batch (GPU chậm + timeout dài),
    # điện thoại phải chờ lâu mới thấy "đã nhận" từng ảnh.
    ocr_results = await ocr.ocr_per_file(payload_files, provider="raw")
    out = []
    # files tích lũy dần trong lô: ảnh sau biết ảnh trước đã chiếm ô nào.
    acc = list(existing_files)
    for r in ocr_results:
        info = classify_text(r.get("text") or "")
        doc_key, side, note = route_to_slot(info, required_docs, acc, hint_doc_key)
        item = {"doc_key": doc_key, "side": side, "note": note, "ocr_ok": bool(r.get("text"))}
        out.append(item)
        if doc_key:
            acc.append({"doc_key": doc_key, "side": side})
    return out
