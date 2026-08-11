"""Xuất Excel thống kê hồ sơ phát sinh tại các xã/phường Bắc Ninh.

Script dùng chung toàn bộ cách lọc trace, đếm hồ sơ và định dạng Excel với
``export_thong_ke_lai_chau``; phần riêng của Bắc Ninh chỉ là danh sách đơn vị
mặc định và tên file đầu ra. Nhờ vậy cùng một trace luôn được đếm giống nhau
trong hai báo cáo tỉnh.

Cách dùng (chạy tại thư mục gốc backend, cần .env trỏ đúng Mongo):
    python -m scripts.export_thong_ke_bac_ninh
    python -m scripts.export_thong_ke_bac_ninh --out /tmp/thong_ke.xlsx
    python -m scripts.export_thong_ke_bac_ninh --xa "Song Liễu"
    python -m scripts.export_thong_ke_bac_ninh --den "11/08/2026 17:00"

Mỗi sheet: STT | Mã thủ tục | Tên thủ tục | Thủ tục thuộc cấp |
Phạm vi hỗ trợ | Số lượng hồ sơ đã tiếp nhận.
"""
import argparse
import asyncio
from collections.abc import Sequence

from scripts.export_thong_ke_lai_chau import _parse_den, main as export_main


# Tài khoản Bắc Ninh hiện được triển khai tại phường Song Liễu. Giá trị không
# kèm tiền tố "Phường" để khớp quy ước users.xa của script báo cáo hiện tại.
XA_MAC_DINH = ["Song Liễu"]
OUT_MAC_DINH = "thong_ke_bac_ninh.xlsx"


def _parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--xa",
        action="append",
        default=None,
        help="Tên xã/phường (lặp lại nhiều lần); mặc định phường Song Liễu",
    )
    parser.add_argument("--out", default=OUT_MAC_DINH, help="Đường dẫn file Excel xuất ra")
    parser.add_argument(
        "--den",
        default=None,
        help="Mốc kết thúc (giờ VN), vd '11/08/2026 17:00'. Bỏ trống = đến hiện tại",
    )
    return parser.parse_args(argv)


def cli(argv: Sequence[str] | None = None) -> None:
    args = _parse_args(argv)
    asyncio.run(export_main(args.xa or XA_MAC_DINH, args.out, _parse_den(args.den)))


if __name__ == "__main__":
    cli()
