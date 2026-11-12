"""Đính kèm cho thủ tục đăng ký khai sinh (liên thông).

Form bước đính kèm có thể có tới 2 ô (2 dòng):
  STT1 (luôn có): Giấy chứng sinh — hoặc văn bản người làm chứng xác nhận việc sinh, hoặc
                  giấy cam đoan về việc sinh.
  STT2 (tùy trường hợp): Tờ khai thay đổi thông tin cư trú (mẫu CT01) — khi trẻ không ở cùng
                  bố/mẹ/người giám hộ.
OCR + phân loại để tìm ĐÚNG từng file trong số file người dùng tải lên, rồi gắn vào đúng ô theo
vị trí (slotIndex 0 = chứng sinh, slotIndex 1 = tờ khai cư trú). Các giấy tờ "other" (CCCD cha/mẹ,
giấy kết hôn…) KHÔNG bị bỏ qua và KHÔNG gộp thành 1 PDF: mỗi tệp là một item repeatUpload cùng
trỏ ô STT1 để FE đính NHIỀU TỆP RỜI vào cùng hàng giấy chứng sinh (trang cho phép nhiều tệp/hàng).

Cấu hình theo tài khoản (planner không biết tài khoản nên router (Auto Fill) và pipeline_runner
(Handfree) gọi ``with_khai_sinh_attach_options`` để server tự đặt cờ, client không gửi được):
  - phường Nghĩa Lộ (Quảng Ngãi) — cờ ``omitBirthDeclaration``: KHÔNG đính Tờ khai đăng ký khai
    sinh; các giấy tờ khác vẫn đính như thường.
  - phường Song Liễu (Bắc Ninh) — cờ ``onlyBirthProof``: CHỈ đính Giấy chứng sinh (hoặc văn bản
    người làm chứng / giấy cam đoan về việc sinh) vào STT1; tờ khai khai sinh, tờ khai cư trú
    CT01, CCCD, giấy kết hôn… vẫn dùng để OCR điền form nhưng không đính.
Tài khoản khác: không có cờ, hành vi giữ y hệt.

Nén tệp trên 2 MB như 4 thủ tục Cổng DVC quốc gia mới (dùng chung ``shrink_oversized`` của
cai_chinh_dvc_moi): bản nén trả ở ``replaceFiles`` để extension đính thay bản gốc; OCR vẫn đọc bản gốc.
Cổng còn chặn TỔNG mỗi dòng 2,6 MB → ``_fit_slot_budget`` nén tiếp các tệp cùng dòng cho tổng lọt ngân sách.
"""
import asyncio
import base64
import re
import time
import unicodedata
from typing import Any

from app.config import settings
from app.pipelines.cai_chinh_dvc_moi.attach.dinh_kem_khong_tach.planner import (
    _SHRINK_LADDER,
    _decode,
    _level_label,
    _render_pdf,
    shrink_merged,
    shrink_oversized,
)
from app.pipelines.khai_sinh_lien_thong.attach import prompt
from app.process.schemas import FileItem
from app.services import ocr
from app.services.llm import client

_OCR_TYPES = {"image/jpeg", "image/png", "image/jpg", "application/pdf"}

_BIRTH_PROOF_LABEL = "Giấy chứng sinh"
_RESIDENCE_FORM_LABEL = "Tờ khai thay đổi thông tin cư trú"


def _fold(value: str) -> str:
    text = unicodedata.normalize("NFD", value or "")
    text = "".join(ch for ch in text if unicodedata.category(ch) != "Mn")
    return re.sub(r"\s+", " ", text.replace("Đ", "D").replace("đ", "d")).strip().lower()


PROCEDURE_KEY = "khai-sinh-dang-ky"
OMIT_BIRTH_DECLARATION_OPTION = "omitBirthDeclaration"
OMITTED_DECLARATION_NOTE = "Không đính kèm Tờ khai đăng ký khai sinh theo cấu hình phường Nghĩa Lộ"
ONLY_BIRTH_PROOF_OPTION = "onlyBirthProof"
ONLY_BIRTH_PROOF_NOTE = "Chỉ đính kèm Giấy chứng sinh theo cấu hình phường Song Liễu, không đính"

