"""Màn chọn thủ tục handfree: 8 ô "hay dùng" + khóa thủ tục theo tỉnh (provinceOnly).

- _service_list_card gắn frequent/frequentOrder cho đúng 8 key cấu hình.
- public_list_for lọc thủ tục provinceOnly theo tỉnh account.
- _to_confirm_procedure chặn account khác tỉnh (choke point mọi lối chọn: bấm ô, gọi tên, detect).
- _HOAN_THIEN_THEO_TINH: 11 tỉnh theo dõi chỉ thấy + mở được thủ tục cột tỉnh ghi "Hoàn thiện phần mềm".
"""
from app.channels.handfree.chat import flow
from app.channels.handfree import procedure_registry as registry

_HANOI = {"auth_user": {"province_slug": "hanoi"},
          "location": {"province": "Thành phố Hà Nội", "ward": "Phường A"}}
_BACNINH = {"auth_user": {"province_slug": "bacninh"},
            "location": {"province": "Tỉnh Bắc Ninh", "ward": "Phường Song Liễu"}}


def test_card_gan_dung_8_o_hay_dung_theo_thu_tu():
    card = flow._service_list_card(_HANOI)
    freq = sorted((i for i in card["items"] if i.get("frequent")),
                  key=lambda x: x["frequentOrder"])
    assert [i["key"] for i in freq] == list(registry._HOME_FREQUENT_KEYS)
    non = [i for i in card["items"] if not i.get("frequent")]
    assert non and all("frequentOrder" not in i for i in non)


def test_public_list_for_khong_khoa_khi_thieu_tinh():
    # Account thiếu tỉnh → KHÔNG lọc (tránh ẩn nhầm hết).
    assert len(registry.public_list_for("")) == len(registry.public_list())


def test_khoa_tinh_an_va_chan_goi_ten(monkeypatch):
    # Tạm khóa ket-hon về Bắc Ninh.
    proc = registry._BY_KEY["ket-hon"]
    monkeypatch.setitem(proc, "provinceOnly", ["bacninh"])

    # Account Hà Nội: không thấy trong card + bị chặn khi chọn.
    card = flow._service_list_card(_HANOI)
    assert not any(i["key"] == "ket-hon" for i in card["items"])
    conv = dict(_HANOI, state="greet")
    r = flow._to_confirm_procedure(conv, "ket-hon")
    assert "Bắc Ninh" in r.display_md
    assert conv.get("procedure_key") is None
    assert conv["state"] == "greet"

    # Account Bắc Ninh: thấy + mở được.
    assert any(i["key"] == "ket-hon" for i in flow._service_list_card(_BACNINH)["items"])
    conv2 = dict(_BACNINH, state="greet")
    flow._to_confirm_procedure(conv2, "ket-hon")
    assert conv2["procedure_key"] == "ket-hon"
    assert conv2["state"] == "confirm_procedure"


# ── Lọc theo bảng "Hoàn thiện phần mềm" (_HOAN_THIEN_THEO_TINH, bảng theo dõi 10/11/2026) ──

def _account(slug: str) -> dict:
    return {"auth_user": {"province_slug": slug}, "location": {}}


def _card_keys(slug: str) -> set[str]:
    return {i["key"] for i in flow._service_list_card(_account(slug))["items"]}


def test_moi_thu_tuc_tro_ly_deu_co_dong_trong_bang_hoan_thien():
    # Thủ tục mới đưa lên trợ lý mà quên thêm dòng → ẩn im lặng ở cả 11 tỉnh theo dõi.
    missing = [p["key"] for p in registry.PROCEDURES if p["key"] not in registry._HOAN_THIEN_THEO_TINH]
    assert not missing, "thiếu dòng trong _HOAN_THIEN_THEO_TINH: " + ", ".join(missing)


