"""Đăng ký khai sinh có yếu tố nước ngoài (2.000528) — cổng Bộ Tư pháp, eForm khai sinh mẫu 2093."""
import asyncio
import json
import re
import unicodedata
from pathlib import Path

from app.pipelines.khai_sinh_nuoc_ngoai.attach import planner as attach
from app.pipelines.khai_sinh_nuoc_ngoai.attach.dinh_kem_khong_tach import planner as khong_tach
from app.pipelines.khai_sinh_nuoc_ngoai.attach.dinh_kem_khong_tach.planner import (
    BIRTH_CERTIFICATE,
    ROWS,
    build_plan_items,
    live_rows,
    promote_birth_row,
)
from app.pipelines.khai_sinh_nuoc_ngoai.attach.dinh_kem_tach import planner as tach
from app.pipelines.khai_sinh_nuoc_ngoai.process import mapper
from app.pipelines.khai_sinh_nuoc_ngoai.process.schema import ALLOWED, UI_COMP_BY_NAME
from app.process.schemas import FileItem
from app.procedures.registry import PROCEDURES, get_attach_pipeline, get_pipeline
from app.services import ocr

KEY = "khai-sinh-nuoc-ngoai"
ROOT = Path(__file__).resolve().parents[2]
LINKS = ROOT / "app" / "procedures" / "data" / "ke_khai_links.json"
EFORM_2093 = ROOT / "monitor-fe" / "src" / "simulations" / "mau-eform" / "2093.json"
# URL trang kê khai thật (ca Khánh Hòa 13/11): DVCQG chọn cơ quan xong chuyển sang cổng Bộ Tư pháp.
MOJ_URL = ("https://dichvucongnganhtuphap.moj.gov.vn/nop-ho-so/148562"
           "?tinhThanhId=37&maThuTuc=2.000528&MaDVC=2.000528.01")
MOJ_BODY = ("Thủ tục đăng ký khai sinh có yếu tố nước ngoài Thông tin chủ hồ sơ Kê khai thông tin Thành phần hồ sơ "
            "NỘI DUNG MẪU HỘ TỊCH ĐIỆN TỬ TƯƠNG TÁC ĐĂNG KÝ KHAI SINH THÔNG TIN VỀ NGƯỜI YÊU CẦU ĐĂNG KÝ KHAI SINH "
            "THÔNG TIN VỀ NGƯỜI ĐƯỢC ĐĂNG KÝ KHAI SINH")
MOTHER = {"applicantFullname": "TRAN THI B", "applicantIdentityNumber": "012190000001"}
CONTEXT = (
    "<phan_vai_da_xac_dinh>\n<quan_he>\nKết luận: Mẹ\n</quan_he>\n"
    "<loai_khai_sinh>\nKết luận: Đã xác định được cả cha lẫn mẹ\nĐã có hồ sơ, giấy tờ cá nhân: Không\n"
    "</loai_khai_sinh>\n</phan_vai_da_xac_dinh>"
)
VN_AREA = {"quocGia": "Việt Nam", "tinh": "Tỉnh Lai Châu", "xa": "Phường Tân Phong", "diaChi": "Bản A"}
BASE = {
    "Con_HoTen": "Li Ming (Lý Minh)",
    "Con_NgaySinh": "10/03/2025",
    "Con_GioiTinh": "Nữ",
    "Con_DanToc": "Hán",
    "Con_QuocTich": "TRUNG QUỐC",
    "Con_NoiSinh": VN_AREA,
    "Con_QueQuan": {"quocGia": "Trung Quốc", "tinh": "Tỉnh Quảng Đông", "xa": "Thành phố Quảng Châu"},
    "Me_HoTen": "Trần Thị B",
    "Me_SoDinhDanh": "012190000001",
    "Me_SoGiayTo": "012190000001",
    "Me_NgaySinh": "01/02/1995",
    "Me_QuocTich": "Việt Nam",
    "Me_DanToc": "Dao",
    "Me_NoiCuTru": VN_AREA,
    "Cha_HoTen": "Li Gang",
    "Cha_QuocTich": "Cộng hòa nhân dân Trung Hoa",
    "Cha_DanToc": "Hán",
    "Cha_LoaiGiayTo": "Hộ chiếu",
    "Cha_SoGiayTo": "EA1234567",
    "Cha_NgaySinh": "05/06/1985",
    "Cha_NgayCap": "02/03/2023",
    "Cha_NoiCuTru": VN_AREA,
    "Cha_LoaiCuTru": "Tạm trú",
}


