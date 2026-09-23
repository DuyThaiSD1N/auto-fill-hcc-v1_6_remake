"""Dẫn công dân qua từng bước wizard của cổng bằng nút bấm ngay trong khung chat.

Luồng CŨ để công dân tự tìm nút "Bước tiếp theo" ở cuối trang cổng — người lớn tuổi hay kẹt ở
đó. Luồng này đặt nút trong sidebar, trợ lý kiểm tra rồi bấm hộ.

Tương thích: bật khi CẢ HAI cùng đồng ý — thủ tục khai `guidedSteps.enabled` VÀ extension khai
`supportsGuidedSteps`. Bản extension trên chợ không khai cờ → mọi nhánh ở đây tắt, flow.py chạy
đúng câu chữ cũ. Vì vậy file này chỉ DỰNG dữ liệu (chip/action/danh sách ô thiếu); câu thoại vẫn
gọi `_fmt(vi.GUIDED_*)` bên flow.py để hàng rào kiểm bản Mông soi được.
"""

from app.channels.handfree.chat import script_vi as vi

# Tên pha do backend đặt, đi theo chip/action ra FE rồi quay về trong báo cáo. Không dùng số
# bước ở đây: số bước là chuyện của cổng (registry.wizard), pha là chuyện của hội thoại.
OWNER = "owner"
ATTACHMENT = "attachment"
RESULT = "result"


def config(proc: dict | None) -> dict:
    return (proc or {}).get("guidedSteps") or {}


def enabled(conv: dict, proc: dict | None) -> bool:
    if not config(proc).get("enabled"):
        return False
    return (conv.get("client_capabilities") or {}).get("supportsGuidedSteps") is True


def owner_scan_enabled(conv: dict, proc: dict | None) -> bool:
    """Quét giấy tờ ngay ở bước chủ hồ sơ. Gác bằng CỜ RIÊNG, không dùng ownerInfo.enabled
    của registry: cờ đó cũng bật cho extension cũ, mà bản cũ nhận giấy ở bước 1 xong sẽ kẹt
    (thủ tục attach-only không có bước kê khai để đi tiếp)."""
    if not config(proc).get("ownerScan"):
        return False
    return (conv.get("client_capabilities") or {}).get("supportsOwnerScan") is True


def needs_scan_at_owner_step(page_context: dict | None) -> bool:
    """Còn ô bắt buộc nào trống thì quét giấy để tự điền; đủ hết rồi thì đừng bắt công dân
    quét lại ở bước này — cứ để giấy tờ sang bước Thành phần hồ sơ.

    Nhánh ủy quyền tự rơi vào vế "còn thiếu" mà không cần luật riêng: bốn ô của khối
    "Thông tin ủy quyền cá nhân" luôn trống khi trang vừa mở.
    """
    form = (page_context or {}).get("ownerForm")
    if not isinstance(form, dict):
        # Client chưa đọc được trạng thái ô (frame lạ, bản FE cũ) → cứ quét như trước,
        # thà hỏi thừa còn hơn bỏ qua rồi để công dân ngồi gõ tay.
        return True
    return int(form.get("missing") or 0) > 0


def docs_for_target(conv: dict, proc: dict | None, target: str) -> list[dict] | None:
    """Checklist giấy tờ THEO BƯỚC, hoặc None để dùng nguyên `requiredDocs` của registry.

    Ở bước Thông tin chủ hồ sơ, công dân đưa thêm CĂN CƯỚC để trợ lý điền form — thứ đó không
    phải giấy đem đi chứng thực. Sang bước Thành phần hồ sơ thì ô đó hết nghĩa, phải rút đi,
    nếu không là bảo công dân đưa lại thứ họ vừa đưa.
    """
    cfg = config(proc)
    extra = (
        cfg.get("authorizationStepDocs") if conv.get("authorization_page")
        else cfg.get("ownerStepDocs")
    ) or []
    if not extra or not owner_scan_enabled(conv, proc):
        return None
    base = list((proc or {}).get("requiredDocs") or [])
    return [*extra, *base] if target == "owner" else base


