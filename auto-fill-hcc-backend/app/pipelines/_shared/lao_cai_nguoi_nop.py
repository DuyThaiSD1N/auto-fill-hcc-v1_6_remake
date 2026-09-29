"""Quy tắc CHUNG cho khối NGƯỜI NỘP (ô `CongDan_*`) của cổng Lào Cai (dichvucong.laocai.gov.vn, eForm iGate).

Mọi thủ tục Lào Cai dùng cùng một khối người nộp: khi mở trang, script cổng đổ TOÀN BỘ khối từ hồ sơ tài
khoản đang đăng nhập (họ tên, số căn cước, ngày sinh, giới tính, dân tộc, ngày/nơi cấp, tỉnh/xã, địa chỉ,
di động, email, fax), và khi bấm "Đồng ý và tiếp tục" cổng gửi Họ tên + Số Căn cước + Ngày sinh của khối
này sang CSDL quốc gia dân cư để xác thực. Hệ quả cho mapper từng thủ tục:

- Chế độ THEO TÀI KHOẢN: người nộp chính là tài khoản → KHÔNG ghi hai ô readonly `CongDan_tenCongDan` /
  `CongDan_soCmnd` (cổng đã đổ đúng), chỉ bù các ô còn lại bằng giấy tờ của chính người đó.
- Chế độ THEO TỜ KHAI (`options.submitterMode="owner_as_submitter"`): người nộp là người trong hồ sơ, KHÁC
  tài khoản → ghi hai ô readonly theo người đó (đi TRƯỚC các ô khác, vì sửa họ tên làm script cổng xoá
  Di động/Số Căn cước) và XOÁ mọi ô nhân thân cổng đã đổ từ tài khoản mà hồ sơ không có — để sót là khối
  thành nửa của tài khoản, nửa của người trong hồ sơ.
"""

O_READONLY = ("CongDan_tenCongDan", "CongDan_soCmnd")

# Ô nhân thân cổng đổ sẵn từ tài khoản. Ô text xoá bằng chuỗi rỗng; select dân tộc/tỉnh có option
# value="" ("-- Chưa chọn --") nên cũng về rỗng được, và xã tự trống khi tỉnh về "Chưa chọn".
O_NHAN_THAN_XOA_DUOC = (
    "CongDan_ngaySinhCongDan",
    "CongDan_danTocCongDan",
    "CongDan_ngayCapCmnd",
    "CongDan_noiCapCmnd",
    "CongDan_maTinhThanh",
    "CongDan_diaChi",
    "CongDan_diDong",
    "CongDan_email",
    "CongDan_fax",
)

# Mọi form Lào Cai dùng chung bộ ô CongDan_* này; package nào không khai ô trong UI_COMP_BY_NAME (vì
# không có dữ liệu để điền) vẫn phải xoá được giá trị tài khoản cổng đã đổ vào ô đó.
_COMP_MAC_DINH = {
    "CongDan_soCmnd": "dom-input",
    "CongDan_ngaySinhCongDan": "dom-input",
    "CongDan_danTocCongDan": "dom-select",
    "CongDan_ngayCapCmnd": "dom-input",
    "CongDan_noiCapCmnd": "dom-input",
    "CongDan_maTinhThanh": "dom-select",
    "CongDan_diaChi": "dom-input",
    "CongDan_diDong": "dom-input",
    "CongDan_email": "dom-input",
    "CongDan_fax": "dom-input",
}

# Ô không bắt buộc: xoá xong để trống bình thường, không tô đỏ đòi cán bộ nhập.
_O_KHONG_TO_DO = frozenset({"CongDan_email", "CongDan_fax"})

# Select giới tính chỉ có Nam/Nữ, không có option trống → không xoá được.
O_GIOI_TINH = "CongDan_gioiTinhCongDan"

CANH_BAO_GIOI_TINH = (
    "Khối \"Thông tin người nộp\" điền theo TỜ KHAI nhưng hồ sơ không ghi giới tính của người nộp. Ô "
    "\"Giới tính\" của cổng không có lựa chọn trống nên vẫn giữ giá trị cổng đổ từ tài khoản — cán bộ "
    "kiểm tra lại ô này."
)

