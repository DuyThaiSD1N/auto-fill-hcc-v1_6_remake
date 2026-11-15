"""Ô cơ quan cấp giấy tờ tùy thân của các tờ khai tư pháp form mới (Cổng DVC quốc gia): chốt lại theo ngày cấp, tên Cục
ghi dạng viết tắt."""
from pathlib import Path

import pytest

from app.pipelines._shared.compact_agent.issuer import (
    ISSUER_BO_CONG_AN,
    ISSUER_CUC,
    issuer_by_issue_date,
    normalize_issuer,
    short_issuer,
)

PIPELINES = Path(__file__).resolve().parents[2] / "app" / "pipelines"


@pytest.mark.parametrize("ngay_cap, expected", [
    ("01/07/2024", ISSUER_BO_CONG_AN),   # đúng mốc Luật Căn cước có hiệu lực
    ("16/05/2025", ISSUER_BO_CONG_AN),
    ("30/06/2024", ISSUER_CUC),
    ("02/07/2021", ISSUER_CUC),
    ("2025", ISSUER_CUC),                # không đủ ngày/tháng/năm thì không đủ căn cứ đổi
    ("", ISSUER_CUC),
])
def test_cuc_in_san_tren_to_khai_chot_lai_theo_ngay_cap(ngay_cap, expected):
    assert issuer_by_issue_date(normalize_issuer("Cục CSQLHC về TTXH"), ngay_cap) == expected


def test_chi_doi_mot_chieu_va_khong_dung_co_quan_khac():
    assert issuer_by_issue_date(ISSUER_BO_CONG_AN, "02/07/2021") == ISSUER_BO_CONG_AN
    assert issuer_by_issue_date("Công an tỉnh A", "16/05/2025") == "Công an tỉnh A"
    assert issuer_by_issue_date("", "16/05/2025") == ""


@pytest.mark.parametrize("raw", ["cục quản lý trái tự xã hội", "cục quản lý và trật tự xã hội",
                                 "Cục Cảnh sát quản lý hành chính về trật tự xã hội", "Cục CSQLHC về TTXH"])
def test_ten_cuc_doc_lech_van_nhan_ra(raw):
    assert normalize_issuer(raw) == ISSUER_CUC


def test_co_quan_khac_khong_bi_nhan_nham_la_cuc():
    assert normalize_issuer("Công an tỉnh A") == "Công an tỉnh A"
    assert normalize_issuer("Sở Lao động - Thương binh và Xã hội") == "Sở Lao động - Thương binh và Xã hội"


def test_ten_cuc_ghi_dang_viet_tat():
    assert short_issuer(ISSUER_CUC) == "Cục Cảnh sát QLHC về TTXH"
    assert short_issuer(normalize_issuer("CỤC TRƯỞNG CỤC CẢNH SÁT QUẢN LÝ HÀNH CHÍNH VỀ TRẬT TỰ XÃ HỘI")) == "Cục Cảnh sát QLHC về TTXH"
    assert short_issuer(ISSUER_BO_CONG_AN) == ISSUER_BO_CONG_AN and short_issuer("") == ""


@pytest.mark.parametrize("package", [
    "xac_nhan_tthn_dvc_moi", "trich_luc_dvc_moi", "cai_chinh_dvc_moi", "khai_sinh_dvc_moi", "khai_tu_dvcqg"])
def test_nam_to_khai_tu_phap_form_moi_deu_chot_o_co_quan_cap(package):
    source = (PIPELINES / package / "process" / "mapper.py").read_text(encoding="utf-8")
    # Chốt theo ngày cấp phải đứng TRƯỚC chỗ suy loại giấy tờ để loại thẻ đi cùng cơ quan cấp.
    checked = source.index("issuer = issuer_by_issue_date(issuer, issue_date)")
    assert checked < source.index("_id_doc_type_with_number(", source.index("def enrich("))
    assert "short_issuer(issuer))" in source