def _fold(value: str) -> str:
    text = unicodedata.normalize("NFD", value).replace("Đ", "D").replace("đ", "d")
    return re.sub(r"[^a-z0-9]+", " ", "".join(c for c in text if unicodedata.category(c) != "Mn").lower()).strip()


def _entry(key: str) -> dict:
    return next(p for p in PROCEDURES if p["key"] == key)


def _enrich(values: dict, account=MOTHER):
    fields = [{"name": k, "comp": "x-input", "value": v} for k, v in values.items()]
    out, warnings = mapper.enrich(fields, {"formContext": account, "_reasoning_context": CONTEXT})
    return out, {f["name"]: f for f in out}, warnings


# ── Registry / nhận diện ──

def test_registry_nhan_dien_theo_ma_tren_cong_bo_tu_phap():
    entry = _entry(KEY)
    link = next(item for item in json.loads(LINKS.read_text(encoding="utf-8"))["links"] if item["key"] == KEY)
    assert link["code"] == "2.000528"
    assert entry["detect"] == {"urlIncludes": ["maThuTuc=2.000528"]}
    assert entry["supportsSplitDocuments"] is True and entry["hasAttachmentStep"] is True
    assert get_pipeline(KEY).__module__ == "app.pipelines.khai_sinh_nuoc_ngoai.process.runner"
    assert get_attach_pipeline(KEY).__module__ == "app.pipelines.khai_sinh_nuoc_ngoai.attach.planner"


def _scope_ok(detect: dict, url: str) -> bool:
    scope = detect.get("urlScope") or []
    return not scope or any(part and part.lower() in url for part in scope)


def test_trang_cong_bo_tu_phap_tu_nhan_dien():
    """Mô phỏng popup.js: bước 0 (textPriority) không rule nào cướp, bước 1 (urlIncludes) chỉ khớp 2.000528."""
    url, body = MOJ_URL.lower(), _fold(MOJ_BODY)
    priority = [
        p["key"] for p in PROCEDURES
        if (d := p.get("detect") or {}).get("textPriority") and _scope_ok(d, url)
        and d.get("textIncludes") and all(_fold(x) in body for x in d["textIncludes"])
    ]
    assert priority == []
    by_url = [
        p["key"] for p in PROCEDURES
        if _scope_ok(d := p.get("detect") or {}, url) and any(u and u.lower() in url for u in d.get("urlIncludes") or [])
    ]
    assert by_url == [KEY]


# ── Mapper ──

def test_ten_o_va_comp_dung_mau_eform_2093():
    """Extension tìm ô theo `<comp name=...>`: tên + comp phải đúng mẫu eForm khai sinh thật."""
    template = {name: f["type"] for name, f in json.loads(EFORM_2093.read_text(encoding="utf-8"))["fields"].items()}
    out, _, _ = _enrich({**BASE, "SoLuongBanSao": "1", **REQUESTER_GRANDMA}, OTHER_ACCOUNT)
    assert out
    # Ô số bản là input trần trong x-select-area "ThongTin"; Loại khai sinh: cổng hiện dựng <x-select> (mẫu chụp
    # 26/9 ghi x-select-default — ca 13/11 extension không tìm thấy ô theo thẻ cũ).
    exceptions = {"SoLuong": "raw", "nksLoaiKhaiSinh": "x-select"}
    for field in out:
        assert field["comp"] == UI_COMP_BY_NAME[field["name"]]
        assert exceptions.get(field["name"], template[field["name"]]) == field["comp"], field["name"]
    assert template["nksLoaiKhaiSinh"] == "x-select-default"
    assert {"HoVaTenC", "NgayCapDDC", "nksLoaiKhaiSinh", "SoLuong"} <= {f["name"] for f in out}
    assert {"Me_LoaiCuTru", "Cha_LoaiCuTru", "Con_QueQuan"} <= ALLOWED
    assert not [f for f in out if f["name"].startswith("citizen")]


