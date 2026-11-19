"""Loại giấy trong hồ sơ cấp bản sao văn bằng từ sổ gốc — lựa chọn "thuộc về" của dòng chứng cứ thanh tra."""

PHIEU = "phiếu đề nghị cấp bản sao văn bằng (viết tay)"
VAN_BANG = "văn bằng / bằng tốt nghiệp"
CCCD = "căn cước / CMND của chủ văn bằng"
CCCD_KHAC = "căn cước / CMND của người khác (người nộp thay, cán bộ)"
UY_QUYEN = "giấy ủy quyền"
KHAC = "giấy khác"
OWNERS = (PHIEU, VAN_BANG, CCCD, CCCD_KHAC, UY_QUYEN, KHAC)