_WARD_PREFIXES = ("xa ", "phuong ", "thi tran ")


def _account_area(user: dict | None) -> tuple[str, str]:
    """(tỉnh, xã) của tài khoản đã bỏ dấu; xã bỏ tiền tố Xã/Phường/Thị trấn."""
    if not user:
        return "", ""
    tinh = _fold(user.get("tinh") or "")
    xa = _fold(user.get("xa") or "")
    for prefix in _WARD_PREFIXES:
        if xa.startswith(prefix):
            xa = xa[len(prefix):].strip()
            break
    return tinh, xa


def is_quang_ngai_nghia_lo(user: dict | None) -> bool:
    """True khi tài khoản thuộc phường Nghĩa Lộ, tỉnh Quảng Ngãi.

    Lào Cai cũng có Phường Nghĩa Lộ nên bắt buộc khớp tỉnh; xã khớp ĐÚNG tên sau khi bỏ tiền tố.
    """
    tinh, xa = _account_area(user)
    return "quang ngai" in tinh and xa == "nghia lo"


def is_bac_ninh_song_lieu(user: dict | None) -> bool:
    """True khi tài khoản thuộc phường Song Liễu, tỉnh Bắc Ninh (khớp cả tỉnh, xã đúng tên)."""
    tinh, xa = _account_area(user)
    return "bac ninh" in tinh and xa == "song lieu"


def with_khai_sinh_attach_options(options: dict | None, user: dict | None, procedure: str) -> dict:
    """Trả bản sao options với các cờ đính kèm khai sinh do server quyết theo tài khoản.

    Luôn gỡ cờ client gửi lên trước: chỉ tài khoản đúng địa bàn mới có cờ.
    """
    result = dict(options or {})
    result.pop(OMIT_BIRTH_DECLARATION_OPTION, None)
    result.pop(ONLY_BIRTH_PROOF_OPTION, None)
    if procedure != PROCEDURE_KEY:
        return result
    if is_quang_ngai_nghia_lo(user):
        result[OMIT_BIRTH_DECLARATION_OPTION] = True
    if is_bac_ninh_song_lieu(user):
        result[ONLY_BIRTH_PROOF_OPTION] = True
    return result


def _is_birth_declaration_text(text: str) -> bool:
    """Tờ khai đăng ký khai sinh (bản giấy) — nhận theo tiêu đề mẫu.

    Phải xét TRƯỚC ``_is_birth_proof_text``: tờ khai có câu "Tôi cam đoan ... khai sinh" nên rule
    chứng sinh (cam đoan + sinh) sẽ nhận nhầm nó là giấy cam đoan về việc sinh.
    """
    return bool(re.search(r"to khai dang k[yi] khai sinh", _fold(text)))


# Mấy ô chỉ có trên mẫu giấy chứng sinh — còn lại khi OCR mất tiêu đề "GIẤY CHỨNG SINH" (nhất là
# bản scan ghép nhiều giấy). Tờ khai đăng ký khai sinh không có các ô này.
_BIRTH_FORM_MARKERS = ("ma so gcs", "nguoi do de", "so con trong lan sinh")


def _has_birth_form_markers(text: str) -> bool:
    folded = _fold(text)
    return any(marker in folded for marker in _BIRTH_FORM_MARKERS)


def _is_birth_proof_text(text: str) -> bool:
    """Rule fallback khi LLM lỗi/không chắc: nhận diện giấy chứng sinh / người làm chứng / cam đoan."""
    folded = _fold(text)
    if "chung sinh" in folded:  # "giấy chứng sinh"
        return True
    if _has_birth_form_markers(text):
        return True
    if "lam chung" in folded and "sinh" in folded:  # văn bản người làm chứng xác nhận việc sinh
        return True
    if "cam doan" in folded and "sinh" in folded:  # giấy cam đoan về việc sinh
        return True
    return False