QUY_TAC_NHAN_THAN_DUNG_NGUOI = """
<nhan_than_dung_nguoi>
- Mỗi cá nhân là MỘT bộ nhân thân: số định danh, ngày sinh, giới tính, dân tộc, ngày cấp, nơi cấp, địa
  chỉ, điện thoại chỉ được lấy ở chỗ ghi GẮN VỚI CHÍNH người đó (cùng dòng/đoạn giới thiệu người đó, hoặc
  thẻ căn cước của người đó).
- Người ký đơn (kể cả ký thay "KT."/"TL."/"TUQ."), người đại diện theo pháp luật ghi trong quyết định hay
  giấy chứng nhận đăng ký doanh nghiệp, người được ủy quyền, người ký ban hành văn bản của cơ quan nhà
  nước là những người KHÁC NHAU, trừ khi trùng cả họ tên lẫn số định danh. Tuyệt đối không lấy nhân thân
  của người này điền cho người kia.
- Khối phẳng ChuHoSo_*/NguoiNop_*: chỉ điền nhân thân của ĐÚNG người mang họ tên ở ChuHoSo_HoTen /
  NguoiNop_HoTen. Hồ sơ không ghi mục nào của chính người đó thì BỎ field đó — không mượn của người khác,
  kể cả khi người khác cùng công ty/cùng hộ.
- Phần "nội dung đã quy định"/"trước khi điều chỉnh" của một quyết định điều chỉnh là thông tin CŨ, không
  dùng làm nhân thân hiện hành của người nộp hay chủ hồ sơ.
</nhan_than_dung_nguoi>
""".strip()


def chot_khoi_nguoi_nop(
    out: list[dict],
    *,
    theo_to_khai: bool,
    comp_by_name: dict[str, str],
    warnings: list[str] | None = None,
    bo_qua: set[str] | frozenset[str] = frozenset(),
) -> list[dict]:
    """Áp quy tắc chung lên danh sách field đã phát của một thủ tục Lào Cai.

    - Theo tài khoản: bỏ hai ô readonly (cổng đã đổ đúng tài khoản).
    - Theo tờ khai, ĐÃ xác định được người nộp (có `CongDan_tenCongDan`): đưa hai ô readonly lên đầu khối
      người nộp và thêm lệnh xoá cho mọi ô nhân thân tài khoản mà hồ sơ không có. Chưa xác định được ai
      thì để nguyên — mapper đã cảnh báo, xoá trắng cả khối chỉ làm cán bộ mất thông tin tài khoản.
    `bo_qua`: ô cổng đang ẩn ở thủ tục đó (phát lệnh xoá cho ô ẩn chỉ làm engine báo "không điền được").
    """
    if not theo_to_khai:
        return [f for f in out if f.get("name") not in O_READONLY]

    names = {f.get("name") for f in out}
    if "CongDan_tenCongDan" not in names:
        # Không có họ tên thì ghi riêng số căn cước là ghép tên tài khoản với số của người khác.
        return [f for f in out if f.get("name") != O_READONLY[1]]

    def lenh_xoa(name: str) -> dict:
        comp = comp_by_name.get(name) or _COMP_MAC_DINH[name]
        # `markEmpty`: extension tô đỏ ô vừa xoá (không có cờ thì chỉ bỏ viền xanh "đã điền").
        return {"name": name, "comp": comp, "value": "", "clear": True,
                "markEmpty": name not in _O_KHONG_TO_DO}

    # Họ tên rồi Số Căn cước (ghi hoặc xoá) — luôn là hai ô đầu của khối người nộp.
    dau = [f for f in out if f.get("name") == O_READONLY[0]]
    dau += [f for f in out if f.get("name") == O_READONLY[1]] or [lenh_xoa(O_READONLY[1])]
    con_lai = [f for f in out if f.get("name") not in O_READONLY]
    xoa = [lenh_xoa(name) for name in O_NHAN_THAN_XOA_DUOC if name not in names and name not in bo_qua]
    if warnings is not None and O_GIOI_TINH not in names and O_GIOI_TINH not in bo_qua:
        warnings.append(CANH_BAO_GIOI_TINH)

    # Hai ô readonly đứng trước ô CongDan_* đầu tiên; lệnh xoá đứng ngay sau ô CongDan_* cuối cùng để
    # engine xử lý hết khối người nộp trước khi sang khối chủ hồ sơ.
    idx_dau = next((i for i, f in enumerate(con_lai) if str(f.get("name", "")).startswith("CongDan_")), 0)
    ket_qua = con_lai[:idx_dau] + dau + con_lai[idx_dau:]
    idx_cuoi = max(
        (i for i, f in enumerate(ket_qua) if str(f.get("name", "")).startswith("CongDan_")),
        default=len(ket_qua) - 1,
    )
    return ket_qua[: idx_cuoi + 1] + xoa + ket_qua[idx_cuoi + 1 :]