def test_que_quan_nuoc_ngoai_chon_khac_va_quoc_gia():
    out, by, warnings = _enrich(BASE)
    names = [f["name"] for f in out]
    assert by["nksQueQuan"]["value"] == "2"
    area = by["nksQueQuan_NuocNgoai"]
    assert area["comp"] == "x-select-area"
    assert area["value"] == {"quocGia": "Trung Quốc", "diaChi": "Thành phố Quảng Châu, Tỉnh Quảng Đông"}
    assert names.index("nksQueQuan") < names.index("nksQueQuan_NuocNgoai")
    assert "nksQueQuan_TrongNuoc" not in by
    # Nơi sinh ở Việt Nam vẫn đi đường của 1.001193.
    assert by["nksNoiSinh"]["value"] == "1" and by["nksNoiSinh_TrongNuoc"]["value"]["tinh"]
    assert by["LoaiDangKy"]["value"] in ("Đăng ký đúng hạn", "Đăng ký quá hạn")
    assert by["nksLoaiKhaiSinh"]["value"] == "Đã xác định được cả cha lẫn mẹ"
    assert not warnings


def test_quoc_tich_dan_toc_giay_to_nguoi_nuoc_ngoai():
    _, by, _ = _enrich(BASE)
    assert by["HoTenKS"]["value"] == "LI MING (LÝ MINH)"
    assert by["QuocTichKS"]["value"] == "Trung Quốc"
    assert by["QuocTichChaKS"]["value"] == "Trung Quốc"
    # Danh mục dân tộc của eForm có "Người nước ngoài", không có "Hán"; đọc từ giấy nên không viền vàng.
    assert by["DanTocKS"]["value"] == mapper.NGUOI_NUOC_NGOAI and not by["DanTocKS"].get("default")
    assert by["DanTocChaKS"]["value"] == mapper.NGUOI_NUOC_NGOAI
    assert by["DanTocMeKS"]["value"] == "Dao"
    assert by["LoaiGiayToDinhDanhCha"]["value"] == "Hộ chiếu"
    assert by["SoGiayToDinhDanhCha"]["value"] == "EA1234567"
    assert "SoDinhDanhCha" not in by
    assert by["SoDinhDanhMe"]["value"] == "012190000001" and by["NamSinhMeKS"]["value"] == "01/02/1995"
    assert by["ChaLoaiCuTru"]["value"] == "Tạm trú" and not by["ChaLoaiCuTru"].get("default")
    assert by["MeLoaiCuTru"]["value"] == "Thường trú" and by["MeLoaiCuTru"]["default"]


def test_the_cu_dan_nuoc_ngoai_la_giay_to_khac():
    values = {**BASE, "Cha_LoaiGiayTo": "Chứng minh nhân dân", "Cha_SoGiayTo": "440100198501010000",
              "Cha_DanToc": ""}
    _, by, _ = _enrich(values)
    assert by["LoaiGiayToDinhDanhCha"]["value"] == mapper.GIAY_TO_KHAC
    # Không có dân tộc trên giấy → vẫn chọn "Người nước ngoài" nhưng viền vàng.
    assert by["DanTocChaKS"]["value"] == mapper.NGUOI_NUOC_NGOAI and by["DanTocChaKS"]["default"]


def test_khong_ghi_quoc_tich_con_thi_de_trong():
    values = {k: v for k, v in BASE.items() if k not in ("Con_QuocTich", "Con_DanToc")}
    _, by, warnings = _enrich(values)
    assert "QuocTichKS" not in by          # 1.001193 mặc định Việt Nam; ở đây không đoán
    assert "DanTocKS" not in by
    assert any("thỏa thuận lựa chọn quốc tịch" in w for w in warnings)


def test_cha_cu_tru_o_nuoc_ngoai():
    values = {**BASE, "Cha_NoiCuTru": {"quocGia": "Trung Quốc", "tinh": "Tỉnh Quảng Đông",
                                       "xa": "Thành phố Quảng Châu", "diaChi": "Số 8 đường X"},
              "Cha_LoaiCuTru": ""}
    out, by, _ = _enrich(values)
    names = [f["name"] for f in out]
    assert by["ChaNoiCuTru"]["value"] == "2"
    assert by["ChaNoiCuTru_NuocNgoai"]["value"] == {
        "quocGia": "Trung Quốc", "diaChi": "Số 8 đường X, Thành phố Quảng Châu, Tỉnh Quảng Đông"}
    assert names.index("ChaNoiCuTru") < names.index("ChaNoiCuTru_NuocNgoai")
    assert by["ChaLoaiCuTru"]["value"] == "Thường trú" and by["ChaLoaiCuTru"]["default"]
    assert "ChaNoiCuTru_TrongNuoc" not in by
    # Cha đã chết → không dựng khối nơi cư trú.
    _, by, _ = _enrich({**values, "Cha_DaChet": True})
    assert "ChaNoiCuTru" not in by and "ChaLoaiCuTru" not in by


