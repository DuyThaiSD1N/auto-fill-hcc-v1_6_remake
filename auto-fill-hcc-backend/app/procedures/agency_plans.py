"""Kế hoạch điền hộ khối "Chọn cơ quan thực hiện" — bước đầu của một số cổng.

Vì sao tách ra file riêng: kế hoạch này được HAI registry dùng chung —
  - `app/procedures/registry.py`      → extension Auto Fill (no handfree) nạp qua /api/v1/procedures,
  - `app/channels/handfree/procedure_registry.py` → trợ lý Handfree phát qua action fill_agency_plan.
Chép thành hai bản là sớm muộn sửa một bên, bên kia lặng lẽ giữ giá trị cũ — mà sai ở đây thì
hồ sơ nộp lên SAI CƠ QUAN, không ai phát hiện tới lúc bị trả lại.

Định dạng theo đúng hợp đồng fields {name, comp, value} của engine fill-angular (cả hai bản
extension dùng chung engine này, đã đối chiếu: cùng tập comp select / diachi / checkbox).
`{province}` / `{ward}` là chỗ trống cho nơi làm thủ tục; phía gọi thay trước khi gửi xuống:
Handfree thay bằng nơi ở của phiên, Auto Fill thay bằng tỉnh/xã đang chọn ở popup.
"""

# Liên thông khai sinh (lienthong.dichvucong.gov.vn — Angular Material), bước 01.
#
# CHỈ điền những ô người dùng thật phải chạm. Bỏ hẳn:
#   - "Cơ quan thực hiện" (CqdkksTenCoQuan, CqdkttTenCoQuan, BhxhTenCoQuan, CapTheCCTenCoQuan):
#     readonly, cổng tự suy từ tỉnh/xã;
#   - toàn bộ khối THƯỜNG TRÚ: tick "Cùng địa bàn" (CqdkttIsDkks) là cổng tự mirror và khoá lại;
#   - "Cấp tỉnh/Cấp Xã-Phường" của thẻ căn cước (CapTheCCLoaiCap): tick IsCapTheCanCuoc xong cổng
#     tự chọn mặc định Xã/Phường và tự điền địa chỉ.
# Điền thừa những ô đó là ghi đè lên giá trị cổng vừa tự suy — sinh lỗi khó đoán.
LIEN_THONG_KHAI_SINH = [
    {"name": "IsNuocNgoai", "comp": "select", "value": "Không có yếu tố nước ngoài"},
    {"name": "CqdkksDiaChi", "comp": "diachi",
     "value": {"tinh": "{province}", "xa": "{ward}"}},
    {"name": "DkksTruongHop", "comp": "select", "value": "Đã xác định được cả cha lẫn mẹ"},
    {"name": "CqdkttIsDkks", "comp": "checkbox", "value": True},
    {"name": "DkttTruongHop", "comp": "select",
     "value": "Con về với cha, mẹ; cha, mẹ là chủ sở hữu chỗ ở hợp pháp"},
    {"name": "IsCapTheCanCuoc", "comp": "checkbox", "value": True},
]
