"""Tư pháp form cũ (DVCQG wizard 4 bước, tờ khai trong iframe tokhaidientu): chủ hồ sơ → tờ khai → đính kèm."""
from app.channels.handfree.chat.resume.base import ResumeAdapter, Step, merge_fields

# Nút chuyển bước ở màn chủ hồ sơ: dẫn từng bước (guided_steps.OWNER) và nút sang Kê khai của tư pháp cũ
# (field_review.OWNER_PHASE).
_OWNER_PHASES = ("owner", "field_review_owner")


class TuPhapCuAdapter(ResumeAdapter):
    family = "tu-phap"
    steps = (
        Step("owner", "owner", "owner_filling", "owner_fields_ready"),
        Step("declaration", "process", "filling", "fields_ready"),
        Step("attach", "attach", "attaching", "attach_ready"),
    )

    # ── Chủ hồ sơ: kế hoạch điền (đã gồm câu trả lời vòng hỏi chủ hồ sơ) + bản cán bộ sửa tay đọc lúc bấm sang bước
    # sau. Điền lại với overwrite=False nên ô cổng đã có sẵn giá trị được giữ, chỉ ô còn trống được điền.
    def decorate(self, conv: dict, reply) -> None:
        specs = [{k: v for k, v in f.items() if k not in ("value", "overwrite")} for f in conv.get("owner_fields") or []]
        for action in reply.actions:
            if action.get("type") == "guided_click_next" and action.get("phase") in _OWNER_PHASES and specs:
                action["readOwnerFields"] = specs

    def observe(self, conv: dict, intent) -> None:
        # Nút chuyển bước dẫn từng bước gửi ô kèm guided_next; nút sang Kê khai của tư pháp cũ gửi kèm báo cáo bấm.
        payload = intent.payload if intent.kind == "action" and isinstance(intent.payload, dict) else {}
        if (intent.value not in ("guided_step_report", "guided_next") or payload.get("phase") not in _OWNER_PHASES
                or not isinstance(payload.get("ownerFields"), dict)
                or (intent.value == "guided_step_report" and not payload.get("ok"))):
            return
        values = {key: (raw.get("value") if isinstance(raw, dict) else raw)
                  for key, raw in payload["ownerFields"].items()}
        keys = [f.get("key") for f in conv.get("owner_fields") or [] if f.get("key")]
        # Chỉ giữ khi đủ mọi ô chủ hồ sơ — đọc thiếu ô là bộ dò không thấy, lưu vào là điền lại thiếu.
        if keys and all(str(values.get(key) or "").strip() for key in keys):
            conv["owner_edited"] = {key: values[key] for key in keys}

    def capture_owner(self, conv: dict, saved: dict, fids: list[str]) -> dict | None:
        if not (conv.get("owner_fields") and conv.get("owner_fields_dispatched")):
            return None
        return {"fields": conv["owner_fields"], "match": conv.get("owner_match") or {},
                "authorization_match": conv.get("authorization_match") or {},
                "edited": conv.get("owner_edited") or saved.get("edited") or {}}

    def apply_owner(self, conv: dict, data: dict, resume: dict) -> None:
        edited = data.get("edited") or {}
        fields = [{**f, "value": edited[f["key"]]} if f.get("key") in edited else f for f in data["fields"]]
        conv.update({
            "owner_fields": fields, "owner_edited": edited, "owner_match": data.get("match") or {"matched": False},
            "authorization_match": data.get("authorization_match") or {}, "owner_errors": [],
            "owner_fields_dispatched": False, "pipeline_status": "owner_fields_ready", "pipeline_error": "",
        })

    # ── Tờ khai: bản trợ lý điền + câu trả lời vòng bổ sung ô (cộng dồn: vòng hỏi đặt lại sau mỗi lần điền).
    # `request_id` nối ảnh chụp form của lượt điền này (store.set_declaration_snapshot) vào bản ghi.
    def capture_declaration(self, conv: dict, saved: dict, fids: list[str]) -> dict | None:
        if not (conv.get("fields") and conv.get("fields_dispatched")):
            return None
        answers = {a["key"]: a for a in saved.get("answers") or [] if a.get("key")}
        for answer in (conv.get("field_review") or {}).get("history") or []:
            if answer.get("key"):
                answers[answer["key"]] = {"key": answer["key"], "value": answer.get("value")}
        return {"fields": conv["fields"], "extracted": conv.get("extracted") or {},
                "request_id": conv.get("trace_request_id") or "", "answers": list(answers.values())}

    def apply_declaration(self, conv: dict, data: dict, resume: dict) -> None:
        snapshot = resume.get("snapshot") or {}
        edited = snapshot.get("fields") if snapshot.get("request_id") == data.get("request_id") else []
        conv.update({
            "fields": merge_fields(data["fields"], data.get("answers") or [], edited or []),
            "extracted": data.get("extracted") or {}, "trace_request_id": data.get("request_id") or None,
            "fields_dispatched": False, "pipeline_status": "fields_ready", "pipeline_error": "",
        })

    # ── Đính kèm: kế hoạch (tệp → dòng thành phần) cùng chế độ gộp/tách và bản nén. Kế hoạch trỏ tệp theo thứ tự
    # trong phiên giấy tờ nên chỉ dùng lại khi danh sách tệp còn y như lúc lập; công dân thêm/bớt giấy thì lập lại.
    def capture_attach(self, conv: dict, saved: dict, fids: list[str]) -> dict | None:
        if not conv.get("attach_plan"):
            return None
        plan_id = conv.get("attach_trace_request_id") or ""
        return {
            "plan": conv["attach_plan"], "plan_id": plan_id,
            "fids": saved["fids"] if saved.get("plan_id") == plan_id and saved.get("fids") else fids,
            "split_documents": conv.get("attach_plan_split_documents"),
            "attach_mode": conv.get("attach_plan_attach_mode"),
            "stt1_virtual": conv.get("attach_plan_stt1_virtual"),
            "replace_files": conv.get("attach_plan_replace_files"),
            "errors": conv.get("attach_errors") or [],
        }

    def usable(self, step: Step, data: dict, fids: list[str]) -> bool:
        return step.key != "attach" or data.get("fids") == fids

    def apply_attach(self, conv: dict, data: dict, resume: dict) -> None:
        conv.update({
            "attach_plan": data["plan"], "attach_trace_request_id": data.get("plan_id") or None,
            "attach_plan_split_documents": data.get("split_documents"),
            "attach_plan_attach_mode": data.get("attach_mode"),
            "attach_plan_stt1_virtual": data.get("stt1_virtual"),
            "attach_plan_replace_files": data.get("replace_files"),
            "attach_errors": data.get("errors") or [], "attach_fail_streak": 0,
            "attach_action_in_progress": False, "attach_action_dispatch_id": "", "attach_action_lease_until": None,
            "pipeline_status": "attach_ready", "pipeline_error": "",
        })
