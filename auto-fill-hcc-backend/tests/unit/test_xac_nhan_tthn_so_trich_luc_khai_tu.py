# -*- coding: utf-8 -*-
"""XNTTHN — ô "Số/Ngày cấp Giấy chứng tử/Trích lục khai tử/Bản án" phải là của CHÍNH TỜ GIẤY NỘP.

Trích lục khai tử (bản sao) mang HAI cặp số/ngày: số của chính bản trích lục ở đầu trang
("Số: 167/TLKT-BS", cấp ngày 07/11/2024) và số đăng ký khai tử GỐC trong sổ được dẫn chiếu ở
thân giấy ("Đã được đăng ký khai tử tại ... Số: 116 ngày 11/12/2009"). Cổng hỏi số/ngày CẤP của
giấy tờ đang nộp, nên phải lấy cặp ĐẦU TRANG. Prompt cũ bắt lấy cặp đăng ký gốc → extension điền
116 / 11/12/2009, sai so với giấy dân nộp.
"""
from app.pipelines.xac_nhan_tthn.process.mapper import enrich
from app.pipelines.xac_nhan_tthn.process.prompt import EXTRA_RULES


def _run(**kv):
    return {f["name"]: f["value"] for f in enrich([{"name": k, "value": v} for k, v in kv.items()])}


# --------------------------------------------------------------------------------------
# MAPPER — số có hậu tố /TLKT-BS phải đi thẳng ra ô của cổng, không bị cắt
# --------------------------------------------------------------------------------------

def test_so_trich_luc_giu_nguyen_hau_to():
    out = _run(
        DeathCert_Number="167/TLKT-BS",
        DeathCert_Date="07/11/2024",
        DeathCert_Agency="Ủy ban nhân dân xã Nghĩa Thương",
    )
    assert out["TinhTrangHonNhanC1"].startswith("Đã đăng ký kết hôn")
    assert "vợ/chồng đã chết" in out["TinhTrangHonNhanC1"]
    detail = out["nxnLoaiTinhTrangHonNhan=4"]
    assert detail["soBanAnQuyetDinhLyHon"] == "167/TLKT-BS"
    assert detail["ngayCapBanAnQuyetDinhLyHon"] == "07/11/2024"
    assert detail["coQuanCapBanAnQuyetDinhLyHon"] == "Ủy ban nhân dân xã Nghĩa Thương"


# --------------------------------------------------------------------------------------
# PROMPT — luật trích xuất phải trỏ về số/ngày của chính tờ giấy
# --------------------------------------------------------------------------------------

def test_prompt_lay_so_ngay_cua_chinh_to_giay():
    assert "GIẤY ĐANG NỘP" in EXTRA_RULES
    assert "167/TLKT-BS" in EXTRA_RULES
    assert "07/11/2024" in EXTRA_RULES


def test_prompt_khong_con_bat_lay_so_dang_ky_goc():
    """Câu lệnh cũ là nguyên nhân trực tiếp của lỗi — không được quay lại."""
    assert "DeathCert_Number = SỐ ĐĂNG KÝ KHAI TỬ GỐC" not in EXTRA_RULES
    assert "TUYỆT ĐỐI KHÔNG dùng số này" not in EXTRA_RULES
    assert "DeathCert_Date = ngày ĐĂNG KÝ KHAI TỬ GỐC" not in EXTRA_RULES