def test_me_nop_thi_quan_he_me_va_noi_cu_tru_muc_i_theo_me():
    out, by, _ = _enrich(BASE)
    names = [f["name"] for f in out]
    # Thứ tự như khai sinh thường: Loại đăng ký, Loại khai sinh, Quan hệ, rồi mục I.
    assert names[:3] == ["LoaiDangKy", "nksLoaiKhaiSinh", "QuanHe"] and by["QuanHe"]["value"] == "MeDe"
    assert by["nksLoaiKhaiSinh"]["comp"] == "x-select"
    assert by["nycNoiCuTru"]["value"] == "1"
    assert by["nycNoiCuTru_TrongNuoc"]["value"] == by["MeNoiCuTru_TrongNuoc"]["value"]
    assert by["nycLoaiCuTru"]["value"] == "Thường trú" and by["nycLoaiCuTru"]["default"]
    assert names.index("nycNoiCuTru") < names.index("nycNoiCuTru_TrongNuoc") < names.index("HoTenKS")
    # Mẹ chính là tài khoản → cổng đã đổ đúng nhân thân mục I, không ghi đè.
    assert "HoVaTenC" not in by


OTHER_ACCOUNT = {"applicantFullname": "NGUYEN VAN C", "applicantIdentityNumber": "001090000009"}
REQUESTER_MOTHER = {"NguoiYeuCau_HoTen": "Trần Thị B", "NguoiYeuCau_SoDinhDanh": "012190000001",
                    "NguoiYeuCau_QuanHe": "Mẹ"}
REQUESTER_GRANDMA = {"NguoiYeuCau_HoTen": "Lê Thị D", "NguoiYeuCau_SoDinhDanh": "012160000002",
                     "NguoiYeuCau_QuanHe": "Bà ngoại"}


def test_nop_ho_thi_muc_i_theo_nguoi_yeu_cau_tren_to_khai_la_me():
    values = {**BASE, **REQUESTER_MOTHER, "Me_NgayCap": "01/02/2021", "Me_NoiCap": "Cục Cảnh sát quản lý hành chính "
                                                                                   "về trật tự xã hội"}
    out, by, warnings = _enrich(values, OTHER_ACCOUNT)
    names = [f["name"] for f in out]
    assert by["QuanHe"]["value"] == "MeDe"
    assert by["HoVaTenC"]["value"] == by["HoTenMeKS"]["value"] == "TRẦN THỊ B"
    assert by["SoDinhDanhC"]["value"] == by["SoGiayToDinhDanhC"]["value"] == "012190000001"
    assert by["LoaiGiayToDinhDanhC"]["value"] == by["LoaiGiayToDinhDanhMe"]["value"]
    assert by["NgayCapDDC"]["value"] == "01/02/2021" and by["NoiCapDDC"]["value"] == by["NoiCapDDMe"]["value"]
    assert by["nycNoiCuTru_TrongNuoc"]["value"] == by["MeNoiCuTru_TrongNuoc"]["value"]
    assert names.index("QuanHe") < names.index("HoVaTenC") < names.index("nycNoiCuTru") < names.index("HoTenKS")
    assert not any("Quan hệ" in w or "quan hệ người nộp" in w for w in warnings)
    # Giấy không có ngày cấp / cơ quan cấp của mẹ → xoá ô cổng đổ theo tài khoản, không để của người khác.
    _, by, _ = _enrich({**BASE, **REQUESTER_MOTHER}, OTHER_ACCOUNT)
    assert by["NgayCapDDC"] == {"name": "NgayCapDDC", "comp": "x-date", "value": "", "clear": True}
    assert by["NoiCapDDC"]["clear"] is True and by["HoVaTenC"]["value"] == "TRẦN THỊ B"