def test_so_thu_tuc_moi_tinh_dung_bang_hoan_thien():
    counts = {slug: len(_card_keys(slug)) for slug in registry._TINH_THEO_DOI}
    assert counts == {
        # Bảng thu-tuc-20261111-0856.xlsx (khớp Excel 100%, không còn ghi đè tay). 12/11 người dùng mở thêm cấp lại
        # GCN bị mất Bắc Ninh 1.115465 (STT 50) cho Bắc Ninh, đính chính GCN Khánh Hòa 1.012790 (STT 103) cho Khánh Hòa.
        # 12/11: +1 mọi tỉnh khai-sinh-nuoc-ngoai (_TAT_CA); Lâm Đồng +2 bản riêng 1.116360 / 1.116356;
        # +1 mọi tỉnh thẻ HDV quốc tế 1.004628 (người dùng mở lại toàn quốc); Lâm Đồng +1 bản riêng 1.116366.
        # Bắc Ninh +1 bản riêng 1.011442 (đăng ký thay đổi BPBĐ, chưa có trong bảng — tạm mở Bắc Ninh).
        # 16/11: +2 mọi tỉnh Bộ Công an thong-bao-luu-tru (2.001159) + dang-ky-thuong-tru (1.004222) (_TAT_CA).
        # 16/11: +1 mọi tỉnh Bộ Công an cap-doi-the-can-cuoc (2.001195) (_TAT_CA, người dùng: toàn quốc).
        # 16/11: +1 mọi tỉnh Bộ Công an cap-the-can-cuoc-duoi-14-tuoi (1.012549 / 1.014062) (_TAT_CA).
        # 16/11: +1 mọi tỉnh dang-ky-xe-lan-dau-san-xuat-lap-rap-trong-nuoc (1.012575) (_TAT_CA, mặc định toàn quốc).
        # 16/11: Lào Cai -1 tro-cap-xa-hoi-hang-thang (1.001776), người dùng ẩn cho Cam Đường.
        # 16/11: +1 mọi tỉnh Bộ Công an cap-lai-the-can-cuoc (2.001194) (_TAT_CA, mặc định toàn quốc).
        # 16/11: +1 mọi tỉnh Bộ Công an cap-the-can-cuoc-tu-du-14-tuoi (2.000200 / 1.014061) (_TAT_CA, mặc định).
        # 16/11: +1 mọi tỉnh Bộ Công an dieu-chinh-thong-tin-ve-cu-tru (1.010039) (_TAT_CA, mặc định toàn quốc).
        # 16/11: +1 mọi tỉnh Bộ Công an xac-nhan-thong-tin-ve-cu-tru (1.010041) (_TAT_CA, mặc định toàn quốc).
        # 18/11: +1 mọi tỉnh tư pháp dang-ky-hoat-dong-trung-tam-tu-van-phap-luat (1.000627) (_TAT_CA, mặc định).
        # 18/11: +1 mọi tỉnh tư pháp dang-ky-hanh-nghe-luat-su-voi-tu-cach-ca-nhan (1.002153) (_TAT_CA, mặc định).
        # 18/11: +1 mọi tỉnh Bộ Y tế cap-gcn-du-dieu-kien-kinh-doanh-duoc-so-y-te (1.014076) (_TAT_CA, mặc định).
        # 18/11: +1 mọi tỉnh Bộ Công an dang-ky-mau-con-dau (2.001428) (_TAT_CA, mặc định toàn quốc).
        # 18/11: +1 mọi tỉnh Bộ Công an cap-ho-chieu-pho-thong-o-trong-nuoc (1.001456) (_TAT_CA, mặc định toàn quốc).
        # 18/11: +1 mọi tỉnh Bộ Công an cap-thi-thuc-cho-nguoi-nuoc-ngoai-tai-viet-nam (1.001194) (_TAT_CA, mặc định).
        # 19/11: +1 mọi tỉnh Bộ Công an cap-the-tam-tru-cho-nguoi-nuoc-ngoai-tai-viet-nam (1.003460) (_TAT_CA, mặc định).
        # 19/11: +1 mọi tỉnh Bộ Nội vụ cong-nhan-che-do-khang-chien-nhiem-chat-doc-hoa-hoc (1.010816) (_TAT_CA,
        # người dùng: toàn quốc).
        # 19/11: +1 mọi tỉnh Bộ Xây dựng cap-giay-phep-lien-van-viet-lao-campuchia (1.002877) (_TAT_CA, mặc định).
        # 19/11: +1 riêng Lâm Đồng tinh-tien-su-dung-dat-nd-50-2026-lam-dong (1.115148) (provinceOnly lamdong).
        # 19/11: +1 mọi tỉnh Bộ Công an trinh-bao-mat-ho-chieu-pho-thong-cap-xa (1.010386) (_TAT_CA, mặc định).
        # 20/11: +1 mọi tỉnh Bộ Công an trinh-bao-mat-ho-chieu-pho-thong-cap-tinh (1.001445) (_TAT_CA, mặc định).
        # 20/11: +1 mọi tỉnh Bộ Công an tach-ho (1.010038) (_TAT_CA, mặc định toàn quốc).
        # 20/11: +1 mọi tỉnh Bộ Công an xoa-dang-ky-tam-tru (1.010028) (_TAT_CA, mặc định toàn quốc).
        # 20/11: +1 mọi tỉnh Bộ Công an dang-ky-xe-lan-dau-nhap-khau (1.013066) (_TAT_CA, mặc định toàn quốc).
        # 20/11: +1 mọi tỉnh Bộ Công an dang-ky-sang-ten-di-chuyen-xe-cap-tinh (2.000076) (_TAT_CA, mặc định toàn quốc).
        # 20/11: +1 mọi tỉnh Bộ Công an thu-hoi-chung-nhan-dang-ky-bien-so-xe-cap-tinh (2.001485) (_TAT_CA, mặc định).
        # 20/11: +2 mọi tỉnh Bộ Công an thu-hoi-chung-nhan-dang-ky-bien-so-xe-cap-xa (1.010919), …-tai-cuc (2.000311) (_TAT_CA, mặc định).
        # 21/11: +1 Bắc Ninh dang-ky-bien-dong-doi-ten-nguoi-su-dung-dat-bac-ninh (1.115460, {"bacninh"}).
        # 24/11: +1 mọi tỉnh Bộ Công an xoa-dang-ky-thuong-tru (1.003197) (_TAT_CA, mặc định toàn quốc).
        # 24/11: +1 mọi tỉnh tư pháp khai-tu-nuoc-ngoai (1.001766) (_TAT_CA, mặc định toàn quốc).
        # 24/11: +1 mọi tỉnh tư pháp khai-tu-luu-dong (1.000419) (_TAT_CA, mặc định toàn quốc).
        # 24/11: +1 Bắc Ninh xac-nhan-tiep-tuc-su-dung-dat-nong-nghiep-bac-ninh (1.115462, {"bacninh"}).
        # 24/11: +1 mọi tỉnh Bộ Xây dựng cap-giay-phep-thi-cong-cong-trinh-tren-duong-bo-dang-khai-thac (1.013061) (_TAT_CA, mặc định toàn quốc).
        # 24/11: +1 mọi tỉnh Bộ Công an cap-phieu-ly-lich-tu-phap-cong-an-cap-tinh (3.000333) (_TAT_CA, mặc định toàn quốc).
        "laichau": 154, "bacninh": 162, "lamdong": 148, "danang": 151, "quangninh": 155, "ninhbinh": 144,
        # 24/11: +1 Khánh Hòa tinh-tien-su-dung-dat-nd-50-2026-khanh-hoa (1.115148, {"khanhhoa"}).
        "quangngai": 145, "laocai": 143, "quangtri": 145, "khanhhoa": 151, "tuyenquang": 145,
    }


