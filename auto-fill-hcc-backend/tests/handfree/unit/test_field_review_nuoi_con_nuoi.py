"""Đăng ký nuôi con nuôi trong nước: vòng bổ sung ô có khối lồng (khối mẹ / cha nuôi — ô con không có thẻ x-* riêng,
dropdown không có name). Mapper gửi kèm khối + nhãn cho dropdown để engine điền tìm đúng chỗ; vòng bổ sung chỉ bật
khi extension tách được khối lồng (supportsFieldReviewNested)."""
from app.channels.handfree.chat import field_review, store
from app.channels.handfree.procedure_registry import get_procedure
from app.pipelines.dang_ky_nuoi_con_nuoi_trong_nuoc.process.mapper import enrich

KEY = "dang-ky-nuoi-con-nuoi-trong-nuoc"
CAPS = {"supportsFieldReview": True, "supportsFieldReviewNested": True}


def _conv(caps=CAPS) -> dict:
    conv = store.new_conversation()
    conv.update({"procedure_key": KEY, "client_capabilities": dict(caps)})
    return conv


def test_chi_bat_khi_extension_tach_duoc_khoi_long():
    proc = get_procedure(KEY)
    assert field_review.active(_conv(), proc)
    assert not field_review.active(_conv({"supportsFieldReview": True}), proc), \
        "bản đọc eForm cũ tách khối mẹ/cha nuôi như khối địa chỉ → hỏi sai ô"


def test_lenh_dien_kem_khoi_long_va_o_nam_sinh():
    extra = field_review.fill_action_extra(_conv(), get_procedure(KEY))
    assert {"VoChongNhanNuoi_Me", "VoChongNhanNuoi_Cha", "MeNuoi", "ChaNuoi", "NguoiDonThanNhanNuoi"} <= set(extra["nested"])
    assert extra["textDates"] == ["NgaySinhM", "NgaySinhCha"]
    assert {"HoVaTenM", "VoChongNhanNuoi_Me#Dân tộc", "ChonNguoiDonThanNhanNuoi", "truongHopNhanNuoi"} <= set(extra["required"])


def test_thu_tuc_khac_khong_gui_khoi_long():
    extra = field_review.fill_action_extra(
        {"procedure_key": "ket-hon", "client_capabilities": {"supportsFieldReview": True}}, get_procedure("ket-hon"))
    assert "nested" not in extra


def _facts(**kw):
    base = {
        "AdoptiveMother_FullName": "Nguyễn Thị A", "AdoptiveMother_BirthDate": "01/01/1980",
        "AdoptiveMother_Ethnicity": "Kinh", "AdoptiveMother_IdNumber": "0" * 12,
        "AdoptiveMother_IdIssueDate": "01/02/2022", "AdoptiveMother_IdIssuePlace": "Bộ công an",
        "AdoptiveMother_Residence": {"quocGia": "Việt Nam", "tinh": "Tỉnh A", "xa": "Xã B", "chiTietDuoiXa": "Thôn C"},
    }
    base.update(kw)
    return [{"name": k, "value": v} for k, v in base.items()]


def _by_name(fields):
    return {f["name"]: f for f in fields}


def test_dropdown_khoi_me_nuoi_mang_khoi_va_nhan():
    out = _by_name(enrich(_facts()))
    assert out["DanTocM"]["containers"] == ["VoChongNhanNuoi_Me", "MeNuoi"] and out["DanTocM"]["label"] == "Dân tộc"
    assert out["QuocTichM"]["label"] == "Quốc tịch"
    assert out["LoaiGiayToDinhDanhM"]["label"] == "Giấy tờ tùy thân"
    assert out["LoaiCuTruM"]["label"] == "Loại cư trú"
    assert out["MeDoiTuong"]["label"] == "Mẹ nuôi là"
    # Ô chữ có name riêng: không cần khối + nhãn.
    assert "containers" not in out["HoVaTenM"] and "label" not in out["SoGiayToDinhDanhM"]


def test_dropdown_khoi_cha_nuoi_va_quoc_gia_khi_vo_chong_cung_nhan():
    facts = _facts(AdoptiveFather_FullName="Trần Văn B", AdoptiveFather_Ethnicity="Tày",
                   AdoptiveFather_Residence={"quocGia": "Việt Nam", "tinh": "Tỉnh A", "xa": "Xã B"})
    out = _by_name(enrich(facts))
    assert out["DanTocCha"]["containers"] == ["VoChongNhanNuoi_Cha", "ChaNuoi"]
    assert out["NoiCuTruM_QuocGia"]["label"] == "Quốc gia nơi cư trú"
    assert out["ChaDoiTuong"]["label"] == "Cha nuôi là"
