"""Đăng ký kết hôn — luồng kết hợp Vintern ‖ Qwen: luật ghép, tách thẻ, điều phối (dữ liệu giả)."""
import base64
import io

from PIL import Image, ImageDraw

from app.pipelines.ket_hon.process import ket_hop
from app.pipelines.ket_hon.process.ket_hop import ghep as ghep_mod
from app.pipelines.ket_hon.process.ket_hop.ghep import ghep

NAM_ID = "001095000123"   # mã tỉnh 001, nam sinh 1995
NU_ID = "001197000456"    # nữ sinh 1997


def _nam(**kw):
    base = {"BenNam_HoTen": "NGUYỄN VĂN AN", "BenNam_SoDinhDanh": NAM_ID, "BenNam_NgaySinh": "01/02/1995"}
    return {**base, **kw}


def _nu(**kw):
    base = {"BenNu_HoTen": "TRẦN THỊ BÌNH", "BenNu_SoDinhDanh": NU_ID, "BenNu_NgaySinh": "03/04/1997"}
    return {**base, **kw}


def test_so_thieu_chu_so_lay_ben_du_12_so():
    out, _ = ghep(_nam(BenNam_SoDinhDanh="00109500012"), _nam(), [])
    assert out["BenNam_SoDinhDanh"] == NAM_ID


def test_cung_hop_le_ma_khac_lay_so_khop_mrz():
    khac = "001095000999"
    out, _ = ghep(_nam(BenNam_SoDinhDanh=khac), _nam(), ["IDVNM0950001230" + NAM_ID + "<<1"])
    assert out["BenNam_SoDinhDanh"] == NAM_ID


def test_cung_hop_le_khong_doi_chieu_duoc_lay_vintern():
    khac = "001095000999"
    out, _ = ghep(_nam(BenNam_SoDinhDanh=khac), _nam(), [])
    assert out["BenNam_SoDinhDanh"] == khac


def test_so_lech_gioi_tinh_la_hong():
    # Số của nữ nằm ở nhóm nam bên Vintern → hỏng; Qwen đúng → lấy Qwen.
    out, _ = ghep(_nam(BenNam_SoDinhDanh=NU_ID), _nam(), [])
    assert out["BenNam_SoDinhDanh"] == NAM_ID


def test_qwen_gan_nguoc_nam_nu_thi_dao_lai():
    q = {"BenNam_HoTen": "TRẦN THỊ BÌNH", "BenNam_SoDinhDanh": NU_ID,
         "BenNu_HoTen": "NGUYỄN VĂN AN", "BenNu_SoDinhDanh": NAM_ID}
    out, quyet = ghep({**_nam(), **_nu()}, q, [])
    assert out["BenNam_SoDinhDanh"] == NAM_ID and out["BenNu_SoDinhDanh"] == NU_ID
    assert quyet[0]["field"] == "*"


def test_vintern_mat_ca_nguoi_lay_tu_qwen():
    out, _ = ghep(_nam(), {**_nam(), **_nu()}, [])
    assert out["BenNu_HoTen"] == "TRẦN THỊ BÌNH"
    assert out["BenNu_SoDinhDanh"] == NU_ID


def test_ngay_sinh_lech_nam_trong_so_la_hong():
    out, _ = ghep(_nam(BenNam_NgaySinh="01/02/1996"), _nam(), [])
    assert out["BenNam_NgaySinh"] == "01/02/1995"


def test_noi_cu_tru_lay_ca_cum_khong_tron():
    v = _nam(BenNam_NoiCuTru_TrongNuoc={"quocGia": "Việt Nam", "tinh": "Lâm Đồng", "xa": "", "diaChi": "Tổ 1"})
    q = _nam(BenNam_NoiCuTru_TrongNuoc={"quocGia": "Việt Nam", "tinh": "Lâm Đồng", "xa": "Phường A", "diaChi": "Tổ 2"})
    out, _ = ghep(v, q, [])
    assert out["BenNam_NoiCuTru_TrongNuoc"]["diaChi"] == "Tổ 2"


