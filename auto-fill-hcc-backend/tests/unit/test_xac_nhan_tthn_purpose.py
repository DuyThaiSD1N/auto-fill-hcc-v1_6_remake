from app.pipelines.xac_nhan_tthn.process import purpose


def _fields(value):
    return [{"name": "HoVaTenC", "value": "X"}, {"name": "Purpose", "comp": "raw", "value": value}]


def _fake_chat(reply):
    async def chat(messages, *args, **kwargs):
        chat.user = messages[-1]["content"]
        return reply
    return chat


async def test_thay_bang_cau_da_chuan_hoa(monkeypatch):
    fake = _fake_chat('```json\n{"muc_dich": "Bổ sung hồ sơ mua bán xe máy", "do_chac": "cao"}\n```')
    monkeypatch.setattr(purpose.client, "chat", fake)
    fields = _fields("Bổ sung hồ sơ mua hàng xe máy")
    await purpose.normalize(fields, "Mục đích sử dụng: Bổ sung hồ sơ mua hàng xe máy\nTôi cam đoan")
    assert fields[1]["value"] == "Bổ sung hồ sơ mua bán xe máy"
    assert "DÒNG OCR: Bổ sung hồ sơ mua hàng xe máy" in fake.user


async def test_khong_chac_thi_giu_nguyen(monkeypatch):
    monkeypatch.setattr(purpose.client, "chat", _fake_chat('{"muc_dich": "Câu khác", "do_chac": "thap"}'))
    fields = _fields("Câu gốc")
    await purpose.normalize(fields, "")
    assert fields[1]["value"] == "Câu gốc"


async def test_khong_them_cum_phap_ly_vao_muc_dich_ket_hon(monkeypatch):
    reply = '{"muc_dich": "Để đăng ký kết hôn, không có giá trị để đăng ký kết hôn", "do_chac": "cao"}'
    monkeypatch.setattr(purpose.client, "chat", _fake_chat(reply))
    fields = _fields("Để đăng ký kết hôn")
    await purpose.normalize(fields, "")
    assert fields[1]["value"] == "Để đăng ký kết hôn"


async def test_loi_llm_giu_nguyen_va_khong_goi_khi_trong(monkeypatch):
    async def boom(*args, **kwargs):
        raise RuntimeError("down")
    monkeypatch.setattr(purpose.client, "chat", boom)
    fields = _fields("Câu gốc")
    await purpose.normalize(fields, "")
    assert fields[1]["value"] == "Câu gốc"
    empty = _fields("")
    await purpose.normalize(empty, "")  # không có mục đích → không gọi LLM, không lỗi
    assert empty[1]["value"] == ""


def test_dong_to_khai_uu_tien_hon_giay_cu():
    text = ("Giấy này được sử dụng để: vay vốn ngân hàng\n"
            "Mục đích sử dụng giấy xác nhận: Bổ sung hồ sơ đất\nTôi cam đoan")
    assert purpose.purpose_line(text) == "Bổ sung hồ sơ đất"
