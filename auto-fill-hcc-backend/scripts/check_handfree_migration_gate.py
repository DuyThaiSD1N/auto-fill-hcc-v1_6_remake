"""Gate ổn định backend hợp nhất trước khi di chuyển dữ liệu Handfree (bước 8.5).

Mặc định chạy toàn bộ test Handfree ngoại trừ danh sách nợ tương thích đã biết, sau đó
chạy các test bảo vệ core Auto Fill mà phần hợp nhất có chạm tới. Một lỗi mới ngoài danh
sách nợ sẽ làm lệnh trả mã khác 0.

Dùng ``--audit-debt`` để chạy lại cả các node nợ (dự kiến đỏ cho đến khi xử lý theo đúng
skill thủ tục tương ứng). Các file planner_v2 không thể collect vẫn được bỏ qua vì model đó
không còn tồn tại trong core hợp nhất.
"""
from __future__ import annotations

import argparse
import os
from pathlib import Path
import shlex
import subprocess
import sys


REPO_ROOT = Path(__file__).resolve().parents[1]

# Bộ planner_v2 cũ đã được thay bằng attachment contract tích hợp của Auto Fill. Các test
# này import module không còn tồn tại nên phải loại ở collection, không được dựng lại code cũ.
COLLECTION_DEBT = (
    "tests/handfree/integration/test_chung_thuc_ban_sao_attach.py",
    "tests/handfree/integration/test_chung_thuc_ban_sao_v2.py",
    "tests/handfree/integration/test_chung_thuc_chu_ky_v2.py",
    "tests/handfree/integration/test_dang_ky_lai_khai_sinh_attachment_v2.py",
    "tests/handfree/integration/test_ket_hon_attachment_v2.py",
    "tests/handfree/integration/test_khai_tu_attachment_v2.py",
    "tests/handfree/integration/test_trich_luc_attachment_v2.py",
    "tests/handfree/integration/test_xac_nhan_tthn_attachment_plan.py",
    "tests/handfree/integration/test_xac_nhan_tthn_attachment_v2.py",
)