def _step_docs(proc: dict | None) -> list[dict]:
    cfg = config(proc)
    return [*(cfg.get("ownerStepDocs") or []), *(cfg.get("authorizationStepDocs") or [])]


def owner_doc_keys(proc: dict | None) -> set[str]:
    """Khóa của các ô chỉ dùng để ĐIỀN FORM (không phải giấy đem đi chứng thực)."""
    return {
        str(doc.get("key") or "")
        for doc in _step_docs(proc)
        if doc.get("key") and doc.get("certifiedInto")
    }


def authorization_doc_key(proc: dict | None) -> str:
    """Ô giấy ủy quyền — giấy này KHÔNG đem đi chứng thực, nó đính vào ô riêng ở bước 1."""
    for doc in config(proc).get("authorizationStepDocs") or []:
        if str(doc.get("key") or "").startswith("giay_uy_quyen"):
            return str(doc["key"])
    return ""


def certified_slot_moves(proc: dict | None) -> list[tuple[str, str]]:
    """(ô điền form → ô giấy cần chứng thực) khi công dân chọn chứng thực luôn giấy đó.

    Ô "căn cước của chủ hồ sơ" bị rút khỏi checklist ở bước sau; tệp nằm lại trong ô đã rút
    thì công dân không còn thấy để xem hay xoá. Chọn chứng thực tức là nó đã thành giấy đem
    đi chứng thực thật → chuyển hẳn sang ô kia cho đúng bản chất.
    """
    # Hai nhánh (tự làm / ủy quyền) khai CÙNG khóa ô căn cước, chỉ khác tên hiển thị → phải
    # khử trùng, không thì chạy lệnh chuyển ô hai lần cho cùng một việc.
    moves: list[tuple[str, str]] = []
    for doc in _step_docs(proc):
        source = str(doc.get("key") or "")
        target = str(doc.get("certifiedInto") or "")
        if source and target and (source, target) not in moves:
            moves.append((source, target))
    return moves


def step_labels(proc: dict | None) -> dict[str, str]:
    """Nhãn ĐÚNG CHỮ trên cổng để câu thoại và nút đọc lại được cho công dân đối chiếu."""
    cfg = config(proc)
    return {
        "attachment_step": cfg.get("attachmentStepLabel") or "Thành phần hồ sơ",
        "result_step": cfg.get("resultStepLabel") or "Thông tin nhận kết quả",
        "submit_label": cfg.get("submitLabel") or "Gửi hồ sơ",
    }


def owner_required_fields(proc: dict | None) -> list[dict]:
    """Hợp đồng để FE đọc ĐÚNG ô trên trang — cùng bộ mô tả mà engine điền chủ hồ sơ đang dùng.

    Đọc từ `ownerInfo.fields` kể cả khi `ownerInfo.enabled` = False: thủ tục attach-only không
    tự điền chủ hồ sơ, nhưng cổng vẫn bắt buộc đúng các ô đó.
    """
    cfg = config(proc)
    groups = (
        (((proc or {}).get("ownerInfo") or {}).get("fields") or {},
         cfg.get("ownerRequiredFields") or []),
        # Bốn ô của khối "Thông tin ủy quyền cá nhân" chỉ có ở nhánh ủy quyền. Cứ khai kèm:
        # trang tự làm không có ô nào khớp nên FE bỏ qua, backend cũng bỏ qua khóa vắng mặt.
        (((proc or {}).get("authorizationInfo") or {}).get("fields") or {},
         cfg.get("authorizationRequiredFields") or []),
    )
    fields = []
    for specs, wanted in groups:
        for source_name in wanted:
            spec = specs.get(source_name)
            if not isinstance(spec, dict):
                continue
            fields.append({
                "key": str(spec.get("key") or source_name),
                "label": str(spec.get("label") or ""),
                "name": str(spec.get("name") or ""),
                "dataE2e": str(spec.get("dataE2e") or ""),
                "sectionLabel": str(spec.get("sectionLabel") or ""),
                "comp": str(spec.get("comp") or "owner-input"),
                "reportLabel": str(spec.get("reportLabel") or spec.get("label") or ""),
            })
    return fields


