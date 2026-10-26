// DANH MỤC THỦ TỤC của web Kiểm thử (cổng 12008). Key theo app/procedures/registry.py; mẫu mô phỏng form lấy ở
// simulations/thu-tuc/<key>/. Thêm thủ tục = thêm một dòng (thủ tục phải có mẫu mô phỏng thì mới chấm được ô đỏ).
//
// - dvc-moi: Cổng DVC quốc gia mới (SurveyJS) — chạy cả điền lẫn đính kèm (bảng thành phần hồ sơ cố định).
// - eform  : eForm Bộ Tư pháp (tokhaidientu.moj.gov.vn) — chỉ điền. Thứ tự theo số lượt thật trong Mongo 25/10/2026.

export interface FormVariant {
  value: string;
  label: string;
  /** Tên ô extension thấy trên trang → BE chỉ nhận biến thể khi đủ chữ ký này (khai_sinh_ket_hop_nhan_cmc). */
  signature: string[];
}

export interface LabProcedure {
  key: string;
  /** Nhãn dự phòng khi /api/v1/procedures chưa tải xong. */
  label: string;
  group: "dvc-moi" | "eform";
  /** Có bước đính kèm để chạy (action=attach). */
  attach: boolean;
  /** Tờ khai đang mở — extension gửi qua formContext, thiếu thì BE trả lỗi không nhận diện được biểu mẫu. */
  variants?: FormVariant[];
}

export const GROUPS: { key: LabProcedure["group"]; label: string; hint: string }[] = [
  { key: "dvc-moi", label: "Cổng DVC quốc gia mới", hint: "Điền + đính kèm" },
  { key: "eform", label: "eForm tư pháp", hint: "Chỉ điền" },
];

export const LAB_PROCEDURES: LabProcedure[] = [
  { key: "khai-sinh-dang-ky-thuong", label: "Thủ tục đăng ký khai sinh", group: "dvc-moi", attach: true },
  { key: "khai-tu", label: "Thủ tục đăng ký khai tử", group: "dvc-moi", attach: true },
  { key: "trich-luc-ks", label: "Cấp bản sao Trích lục hộ tịch, bản sao Giấy khai sinh", group: "dvc-moi", attach: true },
  { key: "xac-nhan-tinh-trang-hon-nhan", label: "Thủ tục cấp Giấy xác nhận tình trạng hôn nhân", group: "dvc-moi", attach: true },
  { key: "thay-doi-cai-chinh-ho-tich", label: "Thay đổi, cải chính, bổ sung thông tin hộ tịch, xác định lại dân tộc", group: "dvc-moi", attach: true },

  { key: "khai-sinh-dang-ky-lai", label: "Thủ tục đăng ký lại khai sinh", group: "eform", attach: false },
  { key: "ket-hon", label: "Thủ tục đăng ký kết hôn", group: "eform", attach: false },
  {
    key: "khai-sinh-ket-hop-nhan-cha-me-con",
    label: "Thủ tục đăng ký khai sinh kết hợp đăng ký nhận cha, mẹ, con",
    group: "eform",
    attach: false,
    variants: [
      { value: "birth_registration", label: "Tờ khai đăng ký khai sinh", signature: ["HoTenKS", "HoTenMeKS", "HoTenChaKS"] },
      { value: "parent_child_recognition", label: "Tờ khai nhận cha, mẹ, con", signature: ["HotenA", "hotenB", "loaiXacNhan"] },
    ],
  },
  { key: "dang-ky-lai-ket-hon", label: "Thủ tục đăng ký lại kết hôn", group: "eform", attach: false },
  { key: "khai-sinh-da-co-ho-so", label: "Thủ tục đăng ký khai sinh cho người đã có hồ sơ, giấy tờ cá nhân", group: "eform", attach: false },
  { key: "ket-hon-nuoc-ngoai", label: "Thủ tục đăng ký kết hôn có yếu tố nước ngoài", group: "eform", attach: false },
  { key: "dang-ky-nhan-cha-me-con", label: "Thủ tục đăng ký nhận cha, mẹ, con", group: "eform", attach: false },
];

export function findLabProcedure(key: string | null | undefined): LabProcedure | undefined {
  return LAB_PROCEDURES.find((p) => p.key === key);
}
