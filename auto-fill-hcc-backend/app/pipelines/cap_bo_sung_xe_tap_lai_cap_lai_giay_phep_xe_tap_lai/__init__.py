"""Pipeline "Cấp bổ sung xe tập lái, cấp lại Giấy phép xe tập lái" (TTHC 1.001751) — cổng DVC Bộ Xây dựng
dvc.moc.gov.vn (Form.io, engine fillFormStandard dom-* + đính kèm attp-row). CÙNG cổng #63 liên vận / cây xanh.

Chủ thể đề nghị là CƠ SỞ ĐÀO TẠO lái xe (tổ chức), người nộp trực tuyến là cá nhân đăng nhập (nộp thay).
  Phần I   Thông tin người nộp → data[...] PHẲNG; chỉ điền khi có CCCD người nộp (không thì để tài khoản tự đổ).
  Phần II  Thông tin chi tiết  → data[organization1/organization2/organization] (cơ quan chủ quản / cơ sở đào
                                  tạo / trường) + DATAGRID xe data[tbantest][i][...] + ký data[TinTTTe/kyTenDongDau].
           ⚠ field-key datagrid KHÔNG trùng nghĩa với nhãn cột (trongtai = Xe của CSĐT, namsanxuat = Xe hợp
           đồng, sokhung = Loại xe, mauson = Số khung, cuakhaunhapxuat = Ghi chú) → map theo THỨ TỰ CỘT.
  Bước 2   Thành phần hồ sơ    → 2 dòng attp-row: (1) Danh sách đề nghị; (2) giấy tờ chứng minh quyền sử dụng
                                  hợp pháp xe (HĐ thuê xe + GCN đăng ký xe + GCN kiểm định).
Bỏ: trường ẩn (note/kinhgui/ownerFullname/thongTinDoanhNghiep/toChucCaNhan), TDTTK (disabled), receivingKind.
"""