def test_nop_ho_nguoi_yeu_cau_khong_phai_cha_me():
    out, by, warnings = _enrich({**BASE, **REQUESTER_GRANDMA}, OTHER_ACCOUNT)
    assert by["QuanHe"]["value"] == mapper.QUAN_HE_KHAC
    assert by["HoVaTenC"]["value"] == "LÊ THỊ D"
    assert by["SoDinhDanhC"]["value"] == by["SoGiayToDinhDanhC"]["value"] == "012160000002"
    for name in ("NgayCapDDC", "NoiCapDDC"):
        assert by[name]["clear"] is True, name
    # Ô chọn không phát lệnh xoá (trợ lý sẽ chọn nhầm option đầu) → giữ loại giấy tờ cổng đã đổ.
    assert "LoaiGiayToDinhDanhC" not in by
    assert not [f for f in out if f.get("clear") and f["comp"] == "x-select"]
    # Không biết nơi cư trú của người yêu cầu → để trống, báo cán bộ; không lấy địa chỉ của tài khoản.
    assert "nycNoiCuTru" not in by and mapper.REQUESTER_NO_RESIDENCE_WARNING in warnings
    # Người yêu cầu trên tờ khai chính là tài khoản → giữ mục I cổng đã đổ.
    _, by, _ = _enrich({**BASE, **REQUESTER_GRANDMA},
                       {"applicantFullname": "LÊ THỊ D", "applicantIdentityNumber": "012160000002"})
    assert "HoVaTenC" not in by and "SoDinhDanhC" not in by


def test_nguoi_khac_nop_thi_noi_cu_tru_muc_i_theo_tai_khoan():
    account = {"applicantFullname": "NGUYEN VAN C", "applicantIdentityNumber": "001090000009",
               "applicantAddress": {"tinh": "Tỉnh Lai Châu", "xa": "Phường Tân Phong", "diaChi": "Số 1 tổ 2"}}
    _, by, warnings = _enrich(BASE, account)
    assert by["QuanHe"]["value"] == mapper.QUAN_HE_KHAC
    area = by["nycNoiCuTru_TrongNuoc"]["value"]
    assert "Lai Châu" in area["tinh"] and area["diaChi"] == "Số 1 tổ 2"
    assert by["nycNoiCuTru"]["value"] == "1" and by["nycLoaiCuTru"]["default"]
    assert any("'Khác' ở ô Quan hệ" in w for w in warnings)
    assert not any("Quan hệ khác" in w for w in warnings)
    # Không có tài khoản, không phải mẹ / cha → để trống mục I cho người dùng chọn.
    _, by, _ = _enrich(BASE, {"applicantFullname": "NGUYEN VAN C", "applicantIdentityNumber": "001090000009"})
    assert "nycNoiCuTru" not in by and "nycLoaiCuTru" not in by


def test_de_nghi_cap_ban_sao():
    _, by, _ = _enrich({**BASE, "SoLuongBanSao": "2"})
    assert by["CapBanSao"]["value"] == mapper.CAP_BAN_SAO_CO and by["SoLuong"]["value"] == "2"
    _, by, _ = _enrich({**BASE, "SoLuongBanSao": "0"})
    assert by["CapBanSao"]["value"] == mapper.CAP_BAN_SAO_KHONG and "SoLuong" not in by
    _, by, _ = _enrich(BASE)
    assert "CapBanSao" not in by


# ── Đính kèm ──

def _files(*names):
    return [FileItem(name=n, type="application/pdf", dataUrl="data:,", role="") for n in names]


def test_bang_dong_dinh_kem():
    items = build_plan_items(["gcs.pdf", "tt.pdf", "hc.pdf", "uq.pdf", "x.pdf"],
                             {0: BIRTH_CERTIFICATE, 1: "nationality_agreement", 2: "other", 3: "authorization",
                              4: "foreign_birth_doc"},
                             {0: "Giấy chứng sinh", 1: "Văn bản thỏa thuận lựa chọn quốc tịch", 2: "Hộ chiếu",
                              3: "Giấy ủy quyền", 4: "Giấy khai sinh nước ngoài"})
    got = [(i["documentName"], i["target"], i["componentIndex"], i["needsAddComponent"]) for i in items]
    assert got == [
        ("Giấy chứng sinh", "existing", 2, False),
        ("Văn bản thỏa thuận lựa chọn quốc tịch", "existing", 5, False),
        ("Hộ chiếu", "new", None, True),           # giấy không có dòng riêng → thêm thành phần hồ sơ
        ("Giấy ủy quyền", "existing", 6, False),
        ("Giấy khai sinh nước ngoài", "existing", 4, False),
    ]
    assert items[2]["componentName"] == "Hộ chiếu"