def test_cum_ly_hon_lay_ca_cum_cua_vintern():
    v = _nam(BenNam_BanAnLyHon_So="12/2020/QĐ")
    q = _nam(BenNam_BanAnLyHon_So="12/2020/QĐ-X", BenNam_BanAnLyHon_Ngay="01/01/2020")
    out, _ = ghep(v, q, [])
    assert out["BenNam_BanAnLyHon_So"] == "12/2020/QĐ"
    assert "BenNam_BanAnLyHon_Ngay" not in out


def test_dan_toc_chi_qwen_co_ma_khong_co_nhan_thi_bo():
    out, _ = ghep(_nam(), _nam(BenNam_DanToc="Kinh"), ["CĂN CƯỚC\nHọ, chữ đệm và tên"])
    assert "BenNam_DanToc" not in out
    out, _ = ghep(_nam(), _nam(BenNam_DanToc="Kinh"), ["Dân tộc: Kinh"])
    assert out["BenNam_DanToc"] == "Kinh"


def test_noi_cap_khac_nhau_lay_ben_khop_ngay_cap():
    v = _nam(BenNam_NgayCap="10/08/2024", BenNam_NoiCap="Cục Cảnh sát quản lý hành chính về trật tự xã hội")
    q = _nam(BenNam_NgayCap="10/08/2024", BenNam_NoiCap="Bộ Công an")
    out, _ = ghep(v, q, [])
    assert out["BenNam_NoiCap"] == "Bộ Công an"


def test_dau_hoi_tinh_la_thieu():
    out, _ = ghep(_nam(BenNam_HoTen="NGUYỄN V[?] AN"), _nam(), [])
    assert out["BenNam_HoTen"] == "NGUYỄN VĂN AN"


def test_soat_ngay_khong_co_trong_chu_vintern_thi_lay_qwen():
    v = _nu(BenNu_NgayCap="19/02/2025")
    q = _nu(BenNu_NgayCap="11/08/2021")
    out, _ = ghep(v, q, [], soat=True, chu_v="Ngày sinh 03/04/1997", chu_q=None)
    assert out["BenNu_NgayCap"] == "11/08/2021"
    out, _ = ghep(v, q, [])                       # không bật soát: rule gốc lấy Vintern
    assert out["BenNu_NgayCap"] == "19/02/2025"


def test_soat_gia_tri_bia_ma_ben_kia_trong_thi_bo():
    out, _ = ghep({"ToKhai_LoaiDangKy": "Đăng ký lần đầu"}, {}, [], soat=True, chu_v="TỜ KHAI ĐĂNG KÝ KẾT HÔN", chu_q=None)
    assert "ToKhai_LoaiDangKy" not in out


def test_soat_xa_khong_co_that_thi_lay_ben_kia():
    v = _nam(BenNam_NoiCuTru_TrongNuoc={"quocGia": "Việt Nam", "tinh": "Khánh Hòa", "xa": "Canh", "diaChi": "TDP 1"})
    q = _nam(BenNam_NoiCuTru_TrongNuoc={"quocGia": "Việt Nam", "tinh": "Khánh Hòa", "xa": "Phường Cam Linh", "diaChi": "TDP 1"})
    out, _ = ghep(v, q, [], soat=True)
    assert out["BenNam_NoiCuTru_TrongNuoc"]["xa"] == "Phường Cam Linh"


def test_cum_ly_hon_vintern_trong_thi_qwen_khong_va():
    out, _ = ghep(_nam(), _nam(BenNam_BanAnLyHon_So="12/2020/QĐ", BenNam_TinhTrangHonNhan="3"), [])
    assert "BenNam_BanAnLyHon_So" not in out and "BenNam_TinhTrangHonNhan" not in out


