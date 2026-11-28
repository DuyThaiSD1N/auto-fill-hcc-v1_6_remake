"""Schema "Đăng ký thành lập hộ kinh doanh" (1.001612) trên Cổng DVC quốc gia mới.

Dữ kiện LLM trả GIỮ NGUYÊN tên của bản HkdOnline (``dang_ky_kinh_doanh``) để dùng chung luật đọc, lượt đọc ảnh dự
phòng, sửa dấu tên hộ và sửa tỉnh/xã theo OCR; chỉ thêm các field biểu mẫu mới tách riêng (thường trú / nơi ở hiện tại,
dân tộc, quốc tịch chủ hộ, email + nơi ở người được ủy quyền, chủ thể thành lập, không kinh doanh tại trụ sở).
"""

from typing import Literal

from pydantic import BaseModel, Field

from app.pipelines.dang_ky_kinh_doanh.giay_de_nghi.fill import DiaChi, GiayDeNghi
from app.pipelines.dang_ky_kinh_doanh.process.schema import COMPACT_COMP_BY_NAME as _HKD_COMP
from app.pipelines.dang_ky_kinh_doanh.process.schema import FIELDS as _HKD_FIELDS

FIELDS: list[dict] = [
    *_HKD_FIELDS,
    {"name": "ChuHo_NoiThuongTru",
     "desc": 'Mục "Nơi thường trú" của chủ hộ trên Giấy đề nghị, object {quocGia,tinh,xa,chiTietDuoiXa}; giấy để trống '
             'thì lấy dòng "Nơi thường trú / Nơi cư trú" trên CCCD của chính chủ hộ.'},
    {"name": "ChuHo_NoiOHienTai",
     "desc": 'Mục "Nơi ở hiện tại" của chủ hộ trên Giấy đề nghị, object {quocGia,tinh,xa,chiTietDuoiXa}; để trống → bỏ.'},
    {"name": "ChuHo_DanToc", "desc": "Dân tộc của chủ hộ (Giấy đề nghị / giấy ủy quyền), vd \"Kinh\"."},
    {"name": "ChuHo_QuocTich", "desc": "Quốc tịch của chủ hộ, vd \"Việt Nam\"."},
    {"name": "UyQuyen_NguoiDuocUyQuyen_Email", "desc": "Thư điện tử của bên được ủy quyền nếu giấy ủy quyền có ghi."},
    {"name": "UyQuyen_NguoiDuocUyQuyen_NoiOHienTai",
     "desc": 'Dòng "Nơi ở hiện tại" của bên được ủy quyền trên giấy ủy quyền, object {quocGia,tinh,xa,chiTietDuoiXa}.'},
    {"name": "ChuTheThanhLap",
     "desc": 'Mục 6 "Chủ thể thành lập hộ kinh doanh": "Cá nhân" hoặc "Các thành viên hộ gia đình" theo ô được đánh '
             'dấu; không đánh dấu → bỏ.'},
    {"name": "TruSo_KhongKinhDoanhTaiTruSo",
     "desc": 'true khi ô "Không kinh doanh tại trụ sở" ở mục 2 được đánh dấu (☒/X); ô trống → bỏ.'},
    {"name": "ThanhVien_DanhSach",
     "desc": ('Bảng mục 7 "Thông tin về các thành viên hộ gia đình" của Giấy đề nghị, array object '
              '{hoTen,ngaySinh,soDinhDanh,gioiTinh,quocTich,danToc,noiThuongTru,noiOHienTai}: MỖI dòng có họ tên là '
              'một object, KỂ CẢ dòng chủ hộ; ngaySinh dd/mm/yyyy; noiThuongTru / noiOHienTai là chữ nguyên văn ô '
              'đó. Bảng trống / chỉ có dấu chấm → bỏ.')},
]

ALLOWED = {f["name"] for f in FIELDS}

COMPACT_COMP_BY_NAME = dict(_HKD_COMP)
for _name in ALLOWED - set(COMPACT_COMP_BY_NAME):
    COMPACT_COMP_BY_NAME[_name] = "x-input"
for _name in ("ChuHo_NoiThuongTru", "ChuHo_NoiOHienTai", "UyQuyen_NguoiDuocUyQuyen_NoiOHienTai"):
    COMPACT_COMP_BY_NAME[_name] = "x-select-area"
COMPACT_COMP_BY_NAME["ThanhVien_DanhSach"] = "raw"

# Radio "Loại người nộp": 1 = chủ hộ tự nộp (khối người nộp cổng đổ từ tài khoản / CSDLQG), 2 = người được ủy quyền
# (khối người nộp theo tài khoản + khối chủ hộ nhập tay). Mapping_Dang_ky_HKD_DVC_Quoc_gia (2 sheet).
LOAI_NGUOI_NOP = "citizenloaitokhai"


