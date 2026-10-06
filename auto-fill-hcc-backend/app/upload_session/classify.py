"""Phân loại ảnh giấy tờ REALTIME khi người dân chụp (docs/05 §2).

Mặc định: OCR raw → phân loại tất định theo từ khóa fold dấu. Thủ tục đăng ký dùng
engine OCR/LLM chung sẽ được dispatch theo procedure_key, còn key/prompt nằm trong
pipeline riêng của thủ tục.
Ảnh không nhận ra → doc_key=None, mobile cho người dân chọn tay (hint doc_key khi chụp
theo từng dòng checklist được ƯU TIÊN nếu OCR không phủ quyết).
"""
import asyncio
import json
import re
import unicodedata

from app.pipelines._shared.documents import representative_excerpt
from app.services import ocr
from app.upload_session import classifier_registry, llm_classifier


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
        return hint_doc_key, None, "theo lựa chọn của công dân (OCR chưa nhận ra)"
    # Có slot "Giấy tờ khác" → xếp vào đó thay vì từ chối.
    if free("khac"):
        return "khac", None, "xếp vào Giấy tờ khác"
    return None, None, "chưa nhận ra loại giấy tờ"


def _slot_free(key: str, required_docs: list[dict], files: list[dict]) -> bool:
    doc = next((d for d in required_docs if d.get("key") == key), None)
    if not doc:
        return False
    if doc.get("repeatable"):
        return True
    return sum(1 for f in files if f.get("doc_key") == key) < int(doc.get("sides") or 1)


# Thủ tục CHƯA có bộ phân loại riêng (upload_classification.py) chỉ có bộ từ khoá chung ở trên —
# vốn chỉ biết giấy hộ tịch/CCCD. Giấy tờ chuyên ngành (đơn xin phép xây dựng, bản vẽ, sổ đỏ…) vì
# thế rơi hết vào "Giấy tờ khác". Tệp nào bộ từ khoá KHÔNG nhận ra thì hỏi LLM theo chính TÊN các ô
# trong checklist của thủ tục: không phải viết prompt riêng cho từng thủ tục.
_SLOT_NAME_SYSTEM_PROMPT = """
Bạn là bộ phân loại giấy tờ cho một thủ tục hành chính. Mỗi yêu cầu chỉ chứa OCR của ĐÚNG MỘT
tệp và danh sách các ô giấy tờ của thủ tục. Chọn đúng một doc_key mà tệp này thuộc về, dựa
vào TIÊU ĐỀ và BẢN CHẤT của tài liệu (không dựa vào việc tài liệu nhắc tới giấy tờ khác: đơn
đề nghị vẫn là đơn dù có ghi số sổ đỏ hay số căn cước bên trong).
Tài liệu không thuộc ô nào → doc_key của ô "giấy tờ khác" nếu danh sách có, không thì "unknown".
OCR trống hoặc quá thiếu để xác định an toàn → "unknown". Không dùng tên tệp làm bằng chứng.
Chỉ trả JSON object đúng schema, không giải thích: {"doc_key":"..."}
""".strip()


def _slot_name_spec(required_docs: list[dict]) -> llm_classifier.ClassificationSpec:
    slots = [{"doc_key": d["key"], "ten_o": str(d.get("name") or "")} for d in required_docs]

    def build_user_prompt(_file_name: str, text: str) -> str:
        compact = representative_excerpt(text, 5000)
        return json.dumps({"cacO": slots, "ocrText": compact}, ensure_ascii=False)

    return llm_classifier.ClassificationSpec(
        system_prompt=_SLOT_NAME_SYSTEM_PROMPT,
        allowed_keys=frozenset(d["key"] for d in required_docs),
        build_user_prompt=build_user_prompt,
    )