def _is_residence_form_text(text: str) -> bool:
    """Rule fallback: nhận diện Tờ khai thay đổi thông tin cư trú (mẫu CT01)."""
    folded = _fold(text)
    if "thay doi thong tin cu tru" in folded:
        return True
    if "thay doi noi cu tru" in folded:
        return True
    if "to khai thay doi" in folded and "cu tru" in folded:
        return True
    if "ct01" in folded.replace(" ", ""):  # mã mẫu CT01
        return True
    return False


def _is_explicit_other_text(text: str) -> bool:
    """Khóa các giấy tờ chắc chắn không thuộc 2 ô cố định.

    LLM chỉ là fallback cho tài liệu OCR chưa rõ. Không được để một nhãn LLM sai biến
    CCCD/CMND hoặc giấy kết hôn thành giấy chứng sinh/tờ khai cư trú.
    """
    folded = _fold(text)
    head = folded[:1200]
    is_identity_card = (
        ("identity card" in head or "citizen identity card" in head)
        and ("full name" in head or "personal identification number" in head or "so / no" in head)
    ) or (
        ("can cuoc cong dan" in head or re.search(r"\bcan cuoc\b", head))
        and ("ho va ten" in head or "ho, chu dem va ten khai sinh" in head or "so / no" in head)
    )
    is_identity_paper = "chung minh nhan dan" in head or "passport" in head or "ho chieu" in head
    is_marriage_certificate = "giay chung nhan ket hon" in folded or "chung nhan ket hon" in folded
    return bool(is_identity_card or is_identity_paper or is_marriage_certificate)


# Tên tệp cổng liên thông nhận: chữ (kể cả có dấu), số, dấu cách, "-" (vd "image-5"). Dấu chấm giữa tên,
# "_" và ký tự lạ khác thì cổng báo không cho ký tự đặc biệt (req 12/11: "att.i12b2EYU_TFdy…").
_SAFE_STEM = re.compile(r"^[\w\s-]+$")


def _is_messy_stem(stem: str) -> bool:
    """Tên gốc có ký tự đặc biệt hoặc là chuỗi ngẫu nhiên (mã do Zalo/ứng dụng tự sinh) → phải đặt lại."""
    if not stem or "_" in stem or not _SAFE_STEM.match(stem):
        return True
    for token in re.split(r"[\s-]+", stem):
        has_digit = any(ch.isdigit() for ch in token)
        has_alpha = any(ch.isalpha() for ch in token)
        mixed_case = any(ch.isupper() for ch in token) and any(ch.islower() for ch in token)
        if len(token) >= 20 or (len(token) >= 10 and has_digit and has_alpha and mixed_case):
            return True
    return False


def _original_document_names(raw_files: list[dict], doc_types: dict[int, str] | None = None) -> dict[int, str]:
    """documentName = TÊN FILE GỐC cho mọi tệp, không đặt theo loại giấy.

    Extension (bật đổi tên) đặt tên tệp tải lên theo documentName; nhiều tệp cùng ô STT1 mà cùng
    nhãn "Giấy chứng sinh" thì cổng liên thông chặn trùng TÊN trong dsFile → chỉ giữ tệp đầu.
    Hai file gốc trùng tên cũng bị chặn như vậy nên tệp sau mới thêm số " 2", " 3".
    Bỏ đuôi ".pdf"/".jpg": extension tự gắn lại đuôi của tệp gốc khi tải lên.
    Tên gốc linh tinh (ký tự đặc biệt, chuỗi ngẫu nhiên) cổng không nhận → đặt lại theo loại giấy.
    """
    doc_types = doc_types or {}
    used: set[str] = set()
    names: dict[int, str] = {}
    for idx, f in enumerate(raw_files):
        original = str(f.get("name") or "").strip()
        dot = original.rfind(".")
        stem = (original[:dot] if dot > 0 else original).strip()
        if _is_messy_stem(stem):
            stem = _DOC_TYPE_NAMES.get(doc_types.get(idx, _DOC_OTHER), "Giấy tờ khác")
        name, n = stem, 2
        while _fold(name) in used:
            name = f"{stem} {n}"
            n += 1
        used.add(_fold(name))
        names[idx] = name
    return names


