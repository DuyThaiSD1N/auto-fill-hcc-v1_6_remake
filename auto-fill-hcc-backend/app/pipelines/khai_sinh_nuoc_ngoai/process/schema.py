"""Schema cho "Đăng ký khai sinh có yếu tố nước ngoài" (2.000528).

Cổng thật: DVCQG chọn cơ quan xong chuyển sang cổng Bộ Tư pháp (dichvucongnganhtuphap.moj.gov.vn/nop-ho-so?
maThuTuc=2.000528), bước "Kê khai thông tin" là eForm "NỘI DUNG MẪU HỘ TỊCH ĐIỆN TỬ TƯƠNG TÁC ĐĂNG KÝ KHAI SINH" — đúng mẫu
2093 "Đăng ký khai sinh V4" (monitor-fe/src/simulations/mau-eform/2093.json), cùng mẫu khai sinh 1.001193 bản cổng
Bộ Tư pháp. Bản 12/11 đoán nhầm là trang SurveyJS của DVCQG nên ra tên ô `citizen*` (13/11 sửa).

Dữ kiện trích xuất dùng lại schema của khai_sinh_dvc_moi (phân vai cha / mẹ / con giống hệt), thêm loại cư trú của cha
mẹ: cha/mẹ người nước ngoài hay khai "Nơi tạm trú" ở Việt Nam. Mapper dựng trước bộ ô SurveyJS trung gian (dùng lại
toàn bộ luật của khai_sinh_dvc_moi + luật yếu tố nước ngoài) rồi dịch sang ô eForm theo EFORM_NAME.
"""

from app.pipelines.khai_sinh_dvc_moi.process.schema import COMPACT_COMP_BY_NAME as _BASE_COMP
from app.pipelines.khai_sinh_dvc_moi.process.schema import FIELDS as _BASE_FIELDS
from app.pipelines.khai_sinh_dvc_moi.process.schema import UI_COMP_BY_NAME as _BASE_UI


def _loai_cu_tru(prefix: str, label: str) -> dict:
    return {
        "name": f"{prefix}_LoaiCuTru",
        "desc": f'Nhãn dòng nơi cư trú của {label} trên tờ khai: "Nơi tạm trú" → "Tạm trú"; "Nơi thường trú" → '
                f'"Thường trú"; "Nơi ở hiện tại" / "nơi đang sinh sống" → "Nơi ở hiện tại". Nhãn chung "Nơi cư trú" '
                f"hoặc không có tờ khai → bỏ.",
    }


FIELDS: list[dict] = [*_BASE_FIELDS, _loai_cu_tru("Me", "MẸ"), _loai_cu_tru("Cha", "CHA")]

ALLOWED = {f["name"] for f in FIELDS}
ALIASES: dict[str, list[str]] = {}
COMPACT_COMP_BY_NAME = {**_BASE_COMP, "Me_LoaiCuTru": "x-input", "Cha_LoaiCuTru": "x-input"}

# Địa chỉ ở nước ngoài: radio "Khác" + ô gộp "_NuocNgoai" {quocGia, diaChi}. Tên radio là tên ô SurveyJS trung gian.
FOREIGN_AREA_RADIOS = {
    "Con_NoiSinh": "citizenNoisinhnks",
    "Con_QueQuan": "citizenQuequannks",
    "Me_NoiCuTru": "citizenMeNoicutru",
    "Cha_NoiCuTru": "citizenChaNoicutru",
}

# Bộ ô SurveyJS trung gian (mapper của khai_sinh_dvc_moi + nhánh nước ngoài) — KHÔNG gửi ra extension.
SJS_COMP_BY_NAME = {
    **_BASE_UI,
    **{f"{radio}_NuocNgoai": "sjs-area" for radio in FOREIGN_AREA_RADIOS.values()},
}