# ── Tờ khai cán bộ nhập trên tab "Tạo tờ khai đăng ký hộ kinh doanh" của Auto Fill (không cần quét tờ khai) ──
# Cùng Giấy đề nghị Mẫu số 1 với bản HkdOnline, thêm khối người nộp mà cổng hỏi ĐẦU TIÊN (radio citizenloaitokhai):
# tab bắt chọn trước khi kê khai. Khối này không in lên giấy (mẫu không có), chỉ để Auto Fill điền cổng.
class NguoiNopToKhai(BaseModel):
    loai: Literal["chu_ho", "uy_quyen"]
    # Người được ủy quyền (chỉ khi loai = uy_quyen). Họ tên / số định danh cổng khoá theo tài khoản, chỉ để đối chiếu.
    hoTen: str = Field(default="", max_length=120)
    soDinhDanh: str = Field(default="", max_length=20)
    dienThoai: str = Field(default="", max_length=30)
    email: str = Field(default="", max_length=120)
    noiO: DiaChi = Field(default_factory=DiaChi)


class ToKhaiDvcqg(GiayDeNghi):
    nguoiNop: NguoiNopToKhai

# Ô SurveyJS: name = phần trước hậu tố "__<số>" của data-name (extension khớp theo tiền tố). Ô cổng đặt tên chung
# ("câu hỏi5", "bảng3"…) trùng tiền tố giữa các khối (vd "câu hỏi5" vừa là xã nơi ở người được ủy quyền vừa là điện
# thoại chủ hộ, cùng hiện một lúc) → gửi NGUYÊN data-name kèm hậu tố, extension khớp đúng tên.
UI_COMP_BY_NAME = {
    LOAI_NGUOI_NOP: "sjs-radio",
    # ── Chủ hộ tự nộp: nhân thân + thường trú cổng khoá theo tài khoản ──
    "citizenPhone1": "sjs-text",
    "citizenEmail1": "sjs-text",
    "câu hỏi1__1782221422172": "sjs-text",                    # Nơi ở hiện tại: số nhà, đường
    "tinhThanhhientai": "sjs-dropdown",
    "phuongXahientai": "sjs-dropdown",
    # ── Người được ủy quyền nộp: khối người nộp (tài khoản) ──
    "citizensdt": "sjs-text",
    "citizenEmail": "sjs-text",
    "câu hỏi3__1761724625529": "sjs-text",                    # Nơi ở hiện tại: số nhà, đường
    "câu hỏi4__1761724625529": "sjs-dropdown",                # Nơi ở hiện tại: tỉnh
    "câu hỏi5__1761724625529": "sjs-dropdown",                # Nơi ở hiện tại: phường/xã
    # ── Người được ủy quyền nộp: khối chủ hộ kinh doanh (nhập tay) ──
    "citizennguoidangkyhkd": "sjs-text",
    "citizenngaythang": "sjs-date",
    "citizengioitinhnguoidangky": "sjs-dropdown",
    "SoDinhdanhcanhanNDK": "sjs-text",
    "câu hỏi5__1779097616381": "sjs-text",                    # Điện thoại chủ hộ
    "câu hỏi1__1782891904359": "sjs-text",                    # Fax chủ hộ
    "citizenQuocTich_NDK": "sjs-dropdown",
    "citizenDantoc_NDK": "sjs-dropdown",
    "Diachichitietnoithuongtrunguoidangky": "sjs-text",
    "bảng3__1782890713158": "sjs-dropdown",                   # Thường trú: tỉnh
    "citizenxanguoidangky": "sjs-dropdown",                   # Thường trú: phường/xã
    "Noiohientaichitiet": "sjs-text",
    "Noiohientaitinh": "sjs-dropdown",
    "Noiohientaiphuong": "sjs-dropdown",
    # ── Thông tin hộ kinh doanh (chung hai trường hợp) ──
    "tenHoKinhDoanh": "sjs-text",
    "tenNuocNgoai": "sjs-text",
    "tenVietTat": "sjs-text",
    "diaChiChiTiet": "sjs-text",
    "dienThoai": "sjs-text",
    "fax": "sjs-text",
    "Thudientu": "sjs-text",
    "website": "sjs-text",
    "khongHoatDongTaiTruSo": "sjs-boolean",
    "nganhNgheKinhDoanh": "sjs-matrix",
    "vonKinhDoanh": "sjs-text",
    "câu hỏi7__1782890713158": "sjs-text",                    # Địa chỉ nhận thông báo thuế: số nhà, đường
    "câu hỏi8__1782890713158": "sjs-dropdown",                # … tỉnh
    "câu hỏi9__1782890713158": "sjs-dropdown",                # … phường/xã
    "dienThoaiThue": "sjs-text",
    "emailThue": "sjs-text",
    "ngayBatDauHoatDong": "sjs-date",
    "soLuongLaoDong": "sjs-text",
    "phuongPhapTinhThue": "sjs-radio",
    "doiTuongThanhLap": "sjs-radio",
    # Bảng thành viên hộ gia đình (mapper.MEMBERS_FIELD): tên thật chưa biết, extension tìm bảng theo tiêu đề cột.
    "thanhVienHoGiaDinh": "sjs-matrix",
    # Ô "Hình thức nhận kết quả" (cc-select React ngoài form SurveyJS, không id/name): extension neo theo nhãn.
    "hinhThucNhanKetQua": "dvc-result-method",
}
