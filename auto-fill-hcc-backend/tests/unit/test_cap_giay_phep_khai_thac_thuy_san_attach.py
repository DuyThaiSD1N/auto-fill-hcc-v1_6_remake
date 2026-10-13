"""Cấp, cấp lại Giấy phép khai thác thủy sản — đính kèm không được bỏ tệp nào (bảng chỉ có 2 dòng Đơn)."""

import json

from app.pipelines.cap_giay_phep_khai_thac_thuy_san.attach import planner, prompt


def _files(*names):
    return [{"name": n} for n in names]


def test_tep_gop_co_don_cap_lai_vao_dong_mau_05():
    items, warnings, _ = planner.build_plan_items(_files("gop.pdf"), [], {0: "don_cap_lai"})
    assert [i["componentName"] for i in items] == ["Đơn đề nghị cấp lại theo Mẫu số 05"]
    assert not warnings


def test_giay_phep_cu_va_cccd_di_kem_dong_don_dat_ten_theo_loai():
    llm = {0: "giay_phep_cu", 1: "don_cap_lai", 2: "cccd", 3: "other"}
    items, warnings, classified = planner.build_plan_items(
        _files("gp.pdf", "don.pdf", "cccd.jpg", "tau.pdf"), [], llm
    )
    assert [i["fileIndex"] for i in items] == [0, 1, 2, 3], "không bỏ tệp nào"
    assert {i["componentName"] for i in items} == {"Đơn đề nghị cấp lại theo Mẫu số 05"}
    assert items[0]["documentName"] == "Giấy phép khai thác thủy sản đã cấp"
    assert items[0]["detectedType"] == "giay_phep_cu"
    assert items[2]["documentName"] == "Căn cước công dân"
    assert items[3]["documentName"] == "tau.pdf", "giấy chưa nhận ra loại giữ tên gốc"
    assert items[1]["documentName"].startswith("Đơn đề nghị cấp lại")
    assert all(c.get("routedTo") == "don_cap_lai" for c in classified if c["fileName"] != "don.pdf")
    assert not warnings


def test_khong_co_don_thi_canh_bao_chu_khong_im_lang():
    items, warnings, _ = planner.build_plan_items(_files("gp.pdf", "cccd.jpg"), [], {0: "giay_phep_cu", 1: "cccd"})
    assert items == []
    assert warnings and "gp.pdf" in warnings[0] and "cccd.jpg" in warnings[0]


async def test_llm_tra_thua_phan_tu_theo_trang_chi_lay_phan_tu_dau_cua_index(monkeypatch):
    async def fake_chat(messages, max_tokens, enable_thinking):
        return json.dumps({"documents": [
            {"index": 0, "docType": "don_cap_lai"},
            {"index": 0, "docType": "giay_phep_cu"},
            {"index": 1, "docType": "cccd"},
        ]})

    monkeypatch.setattr(planner.client, "chat", fake_chat)
    assert await planner._classify_with_llm([{"index": 0, "text": "x"}]) == {0: "don_cap_lai"}


def test_prompt_neu_ro_mot_tep_mot_phan_tu_va_tep_gop():
    assert "ĐÚNG MỘT phần tử cho index đó" in prompt.SYSTEM_PROMPT
    assert "Tệp GỘP nhiều giấy" in prompt.SYSTEM_PROMPT


# --- Phần I người nộp: so SỐ CCCD tài khoản cổng với thẻ CCCD vật lý (cách của xoa_dang_ky_tau_ca) ---
from app.pipelines.cap_giay_phep_khai_thac_thuy_san.process import mapper  # noqa: E402

_CHU_TAU = {
    "NguoiDeNghi_HoTen": "TRẦN VĂN BIỂN",
    "NguoiDeNghi_SoDinhDanh": "049000000111",
    "NguoiDeNghi_ThuongTru": {"quocGia": "Việt Nam", "tinh": "Đà Nẵng", "xa": "Núi Thành", "diaChi": "Thôn 1"},
}
_THE_NGUOI_NOP = {
    "Cccd2_HoTen": "LÊ THỊ NỘP",
    "Cccd2_SoDinhDanh": "001200000222",
    "Cccd2_NgaySinh": "01/02/2000",
    "Cccd2_GioiTinh": "Nữ",
    "Cccd2_ThuongTru": {"quocGia": "Việt Nam", "tinh": "Hà Nội", "xa": "Phường Hoàn Kiếm", "diaChi": "Số 5 Hàng Bạc"},
}