def test_tinh_chi_thay_thu_tuc_da_hoan_thien():
    kh = _card_keys("khanhhoa")
    assert "dang-ky-dat-dai-lan-dau-khanh-hoa" in kh          # STT 44: Khánh Hòa hoàn thiện
    assert "cap-doi-gcn-khanh-hoa" in kh                       # STT 93: Khánh Hòa hoàn thiện (bảng 11:55)
    assert "khai-tu-lien-thong" in kh                          # STT 110: Khánh Hòa hoàn thiện (bảng 11/11)
    assert "khai-tu-lien-thong" in _card_keys("tuyenquang")    # STT 110: Tuyên Quang hoàn thiện (bảng 11/11)
    assert "dinh-chinh-gcn-da-cap-khanh-hoa" in kh             # STT 103: 12/11 người dùng mở cho Khánh Hòa
    assert "cap-lai-giay-chung-nhan-do-bi-mat-bac-ninh" in _card_keys("bacninh")  # STT 50: 12/11 mở cho Bắc Ninh
    assert "cap-gcn-dang-ky-tau-ca" not in kh                  # STT 118: Khánh Hòa chưa cập nhật
    assert "cap-phep-long-duong-via-he" in _card_keys("danang")  # STT 138: chỉ Đà Nẵng
    assert "cap-phep-long-duong-via-he" not in _card_keys("laichau")
    assert "cap-gcn-dang-ky-tau-ca" not in _card_keys("bacninh")  # STT 118: Bắc Ninh Pending
    assert "tro-cap-xa-hoi-hang-thang" not in _card_keys("laocai")  # 16/11: ẩn 1.001776 cho Cam Đường
    assert "tro-cap-xa-hoi-hang-thang" in _card_keys("bacninh")
    assert "hoa-giai-tranh-chap-dat-dai" in _card_keys("lamdong")  # STT 231
    # 1.004628: vắng bảng 11/11, 12/11 người dùng mở lại cả 11 tỉnh.
    assert all("cap-the-huong-dan-vien-du-lich-quoc-te" in _card_keys(s) for s in registry._TINH_THEO_DOI)
    # 12/11: 1.116360 + 1.116356 bản Lâm Đồng mở riêng cho Lâm Đồng.
    for key in ("dang-ky-dat-dai-lan-dau-lam-dong", "dang-ky-dien-tich-tang-them-lam-dong",
                "giao-thue-dat-giao-rung-gia-han-su-dung-dat", "tinh-tien-su-dung-dat-nd-50-2026-lam-dong"):
        assert key in _card_keys("lamdong") and key not in _card_keys("khanhhoa"), key
    # 24/11: 1.115148 bản Khánh Hòa chỉ mở cho Khánh Hòa.
    assert "tinh-tien-su-dung-dat-nd-50-2026-khanh-hoa" in kh
    assert "tinh-tien-su-dung-dat-nd-50-2026-khanh-hoa" not in _card_keys("lamdong")
    # 1.013997: STT 230, cả 11 tỉnh
    assert all("ho-tro-co-so-san-xuat-thiet-hai-dich-benh-dong-vat" in _card_keys(s) for s in registry._TINH_THEO_DOI)
    # Bảng không mở khóa provinceOnly: bản Bắc Ninh ghi _TAT_CA vẫn không lọt sang tỉnh khác.
    assert "tach-hop-thua-dat-bac-ninh" in _card_keys("bacninh")
    assert "tach-hop-thua-dat-bac-ninh" not in _card_keys("laichau")


