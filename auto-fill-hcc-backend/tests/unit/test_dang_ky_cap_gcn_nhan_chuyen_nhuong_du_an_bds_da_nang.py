"""[Đà Nẵng] Đăng ký, cấp GCN cho người nhận chuyển nhượng trong dự án BĐS — detect khoá host."""

from app.procedures.registry import public_list

_KEY = "dang-ky-cap-gcn-nhan-chuyen-nhuong-du-an-bat-dong-san"


def test_registry_detect_khoa_host_da_nang_khong_de_ban_lao_cai():
    entries = {p["key"]: p for p in public_list()}
    assert entries[_KEY]["detect"]["urlScope"] == ["dichvucong.danang.gov.vn"]
    lao_cai = entries["dang-ky-cap-gcn-nhan-chuyen-nhuong-du-an-bat-dong-san-lao-cai"]
    assert "dichvucong.danang.gov.vn" not in lao_cai["detect"].get("urlScope", [])