def _enrich(values, ctx=None):
    out, warnings = mapper.enrich([{"name": k, "value": v} for k, v in values.items()], {"formContext": ctx or {}})
    return {f["name"]: f["value"] for f in out if f.get("occurrence") is None}, warnings


def test_nop_thay_bu_noi_thuong_tru_nguoi_nop_tu_the_khop_so_cccd_tai_khoan():
    # LLM tách vai được tên/số người nộp nhưng bỏ sót nơi thường trú dù thẻ có.
    values = {**_CHU_TAU, **_THE_NGUOI_NOP, "NguoiNop_HoTen": "LÊ THỊ NỘP", "NguoiNop_SoDinhDanh": "001200000222"}
    got, warnings = _enrich(values, {"applicantFullname": "Lê Thị Nộp", "applicantIdentityNumber": "001200000222"})
    assert got["data[isOwnerDossierCheck]"] is False
    assert got["data[fullname]"] == "LÊ THỊ NỘP"
    assert got["data[identityNumber]"] == "001200000222"
    assert got["data[birthday]"] == "01/02/2000"
    assert got["data[gender]"] == "Nữ"
    assert got["data[province]"] == "Thành phố Hà Nội"
    assert got["data[district]"] and got["data[address]"] == "Số 5 Hàng Bạc"
    assert got["data[ownerFullname]"] == "TRẦN VĂN BIỂN"
    assert not any("người nộp" in w for w in warnings)


def test_llm_bo_trong_nguoi_nop_van_lay_duoc_tu_the_khop_tai_khoan():
    got, _ = _enrich({**_CHU_TAU, **_THE_NGUOI_NOP},
                     {"applicantFullname": "Lê Thị Nộp", "applicantIdentityNumber": "001200000222"})
    assert got["data[fullname]"] == "LÊ THỊ NỘP"
    assert got["data[address]"] == "Số 5 Hàng Bạc"
    assert got["data[ownerIdentityNumber]"] == "049000000111"


def test_the_khop_tai_khoan_thang_nguoi_nop_llm_gan_nham():
    values = {**_CHU_TAU, **_THE_NGUOI_NOP, "NguoiNop_HoTen": "NGƯỜI KHÁC", "NguoiNop_SoDinhDanh": "001299999999"}
    got, _ = _enrich(values, {"applicantFullname": "Lê Thị Nộp", "applicantIdentityNumber": "001200000222"})
    assert got["data[fullname]"] == "LÊ THỊ NỘP"
    assert got["data[identityNumber]"] == "001200000222"


def test_the_chu_tau_bu_nhan_than_chu_tau_khi_tu_nop():
    values = {"NguoiDeNghi_HoTen": "TRẦN VĂN BIỂN", "NguoiDeNghi_SoDinhDanh": "049000000111",
              "Cccd1_HoTen": "TRẦN VĂN BIỂN", "Cccd1_SoDinhDanh": "049000000111", "Cccd1_NgaySinh": "03/04/1970",
              "Cccd1_NgayCap": "05/06/2021"}
    got, _ = _enrich(values, {"applicantFullname": "Trần Văn Biển", "applicantIdentityNumber": "049000000111"})
    assert got["data[isOwnerDossierCheck]"] is True
    assert got["data[birthday]"] == "03/04/1970"
    assert got["data[identityDate]"] == "05/06/2021"


def test_nop_thay_khong_co_cccd_nguoi_nop_thi_canh_bao():
    got, warnings = _enrich(dict(_CHU_TAU), {"applicantFullname": "Lê Thị Nộp", "applicantIdentityNumber": "001200000222"})
    assert got["data[fullname]"] == "Lê Thị Nộp"
    assert "data[province]" not in got
    assert any("người nộp" in w for w in warnings)