_PORTAL_ROWS = [
    "Tờ khai đăng ký khai sinh (Mẫu hộ tịch điện tử tương tác)",
    "Giấy chứng sinh Bắt buộc",
    "Trường hợp không có Giấy chứng sinh thì thay thế bằng: văn bản của người làm chứng xác nhận về việc sinh",
    "Trường hợp trẻ em sinh ra tại nước ngoài thì nộp Giấy chứng sinh hoặc giấy tờ khác",
    "- Trường hợp cha hoặc mẹ hoặc cả cha, mẹ là người nước ngoài thì phải nộp văn bản thỏa thuận lựa chọn quốc tịch",
    "- Văn bản ủy quyền (được chứng thực) theo quy định của pháp luật",
]


def _context(rows):
    return {"attachmentContext": {"components": [{"index": i + 1, "componentName": n} for i, n in enumerate(rows)]}}


def test_dong_lay_theo_bang_that_tren_trang():
    rows = live_rows(_context(_PORTAL_ROWS))
    assert {k: v["componentIndex"] for k, v in rows.items()} == {
        BIRTH_CERTIFICATE: 2, "birth_witness": 3, "foreign_birth_doc": 4, "nationality_agreement": 5,
        "authorization": 6}
    assert rows["authorization"]["componentName"] == _PORTAL_ROWS[5]
    # Cổng xếp khác thứ tự → theo đúng bảng trang.
    shuffled = [_PORTAL_ROWS[0], _PORTAL_ROWS[5], _PORTAL_ROWS[1], _PORTAL_ROWS[4]]
    rows = live_rows(_context(shuffled))
    assert rows["authorization"]["componentIndex"] == 2 and rows[BIRTH_CERTIFICATE]["componentIndex"] == 3
    assert rows["nationality_agreement"]["componentIndex"] == 4
    assert rows["birth_witness"] == ROWS["birth_witness"]  # dòng không có trên trang → giữ mặc định
    # Đoạn tên mặc định nằm trong đúng dòng của cổng (extension khớp theo chữ chứa nhau).
    for key, row in ROWS.items():
        hits = [i for i, text in enumerate(_PORTAL_ROWS) if _fold(row["componentName"]) in _fold(text)]
        assert hits and hits[0] + 1 == row["componentIndex"], key


def test_thieu_giay_chung_sinh_thi_doi_giay_dau_len_dong_bat_buoc():
    items = build_plan_items(["cccd.pdf", "hoso.pdf"], {0: "other", 1: "other"},
                             {0: "Căn cước công dân", 1: "Tờ khai đăng ký khai sinh"})
    promote_birth_row(items, {0})
    assert items[0]["target"] == "new"          # thẻ CCCD không lên dòng Giấy chứng sinh
    assert (items[1]["target"], items[1]["componentIndex"]) == ("existing", 2)
    # Đã có giấy chứng sinh → giữ nguyên.
    items = build_plan_items(["a.pdf", "b.pdf"], {0: "other", 1: BIRTH_CERTIFICATE}, {0: "Hộ chiếu"})
    promote_birth_row(items, set())
    assert items[0]["target"] == "new"


_PAGES = ["TỜ KHAI ĐĂNG KÝ KHAI SINH", "GIẤY CHỨNG SINH", "VĂN BẢN THỎA THUẬN CỦA VỢ, CHỒNG VỀ VIỆC LỰA CHỌN QUỐC TỊCH",
          "GIẤY CHỨNG NHẬN KẾT HÔN", "HỘ CHIẾU", "BẢN DỊCH giấy chứng nhận quốc tịch", "LỜI CHỨNG CHỨNG THỰC"]
_OCR = "\n".join(f"───── Trang {i + 1}/{len(_PAGES)} ─────\n{t}" for i, t in enumerate(_PAGES))


def _patch(monkeypatch, documents):
    async def fake_ocr(files):
        return [{"text": _OCR} for _ in files]

    async def fake_chat(messages, max_tokens=None, **_):
        return json.dumps({"documents": documents})

    monkeypatch.setattr(ocr, "ocr_per_file", fake_ocr)
    monkeypatch.setattr(tach.client, "chat", fake_chat)


