"""Pipeline "Cấp, cấp lại Phù hiệu cho xe ô tô, xe bốn bánh có gắn động cơ kinh doanh vận tải" (TTHC 2.002288) —
cổng DVC Bộ Xây dựng dvc.moc.gov.vn (Form.io, engine fillFormStandard dom-* + đính kèm attp-row). CÙNG cổng
với xe tập lái / liên vận / cây xanh.

Chủ thể đề nghị là ĐƠN VỊ KINH DOANH VẬN TẢI (HTX/doanh nghiệp), người nộp trực tuyến là cá nhân đăng nhập.
  Phần I-II   Người nộp + doanh nghiệp của người nộp → data[...] phẳng (organization/taxCode/province1…).
  Phần III    Giấy đề nghị                          → data[SoVanBan/TinhThanh/DT/T_CoQuan/dichVu].
  Phần IV     Đơn vị KDVT                           → data[T_DonViKinhDoanh][...] (GCN ĐK + GPKDVT).
  Phần V-VII  Thẩm định + phương tiện               → data[ThamDinh][...]; xe nhập qua panel "Thêm phương
                                                      tiện" (comp dom-click mở panel) — một xe mỗi lần.
  Bước 2      Thành phần hồ sơ                      → 2 dòng attp-row: (1) Chứng nhận đăng ký xe (+ hợp đồng
                                                      thuê/dịch vụ nếu xe không thuộc sở hữu đơn vị) — Bản
                                                      sao; (2) Giấy đề nghị cấp (cấp lại) phù hiệu — Bản chính.
Bỏ: trường ẩn (note/noidungyeucaugiaiquyet/ownerFullname/file), chonDoiTuong (disabled), ô file trong tờ khai
(GPKDVT, ảnh xe, đăng ký/hợp đồng trong panel xe), receivingKind, captcha.
"""