def missing_owner_labels(proc: dict | None, values: dict | None) -> list[str]:
    """Ô bắt buộc đang để trống, theo tên dễ đọc.

    Ô mà FE KHÔNG tìm thấy trên trang thì vắng khỏi `values` → bỏ qua, không kể là thiếu. Thà
    cho qua rồi để chính cổng chặn, còn hơn chặn oan công dân vì bộ dò của mình không thấy ô.
    """
    values = values if isinstance(values, dict) else {}
    missing = []
    for field in owner_required_fields(proc):
        if field["key"] not in values:
            continue
        raw = values[field["key"]]
        # FE mới trả {value, required}: BẮT BUỘC đọc từ dấu * trên chính trang, không khai
        # cứng ở đây — cùng ô "Địa chỉ chi tiết" có dấu * ở nhánh tự làm nhưng KHÔNG có ở
        # nhánh ủy quyền. FE cũ trả thẳng chuỗi giá trị thì giữ nguyên cách hiểu cũ.
        if isinstance(raw, dict):
            if not raw.get("required"):
                continue
            raw = raw.get("value")
        if not str(raw or "").strip():
            missing.append(field["reportLabel"])
    return missing


def _cta(label: str, send: str) -> dict:
    # cta=True: FE dựng nút to tràn ngang thay vì chip thường. FE cũ không đọc khóa này,
    # nhưng nó cũng không bao giờ nhận được chip này (chưa khai capability).
    return {"label": label, "send": send, "solid": True, "cta": True}


def owner_cta_chip(proc: dict | None) -> dict:
    """Nút chuyển bước ở màn chủ hồ sơ; FE đọc giá trị các ô rồi mới gửi để backend hậu kiểm."""
    return {
        **_cta(vi.GUIDED_OWNER_CTA, "__action:guided_next"),
        "phase": OWNER,
        "collect": "ownerFields",
        "fields": owner_required_fields(proc),
    }


def attach_cta_chip() -> dict:
    return {**_cta(vi.GUIDED_ATTACH_CTA, "__action:guided_next"), "phase": ATTACHMENT}


def submit_cta_chip() -> dict:
    return {**_cta(vi.GUIDED_SUBMIT_CTA, "__action:guided_submit"), "phase": RESULT}


def certify_identity_chips() -> list[dict]:
    """Hỏi RIÊNG thẻ căn cước: nó được quét để điền form, chưa chắc là giấy cần chứng thực."""
    return [
        {"label": vi.GUIDED_CERTIFY_YES_CTA, "send": "__action:certify_identity:yes", "solid": True},
        {"label": vi.GUIDED_CERTIFY_NO_CTA, "send": "__action:certify_identity:no"},
    ]


def cta_chip_for(proc: dict | None, phase: str) -> dict | None:
    """Dựng lại đúng nút vừa bấm để công dân thử lại sau khi cổng chặn."""
    if phase == OWNER:
        return owner_cta_chip(proc)
    if phase == ATTACHMENT:
        return attach_cta_chip()
    if phase == RESULT:
        return submit_cta_chip()
    return None


def _wizard(proc: dict | None, name: str, default: int) -> int:
    value = ((proc or {}).get("wizard") or {}).get(name, default)
    return value if isinstance(value, int) and value > 0 else default


def click_next_action(proc: dict | None, phase: str) -> dict:
    """Bấm nút chuyển bước của cổng, rồi đối chiếu số bước để biết trang có chuyển thật không."""
    expect = (
        _wizard(proc, "attachmentStep", 3) if phase == OWNER
        else _wizard(proc, "resultStep", 4)
    )
    return {"type": "guided_click_next", "phase": phase, "expectStep": expect}


def submit_action(proc: dict | None) -> dict:
    return {"type": "guided_submit", "label": step_labels(proc)["submit_label"]}


def is_result_step(proc: dict | None, page_context: dict | None) -> bool:
    step = (page_context or {}).get("wizardStep")
    return isinstance(step, int) and step == _wizard(proc, "resultStep", 4)