async def _classify_by_slot_names(payload_files: list[dict], ocr_results: list[dict],
                                  infos: list[dict], required_docs: list[dict],
                                  hint_doc_key: str | None, procedure_key: str) -> dict[int, str]:
    """{chỉ số tệp: doc_key} cho các tệp bộ từ khoá không nhận ra. Rỗng = giữ luồng cũ.

    Chỉ chạy khi: biết thủ tục, công dân KHÔNG chụp theo dòng cụ thể (hint thắng), và checklist
    có ít nhất một ô chuyên ngành ngoài "khác"/CCCD — không thì chẳng có gì để phân biệt.
    """
    if not procedure_key or hint_doc_key:
        return {}
    named_slots = [d for d in required_docs
                   if d.get("key") != "khac" and not str(d.get("key") or "").startswith("cccd")]
    if not named_slots:
        return {}
    # Từ khoá chung có nhận ra loại nhưng checklist không có ô cho loại đó (vd đơn xin phép xây
    # dựng có cụm "cam đoan" → cam_doan) thì vẫn rơi xuống "khác" — tệp đó cũng phải hỏi LLM.
    pending = [
        index for index, result in enumerate(ocr_results)
        if (result.get("text") or "").strip() and index < len(payload_files)
        and (not infos[index].get("doc_type")
             or route_to_slot(infos[index], required_docs, [], None)[0] in (None, "khac"))
    ]
    if not pending:
        return {}
    spec = _slot_name_spec(required_docs)
    keys = await asyncio.gather(*(
        llm_classifier._classify_one(payload_files[index], ocr_results[index], spec)
        for index in pending
    ))
    return {index: key for index, key in zip(pending, keys) if key}


async def classify_files(payload_files: list[dict], required_docs: list[dict],
                         existing_files: list[dict], hint_doc_key: str | None,
                         procedure_key: str = "",
                         context: dict | None = None) -> list[dict]:
    """OCR + phân loại 1 lô ảnh. Map kết quả theo THỨ TỰ MẢNG (không tin index nào khác).

    → [{doc_key, side, note, ocr_ok}] cùng độ dài payload_files.
    """
    # Checklist chỉ có MỘT nhóm thì mọi tệp chắc chắn thuộc nhóm đó; quy tắc dựa hoàn toàn
    # trên cấu hình phiên nên engine không cần biết tên thủ tục và không gọi OCR/LLM dư thừa.
    if len(required_docs) == 1:
        doc_key = required_docs[0]["key"] if required_docs else "khac"
        return [
            {"doc_key": doc_key, "side": None,
             "note": "một loại giấy tờ duy nhất", "ocr_ok": False}
            for _ in payload_files
        ]

    registered = classifier_registry.get_upload_classifier(procedure_key)
    if registered:
        # Pipeline tự đăng ký key/prompt/fallback trong upload_classification.py. Engine
        # chung không cần biết tên hoặc key giấy tờ của bất kỳ thủ tục cụ thể nào.
        procedure_fallback = registered.fallback_to_slot

        def fallback(text: str, acc: list[dict]):
            if procedure_fallback:
                return procedure_fallback(text, required_docs, acc, hint_doc_key)
            return route_to_slot(classify_text(text), required_docs, acc, hint_doc_key)

        return await llm_classifier.classify_files(
            payload_files, required_docs, existing_files, registered.spec, fallback,
            context,
        )

    # Phân loại realtime vẫn dùng provider duy nhất Tiếng Nói, với giới hạn token ngắn.
    ocr_results = await ocr.ocr_per_file(payload_files, classify=True)
    infos = [classify_text(r.get("text") or "") for r in ocr_results]
    by_slot_name = await _classify_by_slot_names(
        payload_files, ocr_results, infos, required_docs, hint_doc_key, procedure_key,
    )
    out = []
    # files tích lũy dần trong lô: ảnh sau biết ảnh trước đã chiếm ô nào.
    acc = list(existing_files)
    for index, r in enumerate(ocr_results):
        info = infos[index]
        named = by_slot_name.get(index)
        if named and _slot_free(named, required_docs, acc):
            doc_key, side, note = named, None, "LLM theo tên ô checklist"
        else:
            doc_key, side, note = route_to_slot(info, required_docs, acc, hint_doc_key)
        item = {"doc_key": doc_key, "side": side, "note": note, "ocr_ok": bool(r.get("text"))}
        out.append(item)
        if doc_key:
            acc.append({"doc_key": doc_key, "side": side})
    return out