# Loại tài liệu LLM gán cho mỗi file ở bước đính kèm khai sinh.
_DOC_BIRTH = "birth_proof"
_DOC_RESIDENCE = "residence_form"
_DOC_OTHER = "other"
_DOC_DECLARATION = "birth_declaration"  # chỉ gán khi có cờ omitBirthDeclaration

# Tên đặt lại cho tệp có tên gốc linh tinh (xem _original_document_names).
_DOC_TYPE_NAMES = {
    _DOC_BIRTH: _BIRTH_PROOF_LABEL,
    _DOC_RESIDENCE: "Tờ khai thay đổi thông tin cư trú",
    _DOC_DECLARATION: "Tờ khai đăng ký khai sinh",
    _DOC_OTHER: "Giấy tờ khác",
}


# Cổng liên thông chặn TỔNG dung lượng các tệp của MỘT dòng giấy tờ ("không được quá 2.6MB"); từng tệp dưới 2 MB
# vẫn vỡ khi nhiều tệp cùng dòng (req 12/11: 6 tệp ~1 MB cùng dòng chứng sinh). Đích chừa biên cho cả cách tính
# 2.600.000 byte lẫn 2,6 MiB.
SLOT_BUDGET_BYTES = 2_400_000
_BIRTH_WEIGHT = 2  # giấy chứng sinh được phần dung lượng gấp đôi giấy tờ khác: cán bộ cần đọc rõ nhất
_SLOT_LADDER = _SHRINK_LADDER + [(85, 45, True)]  # thêm một nấc sàn cho dòng có nhiều tệp


def _slot_shares(sizes: dict[int, int], weights: dict[int, int], budget: int) -> dict[int, int]:
    """Chia ngân sách của một dòng kiểu "rót nước": tệp nhỏ hơn phần của nó giữ nguyên, phần dư dồn cho tệp lớn.

    Trả {fileIndex: đích byte} chỉ cho các tệp phải nén; rỗng nếu tổng đã lọt ngân sách.
    """
    pending = set(sizes)
    remaining = budget
    while pending:
        total_weight = sum(weights.get(i, 1) for i in pending)
        fits = [i for i in pending if sizes[i] <= remaining * weights.get(i, 1) / total_weight]
        if not fits:
            return {i: int(remaining * weights.get(i, 1) / total_weight) for i in sorted(pending)}
        for i in fits:
            remaining -= sizes[i]
            pending.discard(i)
    return {}


def _shrink_to_limit(file: dict, limit: int) -> dict:
    """Vẽ lại tệp theo `_SLOT_LADDER` tới nấc đầu tiên lọt `limit`; hết thang thì lấy bản nhỏ nhất."""
    raw = _decode(file["dataUrl"])
    best, label = raw, ""
    for dpi, quality, gray in _SLOT_LADDER:
        out = _render_pdf(raw, dpi, quality, gray)
        if len(out) < len(best):
            best, label = out, _level_label(dpi, quality, gray)
        if len(out) <= limit:
            break
    stem = (file["name"].rsplit(".", 1)[0] if "." in file["name"] else file["name"]) or "tai-lieu"
    return {
        "name": f"{stem}.pdf",
        "type": "application/pdf",
        "dataUrl": "data:application/pdf;base64," + base64.b64encode(best).decode(),
        "originalBytes": len(raw),
        "bytes": len(best),
        "level": label,
    }