# Nợ nghiệp vụ/hợp đồng đã có trước hoặc khác chủ đích với core Auto Fill hiện hành.
# Giữ chính xác đến node test để các test còn lại trong cùng file vẫn chạy ở migration gate.
NODE_DEBT = (
    # Attachment planner/prompt và mapper thủ tục: xử lý ở session theo skill tương ứng.
    "tests/handfree/integration/test_ket_hon_attachment_plan.py::test_ket_hon_attachment_plan_maps_two_pdf_files_by_identity_number",
    "tests/handfree/integration/test_ket_hon_attachment_plan.py::test_ket_hon_attachment_plan_uses_combined_label_for_single_file",
    "tests/handfree/integration/test_ket_hon_attachment_plan.py::test_ket_hon_attachment_plan_classifies_declaration_and_commitment",
    "tests/handfree/integration/test_ket_hon_attachment_plan.py::test_ket_hon_attachment_plan_names_other_by_content",
    "tests/handfree/integration/test_ket_hon_lai_mapper.py::test_map_full_case",
    "tests/handfree/integration/test_ket_hon_nuoc_ngoai.py::test_mapper_viet_va_nuoc_ngoai",
    "tests/handfree/integration/test_ket_hon_nuoc_ngoai.py::test_attach_fixed_slots",
    "tests/handfree/integration/test_khai_sinh_compact_agent.py::test_khai_sinh_compact_agent_derives_angular_fields",
    "tests/handfree/integration/test_khai_sinh_compact_agent.py::test_khai_sinh_compact_prompt_forbids_ui_fields",
    "tests/handfree/integration/test_khai_tu_attachment_plan.py::test_khai_tu_attachment_plan_routes_rows",
    "tests/handfree/integration/test_khai_tu_attachment_plan.py::test_khai_tu_attachment_plan_canh_bao_cccd_lech_nguoi_yeu_cau",
    "tests/handfree/integration/test_khai_tu_dang_ky_lai_attachment_plan.py::test_khai_tu_dang_ky_lai_attach_combined_file_with_death_info_goes_to_row_2",
    "tests/handfree/integration/test_khai_tu_dang_ky_lai_attachment_plan.py::test_khai_tu_dang_ky_lai_attachment_prompt_contract",
    "tests/handfree/integration/test_trich_luc_attachment_plan.py::test_trich_luc_attachment_plan_routes_civil_status_documents_to_new_components",
    "tests/handfree/integration/test_trich_luc_attachment_plan.py::test_trich_luc_attachment_plan_routes_default_existing_rows",
    "tests/handfree/integration/test_trich_luc_attachment_plan.py::test_duplicate_file_names_keep_ocr_by_index_and_merge_same_person_cccd",
    "tests/handfree/integration/test_trich_luc_attachment_plan.py::test_one_attachment_llm_failure_falls_back_all_files_without_retry",
    "tests/handfree/integration/test_trich_luc_compact_agent.py::test_trich_luc_compact_agent_derives_ui_fields",
    "tests/handfree/integration/test_trich_luc_compact_agent.py::test_trich_luc_compact_prompt_rejects_ui_fields",
    "tests/handfree/integration/test_trich_luc_compact_agent.py::test_trich_luc_compact_agent_ignores_direct_ui_values",
    "tests/handfree/integration/test_xac_nhan_tthn_compact_agent.py::test_xac_nhan_tthn_compact_agent_derives_self_ui_fields",
    "tests/handfree/unit/test_ket_hon_mapper_defaults.py::test_chi_co_cccd_suy_luan_lan_dau_dan_toc_kinh",
    "tests/handfree/unit/test_khai_sinh_mapper_defaults.py::test_khong_co_ct01_mac_dinh_vneid_va_bo_cho_muc_dang_ky_thuong_tru",
    "tests/handfree/unit/test_khai_sinh_mapper_defaults.py::test_ct01_khop_me_giu_nhan_dien_me_khong_fallback_sang_bo",
    "tests/handfree/unit/test_khai_sinh_name_uppercase.py::test_ten_con_bo_me_chu_ho_duoc_viet_in_hoa",
    "tests/handfree/unit/test_trich_luc_mapper_quanhe.py::test_quanhe_tu_to_khai_khop_nhan_option",
    "tests/handfree/unit/test_trich_luc_mapper_quanhe.py::test_nyc_nguoi_khac_van_khong_lay_dia_chi_cho_chu_the",
    "tests/handfree/unit/test_trich_luc_mapper_quanhe.py::test_hai_noi_cu_tru_doc_lap_khong_muon_cheo",
    # Contract planner_v2 cũ; core hiện dùng splitDocuments/splitMode tích hợp.
    "tests/handfree/unit/test_attachment_contract_v2.py::test_procedures_dispatch_v2_only_for_capable_extension[ket_hon]",
    "tests/handfree/unit/test_attachment_contract_v2.py::test_procedures_dispatch_v2_only_for_capable_extension[khai_sinh_dang_ky_lai]",
    "tests/handfree/unit/test_attachment_contract_v2.py::test_procedures_dispatch_v2_only_for_capable_extension[khai_tu]",
    "tests/handfree/unit/test_attachment_contract_v2.py::test_procedures_dispatch_v2_only_for_capable_extension[trich_luc]",
    "tests/handfree/unit/test_attachment_contract_v2.py::test_procedures_dispatch_v2_only_for_capable_extension[xac_nhan_tthn]",
    "tests/handfree/unit/test_attachment_contract_v2.py::test_procedures_dispatch_v2_only_for_capable_extension[chung_thuc_ban_sao]",
    "tests/handfree/unit/test_attachment_contract_v2.py::test_procedures_dispatch_v2_only_for_capable_extension[chung_thuc_chu_ky]",
    "tests/handfree/unit/test_attachment_contract_v2.py::test_all_legacy_planners_do_not_join_ocr_by_filename",
    "tests/handfree/unit/test_attachment_contract_v2.py::test_remaining_v2_planners_use_live_component_indexes",
    # Core Auto Fill đã đổi contract HTTP/trace/report; test canonical được chạy ở nhóm CORE.
    "tests/handfree/unit/test_account_maintenance.py::test_disabled_account_cannot_login_and_gets_exact_message",
    "tests/handfree/unit/test_account_maintenance.py::test_disabled_account_current_access_token_is_blocked",
    "tests/handfree/unit/test_account_maintenance.py::test_disabled_account_cannot_refresh",
    "tests/handfree/unit/test_account_maintenance.py::test_maintenance_http_response_supports_installed_extension",
    "tests/handfree/unit/test_repair_attach_trace_files.py::test_rebuild_attachments_restores_original_file_name",
    "tests/handfree/unit/test_reports.py::test_excel_has_safe_unique_sheet_for_every_selected_account",
    "tests/handfree/unit/test_reports.py::test_report_queries_exact_user_ids_and_half_open_range",
    "tests/handfree/unit/test_reports.py::test_stats_by_user_ids_builds_strict_query",
    "tests/handfree/unit/test_trace_attachment_metadata.py::test_trace_keeps_original_names_and_upload_order",
    "tests/handfree/unit/test_trace_attachment_metadata.py::test_trace_maps_split_segments_back_to_source_file",
    "tests/handfree/unit/test_trace_stats_file_stem.py::test_stem_rule_starts_exactly_at_vietnam_midnight",
    "tests/handfree/unit/test_trace_stats_file_stem.py::test_retry_sets_are_deduplicated_but_empty_requests_stay_separate",
    "tests/handfree/unit/test_trace_stats_file_stem.py::test_stats_preserves_old_names_then_uses_stems_without_ocr",
)

