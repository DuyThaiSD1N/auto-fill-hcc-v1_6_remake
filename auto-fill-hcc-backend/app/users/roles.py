"""Định nghĩa role tài khoản dùng chung cho thống kê và báo cáo."""


# Tài khoản CHƯA bị xóa mềm. Xóa tài khoản chỉ đóng dấu `users.deleted_at`, document vẫn nằm
# nguyên trong Mongo — mọi nơi liệt kê tài khoản phải lọc bằng cái này, nếu không tài khoản
# đã xóa vẫn hiện ra như chưa có chuyện gì.
#
# `{"deleted_at": None}` khớp CẢ document chưa từng có trường này (toàn bộ tài khoản tạo
# trước khi có xóa mềm), nên không phải migrate dữ liệu cũ.
#
# NGOẠI LỆ: chỗ tra TÊN để hiển thị lịch sử (traces) KHÔNG được lọc — hồ sơ cũ của một tài
# khoản đã xóa vẫn phải hiện đúng tên người làm.
NOT_DELETED = {"deleted_at": None}


OFFICIAL_ACCOUNT_ROLES = frozenset({"commune", "province"})

# Hành chính công Bộ Công an: tài khoản làm thủ tục của Bộ Công an (cư trú, căn cước, xe, hộ chiếu…).
# KHÔNG thuộc tỉnh nào: vẫn lưu `tinh`/`xa` (cơ quan thực hiện mặc định của vài thủ tục cư trú/căn cước),
# nhưng thống kê/báo cáo xếp mọi tài khoản này vào một nhóm riêng BCA_GROUP ngang hàng các tỉnh — không
# cộng vào tỉnh nào, tài khoản Tỉnh không thấy. Không đưa vào OFFICIAL_ACCOUNT_ROLES: tập đó là đơn vị
# HÀNH CHÍNH của tỉnh (phạm vi tài khoản Tỉnh, chọn tỉnh…).
BCA_ROLE = "bca"
BCA_GROUP = "Bộ Công an"
# Tester HCC Bộ Công an: thử luồng Bộ Công an — cùng giới hạn thủ tục và nhóm "Bộ Công an" như BCA_ROLE, nhưng
# như tài khoản tester ("user"): KHÔNG phải đơn vị báo cáo nên không vào REPORT_UNIT_ROLES.
BCA_TESTER_ROLE = "bca_tester"
BCA_ROLES = frozenset({BCA_ROLE, BCA_TESTER_ROLE})

# Tài khoản là một đơn vị trên báo cáo / thống kê toàn hệ thống (HCC xã, HCC tỉnh, Bộ Công an).
REPORT_UNIT_ROLES = OFFICIAL_ACCOUNT_ROLES | {BCA_ROLE}

# Tổ dân phố: tài khoản CON của một HCC xã (`users.parent_id`), dùng extension như cán bộ xã.
# Không phải một đơn vị: tỉnh/xã chép từ xã cha, số hồ sơ cộng dồn vào xã cha
# (app/stats/cutover.py) nên KHÔNG đưa vào OFFICIAL_ACCOUNT_ROLES — thêm vào là mọc dòng riêng
# trong "Theo đơn vị" và báo cáo.
TDP_ROLE = "tdp"
# Vai trò duy nhất được làm cha của tổ dân phố.
TDP_PARENT_ROLE = "commune"

# Role CHỈ dùng để XEM báo cáo cấp tỉnh trên bảng thống kê (KHÁC "province" của HCC — role đó là
# tài khoản nghiệp vụ cấp tỉnh). Tài khoản này không xử lý hồ sơ; chỉ được xem số liệu tổng hợp của
# mọi phường/xã cùng tỉnh (khóa theo `tinh` của chính tài khoản, không nhận tỉnh/xã từ client).
PROVINCE_ADMIN_ROLE = "province_admin"

# Role nội bộ dành riêng cho web Monitor chứa OCR/LLM và giấy tờ hồ sơ. Không đưa role này
# vào ``users.schemas.Role``: nếu dùng chung enum công khai, trang quản lý tài khoản hiện tại
# sẽ vô tình cho phép admin thường tạo hoặc nâng quyền một tài khoản thành super admin.
SUPER_ADMIN_ROLE = "super_admin"


def normalized_role(value: object) -> str:
    """Tài khoản legacy thiếu role được hiểu là user, không tự nâng thành tài khoản HCC."""
    return str(value or "user")


def is_official_account_role(value: object) -> bool:
    return normalized_role(value) in OFFICIAL_ACCOUNT_ROLES


def is_province_admin_role(value: object) -> bool:
    return normalized_role(value) == PROVINCE_ADMIN_ROLE


def is_bca_role(value: object) -> bool:
    """Tài khoản Bộ Công an (kể cả tester Bộ Công an): chỉ thủ tục Bộ Công an, xếp nhóm "Bộ Công an"."""
    return normalized_role(value) in BCA_ROLES


def is_report_unit_role(value: object) -> bool:
    return normalized_role(value) in REPORT_UNIT_ROLES


def stats_province(user: dict) -> str | None:
    """Tỉnh dùng để xếp nhóm trên thống kê / báo cáo: tài khoản Bộ Công an luôn vào nhóm BCA_GROUP,
    không theo `tinh` đã gán; tài khoản khác giữ `tinh`."""
    if is_bca_role(user.get("role")):
        return BCA_GROUP
    return (user.get("tinh") or "").strip() or None
