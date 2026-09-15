"""Màn chọn thủ tục handfree: 8 ô "hay dùng" + khóa thủ tục theo tỉnh (provinceOnly).

- _service_list_card gắn frequent/frequentOrder cho đúng 8 key cấu hình.
- public_list_for lọc thủ tục provinceOnly theo tỉnh account.
- _to_confirm_procedure chặn account khác tỉnh (choke point mọi lối chọn: bấm ô, gọi tên, detect).
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