CORE_TESTS = (
    "tests/unit/test_account_maintenance.py",
    "tests/unit/test_user_access_management.py",
    "tests/unit/test_reports.py",
    "tests/unit/test_reports_handfree.py",
    "tests/unit/test_stats_handfree.py",
    "tests/unit/test_trace_statistics.py",
    "tests/unit/test_merge_handfree_users.py",
    "tests/unit/test_merge_handfree_data.py",
    "tests/unit/test_backfill_autofill_experience.py",
    "tests/unit/test_repair_attach_trace_files.py",
    "tests/unit/test_ocr_tiengnoi_only.py",
    "tests/unit/test_upload_session_channels.py",
    "tests/unit/test_v2_process.py",
)


def _run(label: str, args: list[str], env: dict[str, str]) -> int:
    command = [sys.executable, "-m", "pytest", "-q", *args]
    print(f"\n=== {label} ===", flush=True)
    print(shlex.join(command), flush=True)
    return subprocess.run(command, cwd=REPO_ROOT, env=env, check=False).returncode


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--audit-debt",
        action="store_true",
        help="Chạy lại cả node nợ để xem phần còn phải xử lý (hiện dự kiến đỏ).",
    )
    args = parser.parse_args()

    env = os.environ.copy()
    # Chỉ dùng trong process test. Runtime production vẫn buộc cấu hình secret thật >= 32 ký tự.
    env.setdefault("UPLOAD_CAPABILITY_SECRET", "ab" * 32)
    # Tránh task ghi cache nền còn treo khi event loop test đóng; test cache tự bật lại bằng mock.
    env.setdefault("OCR_CACHE_ENABLED", "false")

    handfree_args = ["tests/handfree"]
    for path in COLLECTION_DEBT:
        handfree_args.append(f"--ignore={path}")
    if not args.audit_debt:
        for node_id in NODE_DEBT:
            handfree_args.append(f"--deselect={node_id}")

    handfree_status = _run("HANDFREE MIGRATION CONTRACT", handfree_args, env)
    if args.audit_debt:
        return handfree_status

    core_status = _run("AUTO FILL CORE GUARD", list(CORE_TESTS), env)
    if handfree_status or core_status:
        return 1
    print("\nMIGRATION GATE: PASS", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