def test_o_tich_to_khai_theo_qwen_ke_ca_qwen_bo_trong():
    out = ghep_mod.o_tich_theo_qwen({"CopyRequest_WantsCopy": "Có", "BenNam_HoTen": "A B"}, {}, [])
    assert out == {"BenNam_HoTen": "A B"}
    out = ghep_mod.o_tich_theo_qwen({}, {"CopyRequest_Quantity": "2"}, [])
    assert out == {"CopyRequest_Quantity": "2"}


# ---------------------------------------------------------------- tách thẻ
def _trang_hai_the() -> dict:
    img = Image.new("RGB", (1240, 1754), "white")
    d = ImageDraw.Draw(img)
    for y in (150, 1000):
        d.rectangle((300, y, 300 + 640, y + 404), fill=(90, 160, 150))
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return {"name": "cccd.png", "type": "image/png",
            "dataUrl": "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode()}


def test_tach_the_cat_rieng_hai_the_va_gop_lai_dung_tep():
    from app.services import tach_the
    f = _trang_hai_the()
    da_cat, _ = tach_the.cat([f])
    assert len(da_cat[0][0][1]) == 2
    items, groups, so_the = tach_the.tach([f], da_cat)
    assert so_the == 2 and len(items) == 2 and groups == [[0, 1]]
    gop = tach_the.gop_ket_qua([f], [{"name": i["name"], "text": f"the {n}"} for n, i in enumerate(items, 1)], groups)
    assert gop[0]["name"] == "cccd.png" and "the 1" in gop[0]["text"] and "the 2" in gop[0]["text"]


def test_tach_the_tep_khong_doc_duoc_giu_nguyen():
    from app.services import tach_the
    f = {"name": "x.jpg", "type": "image/jpeg", "dataUrl": "data:x;base64,AAA"}
    da_cat, _ = tach_the.cat([f])
    items, groups, so_the = tach_the.tach([f], da_cat)
    assert items == [f] and groups == [[0]] and so_the == 0


# ---------------------------------------------------------------- điều phối
def _vintern(fields, text="CĂN CƯỚC"):
    async def chay(ocr_fn=None):
        return {"fields": [{"name": k, "comp": "x-input", "value": v} for k, v in fields.items()],
                "ocr_text": text, "llm_output": {"fields": fields}, "errors": [], "stats": {}}
    return chay


async def test_qwen_loi_giu_nguyen_vintern(monkeypatch):
    from app.pipelines.ket_hon.process.ket_hop import qwen_json
    monkeypatch.setattr(qwen_json, "doc", lambda files, da_cat: {"raw": {}, "error": "máy chủ lỗi"})
    res = await ket_hop.run({"doc": [{"name": "x.jpg", "type": "image/jpeg", "dataUrl": "data:x;base64,AAA"}]},
                            _vintern(_nam()))
    assert {f["name"]: f["value"] for f in res["fields"]} == _nam()
    assert res["errors"] == [] and res["llm_output"]["ket_hop"]["qwen_loi"] == "máy chủ lỗi"


async def test_ghep_vintern_thieu_lay_qwen_va_o_tich_theo_qwen_khi_co_to_khai(monkeypatch):
    from app.pipelines.ket_hon.process.ket_hop import qwen_json
    q = {**_nam(BenNam_NgayCap="02/07/2021")}
    monkeypatch.setattr(qwen_json, "doc", lambda files, da_cat: {"raw": q, "ms": 5})
    v = {**_nam(), "CopyRequest_WantsCopy": "Có"}
    res = await ket_hop.run({"doc": [{"name": "x.jpg", "type": "image/jpeg", "dataUrl": "data:x;base64,AAA"}]},
                            _vintern(v, text="TỜ KHAI ĐĂNG KÝ KẾT HÔN\nNgày cấp 02/07/2021"))
    out = {f["name"]: f["value"] for f in res["fields"]}
    assert out["BenNam_NgayCap"] == "02/07/2021"
    assert "CopyRequest_WantsCopy" not in out
    assert res["llm_output"]["fields"] == v and res["llm_output"]["ket_hop"]["ghep"]