async def _fit_slot_budget(raw_files: list[dict], attachments: list[dict], replaced: dict[str, dict],
                           errors: list[str]) -> None:
    """Nén các tệp cùng một dòng cho tổng lọt `SLOT_BUDGET_BYTES`; bản nén ghi vào `replaced` (= replaceFiles)."""
    def size(i: int) -> int:
        entry = replaced.get(str(i))
        if entry:
            return entry["bytes"]
        try:
            return len(_decode(raw_files[i]["dataUrl"]))
        except Exception:  # noqa: BLE001 — dataUrl hỏng: không nén được, coi như 0 để không chặn cả dòng
            return 0

    rows: dict[Any, list[dict]] = {}
    for item in attachments:
        rows.setdefault(item.get("slotIndex"), []).append(item)
    for items in rows.values():
        indexes = sorted({
            it["fileIndex"] for it in items
            if isinstance(it.get("fileIndex"), int) and 0 <= it["fileIndex"] < len(raw_files)
            and raw_files[it["fileIndex"]].get("dataUrl")
        })
        sizes = {i: size(i) for i in indexes}
        if sum(sizes.values()) <= SLOT_BUDGET_BYTES:
            continue
        birth = {it["fileIndex"] for it in items if it.get("detectedType") == _BIRTH_PROOF_LABEL}
        weights = {i: _BIRTH_WEIGHT if i in birth else 1 for i in indexes}
        shares = _slot_shares(sizes, weights, SLOT_BUDGET_BYTES)

        async def one(i: int, limit: int) -> None:
            try:
                entry = await asyncio.to_thread(_shrink_to_limit, raw_files[i], limit)
            except Exception as e:  # noqa: BLE001 — nén hỏng thì để nguyên, cổng tự báo nếu từ chối
                errors.append(f"Không nén được {raw_files[i].get('name')}: {e}")
                return
            if entry["bytes"] < size(i):
                replaced[str(i)] = entry

        await asyncio.gather(*(one(i, limit) for i, limit in shares.items()))
        total = sum(size(i) for i in indexes)
        if total > SLOT_BUDGET_BYTES:
            errors.append(
                f"Dòng {items[0].get('slotName') or items[0].get('componentName')} nén hết mức vẫn "
                f"{total / 1e6:.1f} MB, vượt giới hạn 2,6 MB của cổng; cần bớt giấy tờ đính kèm."
            )


async def _classify_with_llm(documents: list[dict[str, Any]]) -> dict[int, str]:
    """Trả về {fileIndex: docType} với docType ∈ {birth_proof, residence_form, other}."""
    if not documents:
        return {}

    messages = [
        {"role": "system", "content": prompt.SYSTEM_PROMPT},
        {"role": "user", "content": prompt.build_user_prompt(documents)},
    ]
    raw = await client.chat(messages, max_tokens=400, enable_thinking=settings.agent_reasoning)
    parsed = client.extract_json_block(raw)
    parsed_docs = parsed.get("documents", []) or []
    out: dict[int, str] = {}

    def _norm(item: dict) -> str:
        dt = _fold(str(item.get("docType", "")))
        if dt in (_DOC_BIRTH, _DOC_RESIDENCE):
            return dt
        return _DOC_OTHER

    # `index` là định danh file trong request, không phải vị trí của item trong output.
    # LLM có thể sắp xếp lại kết quả theo loại; map theo thứ tự sẽ gán nhãn của giấy
    # chứng sinh cho CCCD đứng đầu danh sách. Index thiếu/sai thì bỏ item để caller
    # giữ `other`, không đoán theo vị trí.
    valid = {d["index"] for d in documents}
    for item in parsed_docs:
        try:
            idx = int(item.get("index"))
        except Exception:  # noqa: BLE001
            continue
        if idx in valid:
            out[idx] = _norm(item)
    return out