def test_tach_file_dung_dong_va_khong_sot_trang(monkeypatch):
    _patch(monkeypatch, [
        {"fileIndex": 0, "pages": [1], "docType": "other", "documentName": "Tờ khai đăng ký khai sinh"},
        {"fileIndex": 0, "pages": [2], "docType": BIRTH_CERTIFICATE, "documentName": "Giấy chứng sinh"},
        {"fileIndex": 0, "pages": [3], "docType": "nationality_agreement",
         "documentName": "Văn bản thỏa thuận lựa chọn quốc tịch"},
        {"fileIndex": 0, "pages": [4], "docType": "other", "documentName": "Giấy chứng nhận kết hôn"},
        {"fileIndex": 0, "pages": [5], "docType": "other", "documentName": "Hộ chiếu"},
        {"fileIndex": 0, "pages": [6], "docType": "nationality_agreement",
         "documentName": "Giấy chứng nhận quốc tịch"},
        # trang 7 (lời chứng) LLM bỏ sót → gộp vào giấy liền trước, không mất trang.
    ])
    res = asyncio.run(attach.plan(_files("hoso.pdf"), {"splitDocuments": True, **_context(_PORTAL_ROWS)}))
    got = [(i["documentName"], i["target"], i["componentIndex"], i["sourceSegments"][0]["pageIndexes"])
           for i in res["attachments"]]
    assert got == [
        ("Tờ khai đăng ký khai sinh", "new", None, [0]),
        ("Giấy chứng sinh", "existing", 2, [1]),
        ("Văn bản thỏa thuận lựa chọn quốc tịch", "existing", 5, [2]),
        ("Giấy chứng nhận kết hôn", "new", None, [3]),
        ("Hộ chiếu", "new", None, [4]),
        ("Giấy chứng nhận quốc tịch", "existing", 5, [5, 6]),
    ]
    assert res["attachments"][2]["componentName"] == _PORTAL_ROWS[4]


def test_tat_tach_thi_dinh_nguyen_tep(monkeypatch):
    _patch(monkeypatch, [])

    async def fake_chat(*_a, **_k):
        return '{"documents":[{"index":0,"docType":"nationality_agreement","documentName":"Văn bản thỏa thuận"}]}'

    monkeypatch.setattr(khong_tach.client, "chat", fake_chat)
    for options in ({}, {"splitDocuments": "true"}, None):
        res = asyncio.run(attach.plan(_files("hoso.pdf"), options))
        item = res["attachments"][0]
        assert "sourceSegments" not in item
        assert (item["target"], item["componentIndex"]) == ("existing", ROWS["nationality_agreement"]["componentIndex"])


def test_tach_loi_quay_ve_khong_tach(monkeypatch):
    _patch(monkeypatch, [])
    calls = []

    async def fake_chat(messages, **_):
        calls.append(messages[0]["content"])
        if "TỪNG TRANG" in messages[0]["content"]:
            raise RuntimeError("llm hỏng")
        return '{"documents":[{"index":0,"docType":"other","documentName":"Tờ khai đăng ký khai sinh"}]}'

    monkeypatch.setattr(tach.client, "chat", fake_chat)
    res = asyncio.run(attach.plan(_files("hoso.pdf"), {"splitDocuments": True}))
    item = res["attachments"][0]
    # Tệp gộp duy nhất, không có giấy chứng sinh riêng → lên dòng Giấy chứng sinh bắt buộc.
    assert (item["target"], item["componentName"]) == ("existing", ROWS[BIRTH_CERTIFICATE]["componentName"])
    assert "sourceSegments" not in item
    assert any("(tách)" in e for e in res["errors"])


# ── Trợ lý người dân ──

def test_tro_ly_cung_key_detect_luong_tu_phap_va_hien_o_11_tinh():
    from app.channels.handfree import procedure_registry as handfree
    from app.channels.handfree.chat.field_review import registry as field_review
    from app.channels.handfree.chat.procedure_picker.prompt import PROCEDURE_HINTS

    proc = handfree.get_procedure(KEY)
    assert proc["detect"] == _entry(KEY)["detect"]
    # Wizard 4 bước của cổng Bộ Tư pháp (chủ hồ sơ → kê khai → thành phần → nhận kết quả) như kết hôn.
    assert proc["flowProfile"] == "tu-phap" and proc["supportsSplitDocuments"] is True
    assert handfree.get_owner_info_pipeline(KEY) is not None
    link = next(item for item in json.loads(LINKS.read_text(encoding="utf-8"))["links"] if item["key"] == KEY)
    assert proc["keKhaiUrl"] == link["url"]
    assert handfree._HOAN_THIEN_THEO_TINH[KEY] == handfree._TAT_CA
    assert KEY in PROCEDURE_HINTS
    config = field_review.get(KEY)
    assert "nycNoiCuTru" in config["required"] and "HoTenKS" in config["required"]
