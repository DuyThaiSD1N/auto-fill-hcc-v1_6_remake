"""Gợi ý xã cho bước sửa chính tả xã (area_remap.ward_hints) + thanh tra tên xã của liên thông khai tử."""

import asyncio

from app.pipelines._shared import area_remap
from app.pipelines._shared.area_remap import remap_area, ward_hints
from app.pipelines._shared.thanh_tra import ten_xa
from app.pipelines.khai_tu_lien_thong.process import mapper
from app.pipelines.khai_tu_lien_thong.process.runner import run
from app.procedures.registry import get_procedure
from app.second_pass import service as second_pass

_Q = "Quảng Ngãi"


def _xa(tinh, xa):
    return (remap_area({"tinh": tinh, "xa": xa, "diaChi": "Xóm 2"}) or {}).get("xa")


def test_khong_goi_y_giu_nguyen_sua_chinh_ta_cu():
    # Tên đọc lệch 1 chữ với xã cũ (Bình Dương → Bình Sơn), lệch 2 chữ với Bình Chương.
    assert _xa(_Q, "Bình Lương") == "Xã Bình Sơn"


def test_goi_y_quay_khong_de_len_ket_qua_sua_chinh_ta():
    with ward_hints("HCC xã Bình Chương"):
        assert _xa(_Q, "Bình Lương") == "Xã Bình Sơn"
    # Xã cũ Bình Chánh lệch 1 chữ: người ở xã khác vẫn nộp ở quầy này.
    with ward_hints("HCC Xã Bình Minh"):
        assert _xa(_Q, "Bình chính") == "Xã Bình Sơn"


def test_goi_y_quay_dung_khi_ten_khong_gan_xa_nao():
    assert _xa("Bắc Ninh", "Phường Việt An") == "Phường Việt An"
    with ward_hints("Phường Việt Yên"):
        assert _xa("Bắc Ninh", "Phường Việt An") == "Phường Việt Yên"
    with ward_hints("HCC phường Yên Dũng"):
        assert _xa("Bắc Ninh", "phường yên chùng") == "Phường Yên Dũng"


def test_goi_y_manh_de_len_xa_cu_lech_chu_nhung_khong_de_khi_chi_lech_dau():
    with ward_hints("BÌNH CHƯƠNG", strong=True):
        assert _xa(_Q, "Bình Lương") == "Xã Bình Chương"
        assert _xa(_Q, "Xã Đinh Cương") == "Xã Đình Cương"
        # Tên xã có thật (xã cũ) không phải chữ đọc lệch: không đụng.
        assert _xa(_Q, "Bình Dương") == "Xã Bình Sơn"


def test_goi_y_het_hieu_luc_ngoai_khoi_with():
    with ward_hints("XÃ BÌNH CHƯƠNG", strong=True):
        pass
    assert _xa(_Q, "Bình Lương") == "Xã Bình Sơn"
    assert area_remap._WARD_HINTS.get() == ()


_OCR = (
    "TỜ KHAI ĐĂNG KÝ KHAI TỬ\nKính gửi: (1) ỦY BAN NHÂN DÂN XÃ BÌNH CHƯƠNG\n"
    "Nơi cư trú cuối cùng: (2) Xóm 2 Bình Lương Quảng Ngãi\n"
)
_FIELDS = [
    {"name": "NguoiMat_HoTen", "value": "NGUYỄN VĂN A"},
    {"name": "NguoiMat_NoiCuTruCuoiCung",
     "value": {"quocGia": "Việt Nam", "tinh": "Quảng Ngãi", "xa": "Bình Lương", "diaChi": "Xóm 2"}},
]


def _residence(ocr_text):
    out = mapper.enrich([dict(f) for f in _FIELDS], {}, ocr_text=ocr_text)
    return next(f["value"] for f in out if f["name"] == "NctccDiaChi")


def test_lien_thong_khai_tu_lay_xa_kinh_gui_lam_goi_y_manh():
    assert mapper._receiving_wards(_OCR) == ["BÌNH CHƯƠNG"]
    assert _residence(_OCR)["xa"] == "Bình Chương"
    assert _residence("")["xa"] == "Bình Sơn"


def test_thanh_tra_ten_xa_nhan_ra_xa_do_ma_doan():
    value = _FIELDS[1]["value"]
    found = ten_xa.guessed_ward(value, mapper.khai_tu_mapper._area(value))
    assert found and found[2] == "Xã Bình Sơn"
    # Tên đọc ra xã hiện hành không cần sửa chính tả: không phải xã do mã đoán.
    exact = {**value, "xa": "Bình Chương"}
    assert ten_xa.guessed_ward(exact, mapper.khai_tu_mapper._area(exact)) is None


def test_lien_thong_khai_tu_bat_dien_dot_hai_angular():
    assert second_pass.capability(get_procedure("khai-tu-lien-thong")) == "secondPassAngular"


def test_runner_tra_luot_dot_hai_khi_extension_khai(monkeypatch):
    async def fake_extract(files_by_role, options, documents_out=None):
        if documents_out is not None:
            documents_out.append({"name": "to_khai.pdf", "text": _OCR})
        return {"fields": [dict(f) for f in _FIELDS], "ocr_text": _OCR}

    monkeypatch.setattr("app.pipelines.khai_tu_lien_thong.process.runner.extract", fake_extract)
    on = asyncio.run(run({"": []}, {"_secondPass": True}))
    off = asyncio.run(run({"": []}, {}))
    assert callable(on.get("_second_pass"))
    assert "_second_pass" not in off