async def plan_khai_sinh_attachments(
    files: list[FileItem],
    options: dict | None = None,
    session: dict | None = None,
) -> dict:
    omit_declaration = (options or {}).get(OMIT_BIRTH_DECLARATION_OPTION) is True
    only_birth_proof = (options or {}).get(ONLY_BIRTH_PROOF_OPTION) is True
    errors: list[str] = []
    raw_files = [{"name": f.name, "type": f.type, "dataUrl": f.dataUrl} for f in files]
    ocr_files = [f for f in raw_files if f.get("type") in _OCR_TYPES]

    t0 = time.monotonic()
    shrink_task = asyncio.create_task(shrink_oversized(raw_files, errors))
    ocr_results = await ocr.ocr_per_file(ocr_files) if ocr_files else []
    ocr_ms = int((time.monotonic() - t0) * 1000)
    for r in ocr_results:
        if r.get("error"):
            errors.append(f"OCR {r.get('name')}: {r['error']}")

    ocr_by_name = {r.get("name"): r for r in ocr_results}
    # LLM chạy trước và phân loại TOÀN BỘ file thành một trong 3 loại, gồm `other`.
    # Rule phía dưới chỉ kiểm tra kết quả rõ ràng sai và fallback khi LLM thiếu/trượt.
    llm_docs = [
        {
            "index": idx,
            "fileName": file.get("name"),
            "text": str(ocr_by_name.get(file.get("name"), {}).get("text") or ""),
        }
        for idx, file in enumerate(raw_files)
    ]

    t1 = time.monotonic()
    llm_types: dict[int, str] = {}
    if llm_docs:
        try:
            llm_types = await _classify_with_llm(llm_docs)
        except Exception as e:  # noqa: BLE001
            errors.append(f"attachment_agent: {e}")
    llm_ms = int((time.monotonic() - t1) * 1000)

    final_types: dict[int, str] = {}
    classification_sources: dict[int, str] = {}
    for idx, file in enumerate(raw_files):
        text = str(ocr_by_name.get(file.get("name"), {}).get("text") or "")
        llm_type = llm_types.get(idx, _DOC_OTHER)

        # LLM vẫn chạy trước, nhưng nhãn trái hẳn loại giấy tờ rõ ràng phải bị chặn.
        # Đây là validation an toàn, không phải phân loại trước LLM.
        if omit_declaration and _is_birth_declaration_text(text):
            final_types[idx] = _DOC_DECLARATION
            classification_sources[idx] = "rule_omit_declaration"
        elif only_birth_proof and _is_birth_declaration_text(text) and not _has_birth_form_markers(text):
            # Tờ khai có câu "cam đoan ... khai sinh" nên rule chứng sinh nhận nhầm → chỉ đính nó khi
            # là tệp ghép có trang giấy chứng sinh thật (còn ô của mẫu chứng sinh).
            final_types[idx] = _DOC_OTHER
            classification_sources[idx] = "rule_declaration_other"
        elif _is_birth_proof_text(text):
            final_types[idx] = _DOC_BIRTH
            classification_sources[idx] = "rule_fallback" if llm_type != _DOC_BIRTH else "llm"
        elif _is_residence_form_text(text):
            final_types[idx] = _DOC_RESIDENCE
            classification_sources[idx] = "rule_fallback" if llm_type != _DOC_RESIDENCE else "llm"
        elif _is_explicit_other_text(text):
            final_types[idx] = _DOC_OTHER
            classification_sources[idx] = "rule_override_other" if llm_type != _DOC_OTHER else "llm"
        else:
            final_types[idx] = llm_type
            classification_sources[idx] = "llm" if idx in llm_types else "default"

    # Tìm 1 file cho mỗi ô từ kết quả LLM đã được validation. `other` là kết quả bình
    # thường: có thể không tìm thấy một hoặc cả hai loại đích, tuyệt đối không ép gán.
    # MỌI tệp giấy chứng sinh (kể cả tệp ghép có giấy chứng sinh, sinh đôi nhiều giấy) → STT1, MỌI tờ
    # khai cư trú → STT2. Chỉ lấy tệp đầu thì tệp cùng loại thứ hai rơi xuống "other": chứng sinh có
    # thể bị dời sang STT2, tờ khai cư trú lại vào STT1.
    birth_indices = [i for i in range(len(raw_files)) if final_types[i] == _DOC_BIRTH]
    residence_indices = [i for i in range(len(raw_files)) if final_types[i] == _DOC_RESIDENCE]
    birth_index = birth_indices[0] if birth_indices else None
    residence_index = residence_indices[0] if residence_indices else None

    attachments: list[dict] = []
    document_names = _original_document_names(raw_files, final_types)
    declaration_indices = [i for i in range(len(raw_files)) if final_types[i] == _DOC_DECLARATION]
    for idx in declaration_indices:
        errors.append(f"{OMITTED_DECLARATION_NOTE}: {raw_files[idx]['name']}")

    # STT1 nhận giấy chứng sinh + mọi giấy tờ khác (CCCD cha/mẹ, giấy kết hôn… = "other").
    # Trang liên thông CHO ĐÍNH NHIỀU FILE vào 1 hàng: input #fileDinhKem KHÔNG có `multiple`
    # (change handler chỉ đọc files[0] rồi `dsFile.push` — tích lũy từng file, chặn trùng TÊN)
    # → KHÔNG gộp thành 1 PDF nữa. Phát MỖI file MỘT item `repeatUpload` cùng trỏ ô STT1 để FE
    # mở menu "Chọn tệp tin" nhiều lần, thêm từng tệp RỜI vào cùng hàng chứng sinh.
    # Chưa có giấy chứng sinh vẫn đính các giấy tờ khác vào STT1 (hồ sơ không mất phần đã có),
    # kèm lời nhắc bổ sung giấy chứng sinh.
    other_indices = [
        i for i in range(len(raw_files))
        if i not in birth_indices and i not in residence_indices and i not in declaration_indices
    ]
    # Song Liễu (cờ onlyBirthProof): chỉ giấy chứng sinh vào STT1. Giấy tờ khác và tờ khai cư trú
    # không đính (vẫn đã dùng để OCR điền form); chưa có chứng sinh thì không đính gì.
    only_omitted_indices: list[int] = []
    if only_birth_proof:
        only_omitted_indices = sorted(other_indices + residence_indices)
        other_indices, residence_indices = [], []
        if only_omitted_indices:
            errors.append(
                f"{ONLY_BIRTH_PROOF_NOTE}: " + ", ".join(raw_files[i]["name"] for i in only_omitted_indices)
            )
    stt1_indices = birth_indices + other_indices
    for idx in stt1_indices:  # chứng sinh trước, rồi các giấy tờ khác
        f = raw_files[idx]
        item = {
            "fileIndex": idx,
            "fileName": f["name"],
            "documentName": document_names[idx],
            "componentName": _BIRTH_PROOF_LABEL,
            "target": "fixed-slot",
            "slotIndex": 0,            # STT1: giấy chứng sinh (nhận nhiều tệp rời)
            "slotKey": "birth_proof",  # FE khớp đúng dòng theo text tên giấy tờ
            "slotName": _BIRTH_PROOF_LABEL,
            "needsAddComponent": False,
            "repeatUpload": True,      # FE mở menu lại cho từng tệp, không gộp
            "detectedType": _BIRTH_PROOF_LABEL if idx in birth_indices else _DOC_OTHER,
        }
        # Cổng chặn TỔNG dung lượng mỗi loại giấy tờ ("không được quá 2.6MB"), nên dồn hết
        # giấy tờ khác vào STT1 sẽ vỡ hạn mức khi hồ sơ có nhiều tệp. Chỉ giấy tờ KHÁC mới
        # được phép rơi sang STT2 — giấy chứng sinh phải nằm đúng ô của nó, không bao giờ
        # được dời. FE chỉ dùng ô này KHI cổng thật sự báo quá dung lượng.
        if idx not in birth_indices:
            item["fallbackSlotIndex"] = 1
            item["fallbackSlotKey"] = "residence_form"
            item["fallbackSlotName"] = _RESIDENCE_FORM_LABEL
        attachments.append(item)
    if not birth_indices:
        errors.append(
            "Không tìm thấy giấy chứng sinh (hoặc văn bản người làm chứng/giấy cam đoan về việc sinh) "
            "trong các file đã tải lên"
            + ("; đã đính các giấy tờ khác vào ô giấy chứng sinh, cần bổ sung giấy chứng sinh." if other_indices else ".")
        )

    for idx in residence_indices:
        f = raw_files[idx]
        item = {
            "fileIndex": idx,
            "fileName": f["name"],
            "documentName": document_names[idx],
            "componentName": _RESIDENCE_FORM_LABEL,
            "target": "fixed-slot",
            "slotIndex": 1,            # STT2: tờ khai thay đổi thông tin cư trú (tùy trường hợp)
            "slotKey": "residence_form",  # FE khớp đúng dòng theo text tên giấy tờ
            "slotName": _RESIDENCE_FORM_LABEL,
            "needsAddComponent": False,
            "detectedType": _RESIDENCE_FORM_LABEL,
        }
        if len(residence_indices) > 1:
            item["repeatUpload"] = True  # nhiều tờ khai → thêm từng tệp rời vào cùng hàng STT2
        attachments.append(item)

    # "other" luôn gộp vào STT1 → matched; mọi tệp đều có chỗ, skipped thường rỗng.
    matched = set(birth_indices) | set(residence_indices)
    matched.update(other_indices)
    matched.update(declaration_indices)  # đã có ghi chú riêng, không báo "bỏ qua"
    matched.update(only_omitted_indices)  # như trên (cấu hình Song Liễu)
    skipped_names = [rf["name"] for i, rf in enumerate(raw_files) if i not in matched]
    if skipped_names:
        errors.append(
            "Bỏ qua file: "
            + ", ".join(skipped_names)
        )

    replace_files = await shrink_task
    await _fit_slot_budget(raw_files, attachments, replace_files, errors)
    # Không có tệp ghép nên chỉ đổi fileName theo bản nén (ảnh → .pdf).
    await shrink_merged(raw_files, attachments, replace_files, errors)

    return {
        "attachments": attachments,
        "replaceFiles": replace_files or None,
        "extracted": {
            "documents": [f["name"] for f in raw_files],
            "ocrDocuments": [r.get("name") for r in ocr_results if r.get("text")],
            "llmDocuments": [doc["fileName"] for doc in llm_docs],
            "classified": [
                {
                    "fileName": file["name"],
                    "docType": final_types[idx],
                    "source": classification_sources[idx],
                }
                for idx, file in enumerate(raw_files)
            ],
            "birthProof": raw_files[birth_index]["name"] if birth_index is not None else None,
            "residenceForm": raw_files[residence_index]["name"] if residence_index is not None else None,
            "skipped": skipped_names,
            "omittedDeclarations": [raw_files[i]["name"] for i in declaration_indices],
            "onlyBirthProofOmitted": [raw_files[i]["name"] for i in only_omitted_indices],
            "shrunk": [
                {"fileName": r["name"], "originalBytes": r["originalBytes"], "bytes": r["bytes"], "level": r["level"]}
                for r in replace_files.values()
            ],
            "sessionId": (session or {}).get("request_id"),
        },
        "stats": {
            "ocr_latency_ms": ocr_ms,
            "llm_latency_ms": llm_ms,
            "total_latency_ms": ocr_ms + llm_ms,
        },
        "errors": errors,
    }


# Entrypoint thống nhất cho registry app.pipelines.<procedure>.attach.
plan = plan_khai_sinh_attachments
