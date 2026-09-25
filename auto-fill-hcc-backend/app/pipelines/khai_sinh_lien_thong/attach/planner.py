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

Cấu hình theo tài khoản: phường Nghĩa Lộ (Quảng Ngãi) KHÔNG đính Tờ khai đăng ký khai sinh; các
giấy tờ khác vẫn đính như thường. Planner không biết tài khoản nên router (Auto Fill) và
pipeline_runner (Handfree) gọi ``with_nghia_lo_attach_options`` để server tự đặt cờ
``omitBirthDeclaration``. Tài khoản khác: không có cờ, hành vi giữ y hệt.
"""
import re
import time
import unicodedata
from typing import Any

from app.config import settings
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

_WARD_PREFIXES = ("xa ", "phuong ", "thi tran ")


def is_quang_ngai_nghia_lo(user: dict | None) -> bool:
    """True khi tài khoản thuộc phường Nghĩa Lộ, tỉnh Quảng Ngãi.

    Lào Cai cũng có Phường Nghĩa Lộ nên bắt buộc khớp tỉnh; xã khớp ĐÚNG tên sau khi bỏ tiền tố.
    """
    if not user:
        return False
    tinh = _fold(user.get("tinh") or "")
    xa = _fold(user.get("xa") or "")
    for prefix in _WARD_PREFIXES:
        if xa.startswith(prefix):
            xa = xa[len(prefix):].strip()
            break
    return "quang ngai" in tinh and xa == "nghia lo"


def with_nghia_lo_attach_options(options: dict | None, user: dict | None, procedure: str) -> dict:
    """Trả bản sao options với cờ bỏ Tờ khai khai sinh do server quyết theo tài khoản."""
    result = dict(options or {})
    result.pop(OMIT_BIRTH_DECLARATION_OPTION, None)
    if procedure == PROCEDURE_KEY and is_quang_ngai_nghia_lo(user):
        result[OMIT_BIRTH_DECLARATION_OPTION] = True
    return result


def _is_birth_declaration_text(text: str) -> bool:
    """Tờ khai đăng ký khai sinh (bản giấy) — nhận theo tiêu đề mẫu.

    Phải xét TRƯỚC ``_is_birth_proof_text``: tờ khai có câu "Tôi cam đoan ... khai sinh" nên rule
    chứng sinh (cam đoan + sinh) sẽ nhận nhầm nó là giấy cam đoan về việc sinh.
    """
    return bool(re.search(r"to khai dang k[yi] khai sinh", _fold(text)))


def _is_birth_proof_text(text: str) -> bool:
    """Rule fallback khi LLM lỗi/không chắc: nhận diện giấy chứng sinh / người làm chứng / cam đoan."""
    folded = _fold(text)
    if "chung sinh" in folded:  # "giấy chứng sinh"
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


# Loại tài liệu LLM gán cho mỗi file ở bước đính kèm khai sinh.
_DOC_BIRTH = "birth_proof"
_DOC_RESIDENCE = "residence_form"
_DOC_OTHER = "other"
_DOC_DECLARATION = "birth_declaration"  # chỉ gán khi có cờ omitBirthDeclaration


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
    errors: list[str] = []
    raw_files = [{"name": f.name, "type": f.type, "dataUrl": f.dataUrl} for f in files]
    ocr_files = [f for f in raw_files if f.get("type") in _OCR_TYPES]

    t0 = time.monotonic()
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
    birth_index: int | None = None
    residence_index: int | None = None
    for idx in range(len(raw_files)):
        dtype = final_types[idx]
        if birth_index is None and dtype == _DOC_BIRTH:
            birth_index = idx
            continue
        if residence_index is None and dtype == _DOC_RESIDENCE:
            residence_index = idx
            continue

    attachments: list[dict] = []
    other_indices: list[int] = []
    declaration_indices = [i for i in range(len(raw_files)) if final_types[i] == _DOC_DECLARATION]
    for idx in declaration_indices:
        errors.append(f"{OMITTED_DECLARATION_NOTE}: {raw_files[idx]['name']}")

    # STT1 nhận giấy chứng sinh + mọi giấy tờ khác (CCCD cha/mẹ, giấy kết hôn… = "other").
    # Trang liên thông CHO ĐÍNH NHIỀU FILE vào 1 hàng: input #fileDinhKem KHÔNG có `multiple`
    # (change handler chỉ đọc files[0] rồi `dsFile.push` — tích lũy từng file, chặn trùng TÊN)
    # → KHÔNG gộp thành 1 PDF nữa. Phát MỖI file MỘT item `repeatUpload` cùng trỏ ô STT1 để FE
    # mở menu "Chọn tệp tin" nhiều lần, thêm từng tệp RỜI vào cùng hàng chứng sinh.
    if birth_index is not None:
        other_indices = [
            i for i in range(len(raw_files))
            if i not in (birth_index, residence_index) and i not in declaration_indices
        ]
        for idx in (birth_index, *other_indices):  # chứng sinh trước, rồi các giấy tờ khác
            f = raw_files[idx]
            item = {
                "fileIndex": idx,
                "fileName": f["name"],
                "documentName": _BIRTH_PROOF_LABEL,
                "componentName": _BIRTH_PROOF_LABEL,
                "target": "fixed-slot",
                "slotIndex": 0,            # STT1: giấy chứng sinh (nhận nhiều tệp rời)
                "slotKey": "birth_proof",  # FE khớp đúng dòng theo text tên giấy tờ
                "slotName": _BIRTH_PROOF_LABEL,
                "needsAddComponent": False,
                "repeatUpload": True,      # FE mở menu lại cho từng tệp, không gộp
                "detectedType": _BIRTH_PROOF_LABEL if idx == birth_index else _DOC_OTHER,
            }
            # Cổng chặn TỔNG dung lượng mỗi loại giấy tờ ("không được quá 2.6MB"), nên dồn hết
            # giấy tờ khác vào STT1 sẽ vỡ hạn mức khi hồ sơ có nhiều tệp. Chỉ giấy tờ KHÁC mới
            # được phép rơi sang STT2 — giấy chứng sinh phải nằm đúng ô của nó, không bao giờ
            # được dời. FE chỉ dùng ô này KHI cổng thật sự báo quá dung lượng.
            if idx != birth_index:
                item["fallbackSlotIndex"] = 1
                item["fallbackSlotKey"] = "residence_form"
                item["fallbackSlotName"] = _RESIDENCE_FORM_LABEL
            attachments.append(item)
    else:
        errors.append(
            "Không tìm thấy giấy chứng sinh (hoặc văn bản người làm chứng/giấy cam đoan về việc sinh) "
            "trong các file đã tải lên."
        )

    if residence_index is not None:
        f = raw_files[residence_index]
        attachments.append({
            "fileIndex": residence_index,
            "fileName": f["name"],
            "documentName": _RESIDENCE_FORM_LABEL,
            "componentName": _RESIDENCE_FORM_LABEL,
            "target": "fixed-slot",
            "slotIndex": 1,            # STT2: tờ khai thay đổi thông tin cư trú (tùy trường hợp)
            "slotKey": "residence_form",  # FE khớp đúng dòng theo text tên giấy tờ
            "slotName": _RESIDENCE_FORM_LABEL,
            "needsAddComponent": False,
            "detectedType": _RESIDENCE_FORM_LABEL,
        })

    # "other" nay đã gộp vào STT1 → matched. Chỉ còn skip khi KHÔNG có chứng sinh (không có ô để gộp).
    matched = {i for i in (birth_index, residence_index) if i is not None}
    matched.update(other_indices)
    matched.update(declaration_indices)  # đã có ghi chú riêng, không báo "bỏ qua"
    skipped_names = [rf["name"] for i, rf in enumerate(raw_files) if i not in matched]
    if skipped_names:
        errors.append(
            "Bỏ qua file (chưa có giấy chứng sinh làm ô đính kèm): "
            + ", ".join(skipped_names)
        )

    return {
        "attachments": attachments,
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