def test_tinh_ngoai_bang_theo_doi_khong_loc_them():
    keys = _card_keys("gialai")
    assert {"hoa-giai-tranh-chap-dat-dai", "khai-tu-lien-thong", "cap-phep-long-duong-via-he"} <= keys
    expected = [p["key"] for p in registry.public_list() if registry.is_allowed_in_province(p, "gialai")]
    assert [p["key"] for p in registry.public_list_for("gialai")] == expected


def test_agent_chon_thu_tuc_chi_thay_thu_tuc_da_hoan_thien():
    from app.channels.handfree.chat.procedure_picker.agent import procedures_for
    keys = {p["key"] for p in procedures_for("khanhhoa")}
    assert "cap-gcn-dang-ky-tau-ca" not in keys and "dang-ky-dat-dai-lan-dau-khanh-hoa" in keys


def test_chon_thu_tuc_tinh_chua_hoan_thien_bi_chan():
    # Detect trang / gọi tên thủ tục chưa hoàn thiện ở tỉnh tài khoản → không mở, mời chọn thủ tục khác.
    conv = dict(_account("khanhhoa"), state="greet")
    r = flow._to_confirm_procedure(conv, "cap-gcn-dang-ky-tau-ca")
    assert "chưa làm được" in r.display_md and "Khánh Hòa" in r.display_md
    assert conv.get("procedure_key") is None and conv["state"] == "greet"
    assert [c.get("kind") for c in r.cards] == [flow._service_list_card(conv).get("kind")]

    conv2 = dict(_account("khanhhoa"), state="greet")
    flow._to_confirm_procedure(conv2, "dang-ky-dat-dai-lan-dau-khanh-hoa")
    assert conv2["procedure_key"] == "dang-ky-dat-dai-lan-dau-khanh-hoa"