# Ô SurveyJS trung gian → ô eForm 2093. Ô không có ở đây (citizenField62 "quan hệ khác", số lượng bản sao) mapper dịch
# riêng: eForm không có ô ghi chữ quan hệ, còn bản sao là cặp CapBanSao + SoLuong.
EFORM_NAME = {
    "citizenQuanhevoinguoiduockhaisinh": "QuanHe",
    "citizenLoaiDangKy": "LoaiDangKy",
    "citizenLoaikhaisinh_NgdcKS": "nksLoaiKhaiSinh",
    "citizenHoVaTen_NgdcKS": "HoTenKS",
    "citizenNgaythangnamsinh_NgdcKS": "NgaySinhChon",
    "citizenGioitinh_NgdcKS": "GioiTinhKS",
    "citizenDanToc_NgdcKS": "DanTocKS",
    "citizenQuoctich_NgdcKS": "QuocTichKS",
    "citizenNoisinhnks": "nksNoiSinh",
    "citizenNoisinhnks_TrongNuoc": "nksNoiSinh_TrongNuoc",
    "citizenNoisinhnks_NuocNgoai": "nksNoiSinh_NuocNgoai",
    "citizenQuequannks": "nksQueQuan",
    "citizenQuequannks_TrongNuoc": "nksQueQuan_TrongNuoc",
    "citizenQuequannks_NuocNgoai": "nksQueQuan_NuocNgoai",
    # Mẹ
    "citizenNDK_HoVaTen": "HoTenMeKS",
    "citizenNDK_NgaySinh": "NamSinhMeKS",
    "citizenNDK_SoDinhDanh": "SoDinhDanhMe",
    "citizenLoaiGiaytotuythan_me": "LoaiGiayToDinhDanhMe",
    "citizenSoGiayToTuyThan_me": "SoGiayToDinhDanhMe",
    "citizenNgaythangnamcap__me": "NgayCapDDMe",
    "citizenCoquancap_me": "NoiCapDDMe",
    "citizenDanToc_me": "DanTocMeKS",
    "citizenQuoctich_me": "QuocTichMeKS",
    "citizenMeLoaicutru": "MeLoaiCuTru",
    "citizenMeNoicutru": "MeNoiCuTru",
    "citizenMeNoicutru_TrongNuoc": "MeNoiCuTru_TrongNuoc",
    "citizenMeNoicutru_NuocNgoai": "MeNoiCuTru_NuocNgoai",
    # Cha
    "citizenNDK_HoVaTenCha": "HoTenChaKS",
    "citizenNDK_NgaySinhCha": "NamSinhChaKS",
    "citizenNDK_SoDinhDanhCha": "SoDinhDanhCha",
    "citizenField24": "LoaiGiayToDinhDanhCha",
    "citizenSoGiayToTuyThan_cha": "SoGiayToDinhDanhCha",
    "citizenNgaythangnamcap__cha": "NgayCapDDCha",
    "citizenCoquancap_cha": "NoiCapDDCha",
    "citizenDanToc_cha": "DanTocChaKS",
    "citizenQuoctich_cha": "QuocTichChaKS",
    "citizenChaLoaicutru": "ChaLoaiCuTru",
    "citizenChaNoicutru": "ChaNoiCuTru",
    "citizenChaNoicutru_TrongNuoc": "ChaNoiCuTru_TrongNuoc",
    "citizenChaNoicutru_NuocNgoai": "ChaNoiCuTru_NuocNgoai",
}

# Ô eForm 2093 mapper phát ra: name → comp (thẻ web-component extension tìm theo `<comp name=...>`), đúng như mẫu.
# Thứ tự dict = thứ tự phát ra, chép khai sinh thường (khai_sinh_thuong) đang chạy trên cùng mẫu: Loại đăng ký + Loại
# khai sinh trước (cổng ẩn / hiện khối mẹ, cha theo ô này), Quan hệ, rồi khối người yêu cầu, con, mẹ, cha.
UI_COMP_BY_NAME = {
    "LoaiDangKy": "x-radio",
    # Mẫu 2093 chụp 26/9 ghi x-select-default, nhưng eForm khai sinh trên cổng hiện dựng <x-select
    # name="nksLoaiKhaiSinh"> (1.000689, 1.004772 đã gặp; ca 2.000528 ngày 13/11 ô này không chọn được).
    "nksLoaiKhaiSinh": "x-select",
    "QuanHe": "x-radio",
    # Mục I: cổng đổ sẵn theo tài khoản; có tờ khai thì ghi đè theo người yêu cầu trên tờ khai.
    "HoVaTenC": "x-input",
    "SoDinhDanhC": "x-input",
    "LoaiGiayToDinhDanhC": "x-select",
    "SoGiayToDinhDanhC": "x-input",
    "NgayCapDDC": "x-date",
    "NoiCapDDC": "x-input",
    "nycLoaiCuTru": "x-select",
    "nycNoiCuTru": "x-radio",
    "nycNoiCuTru_TrongNuoc": "x-select-area",
    "nycNoiCuTru_NuocNgoai": "x-select-area",
    "HoTenKS": "x-input",
    "NgaySinhChon": "x-input",
    "GioiTinhKS": "x-select",
    "DanTocKS": "x-select",
    "QuocTichKS": "x-select",
    "nksNoiSinh": "x-radio",
    "nksNoiSinh_TrongNuoc": "x-select-area",
    "nksNoiSinh_NuocNgoai": "x-select-area",
    "nksQueQuan": "x-radio",
    "nksQueQuan_TrongNuoc": "x-select-area",
    "nksQueQuan_NuocNgoai": "x-select-area",
    "HoTenMeKS": "x-input",
    "NamSinhMeKS": "x-date-text",
    "SoDinhDanhMe": "x-input",
    "LoaiGiayToDinhDanhMe": "x-select",
    "SoGiayToDinhDanhMe": "x-input",
    "NgayCapDDMe": "x-date",
    "NoiCapDDMe": "x-input",
    "DanTocMeKS": "x-select",
    "QuocTichMeKS": "x-select",
    "MeLoaiCuTru": "x-select",
    "MeNoiCuTru": "x-radio",
    "MeNoiCuTru_TrongNuoc": "x-select-area",
    "MeNoiCuTru_NuocNgoai": "x-select-area",
    "HoTenChaKS": "x-input",
    "NamSinhChaKS": "x-date-text",
    "SoDinhDanhCha": "x-input",
    "LoaiGiayToDinhDanhCha": "x-select",
    "SoGiayToDinhDanhCha": "x-input",
    "NgayCapDDCha": "x-date",
    "NoiCapDDCha": "x-input",
    "DanTocChaKS": "x-select",
    "QuocTichChaKS": "x-select",
    "ChaLoaiCuTru": "x-select",
    "ChaNoiCuTru": "x-radio",
    "ChaNoiCuTru_TrongNuoc": "x-select-area",
    "ChaNoiCuTru_NuocNgoai": "x-select-area",
    # (27) Đề nghị cấp bản sao: radio Có/Không; ô số bản nằm trong x-select-area "ThongTin" (input trần) như 1.004772.
    "CapBanSao": "x-radio",
    "SoLuong": "raw",
}
