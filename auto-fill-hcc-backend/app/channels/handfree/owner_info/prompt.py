"""Rules for selecting the portal owner before extracting owner-page fields."""

import json

from .schema import ISSUE_PLACE_OPTIONS


def build_rules(owner_context: dict, include_authorization: bool = False) -> str:
    context = {
        "fullName": str(owner_context.get("fullName") or "").strip(),
        "identityNumber": str(owner_context.get("identityNumber") or "").strip(),
        "dateOfBirth": str(owner_context.get("dateOfBirth") or "").strip(),
        "gender": str(owner_context.get("gender") or "").strip(),
    }
    issue_place_options = json.dumps(ISSUE_PLACE_OPTIONS, ensure_ascii=False)
    owner_rules = f"""

<owner_page_task>
Thông tin định danh đang hiển thị trên trang Thông tin chủ hồ sơ:
{json.dumps(context, ensure_ascii=False)}

- Chỉ chọn MỘT người trong tài liệu khớp chủ hồ sơ theo HỌ TÊN HOẶC SỐ ĐỊNH DANH.
- Ưu tiên số định danh khi tài liệu đọc được. Không chọn theo thứ tự file, giới tính hay vai trò.
- Luôn trả Owner_FullName và Owner_IdentityNumber của người đã chọn nếu tài liệu có, để backend
  kiểm tra lại. Nếu không có người nào khớp thì không trả bất kỳ field Owner_* nào.
- KHỐI THÔNG TIN của một người: các dòng liền nhau mô tả cùng một người — dưới cùng một tiêu đề/vai
  (Bên A, Bên B, mục I/II, Người yêu cầu, Ông/Bà…) hoặc trong cùng một câu giới thiệu
  người đó — có họ tên và/hoặc số giấy tờ của người đó. Mọi dòng trong khối (ngày cấp, nơi cấp, nơi cư trú,
  số điện thoại) là của CHÍNH người đó. Khối kết thúc khi sang tiêu đề/vai của người khác hoặc sang mục nội dung.
- Văn bản giữa nhiều bên (hợp đồng, giấy tờ hai bên, đơn, văn bản thỏa thuận…) có nhiều khối: chủ hồ sơ có thể là
  bất kỳ khối nào (kể cả Bên B / bên thứ hai). Chọn khối có họ tên hoặc số giấy tờ khớp chủ hồ sơ, rồi lấy các field từ
  ĐÚNG khối đó. Đọc HẾT từng dòng của khối đã chọn và trả MỌI field Owner_* có giá trị trong khối (ngày cấp, nơi
  cấp, số điện thoại, địa chỉ) — bỏ sót một dòng có giá trị là sai.
- Chuỗi chỉ có dấu chấm/gạch (".…", "....", "___") hoặc nhãn bỏ trống là CHƯA ĐIỀN → không có giá trị. Giá trị
  thật kèm dấu chấm thừa phía sau thì bỏ phần dấu chấm.
- Owner_IssueDate và Owner_IssuePlace lấy từ thẻ căn cước/giấy tờ định danh của đúng người đó, HOẶC từ khối
  thông tin của người đó trong văn bản khi ngày cấp/nơi cấp đi kèm chính số giấy tờ của người đó. Không lấy ngày
  cấp của giấy tờ khác (giấy chứng nhận quyền sử dụng đất, giấy phép…) hay của người khác.
- Owner_IssuePlace CHỈ được là chính xác một chuỗi trong enum sau: {issue_place_options}.
  Chuẩn hóa cách viết OCR/viết tắt về đúng nhãn enum. Nếu không xác định chắc chắn thì bỏ field,
  tuyệt đối không trả nguyên văn hoặc tự tạo tên cơ quan khác.
- Owner_PhoneNumber: dòng "Số điện thoại"/"Điện thoại"/"SĐT"/"ĐT" nằm TRONG khối thông tin của chủ hồ sơ là số
  của chủ hồ sơ → PHẢI trả (đủ chữ số, bỏ dấu cách/chấm). Số nằm cùng khối với họ tên/số giấy tờ đã khớp là
  bằng chứng CHẮC CHẮN, không phải suy đoán — quy tắc "không chắc thì bỏ" không áp ở đây. Không lấy số nằm trong khối của người khác, số của cơ
  quan/văn phòng ở đầu trang, chân trang, con dấu; không có số trong khối của chủ hồ sơ thì bỏ field.
- Owner_DetailedAddress lấy từ dòng nơi cư trú/thường trú/địa chỉ trong khối của chủ hồ sơ (hoặc thẻ căn cước),
  chỉ phần chi tiết như số nhà/thôn/xóm/tổ; bỏ tên xã/phường, huyện và tỉnh.
- Không trộn dữ liệu của nhiều người trong hồ sơ.
</owner_page_task>
"""
    if not include_authorization:
        return owner_rules

    return owner_rules + f"""

<personal_authorization_task>
Nhánh đang thực hiện: Người khác ủy quyền.
Chủ hồ sơ ở trên là người ĐƯỢC ỦY QUYỀN đang đi nộp hồ sơ.

- Chỉ thực hiện phần này khi tài liệu có GIẤY ỦY QUYỀN, VĂN BẢN ỦY QUYỀN hoặc HỢP ĐỒNG ỦY QUYỀN thật.
- Trả Authorization_DocumentTitle theo tiêu đề đọc được của văn bản.
- Tách đúng hai vai trò: người ủy quyền/bên ủy quyền và người được ủy quyền/bên nhận ủy quyền.
- Người được ủy quyền phải khớp thông tin chủ hồ sơ sau; backend sẽ kiểm tra lại:
  {json.dumps(context, ensure_ascii=False)}
- Authorization_RecipientFullName và Authorization_RecipientIdentityNumber lấy từ phần người được
  ủy quyền trên chính văn bản, không lấy đại từ CCCD khác.
- Authorization_GrantorFullName, Authorization_GrantorDateOfBirth và
  Authorization_GrantorIdentityNumber chỉ thuộc người ủy quyền.
- Văn bản ủy quyền LUÔN ghi ngày sinh của CẢ HAI bên, nhưng chỉ có MỘT trường ngày sinh để trả.
  Authorization_GrantorDateOfBirth lấy ngày sinh trong khối BÊN ỦY QUYỀN (bên A, thường là mục
  I); ngày sinh của bên được ủy quyền (bên B) không có chỗ trả, bỏ qua nó. Đọc được ngày sinh
  của bên A thì PHẢI trả — có hai ngày sinh trong tài liệu KHÔNG phải là lý do để bỏ trống.
- Chỉ được dùng giấy tờ định danh khác để bổ sung người ủy quyền khi đã nối chắc chắn bằng họ tên
  hoặc số giấy tờ ghi trên văn bản ủy quyền.
- Authorization_Relationship chỉ trả khi tài liệu ghi rõ quan hệ với người được ủy quyền;
  không suy đoán từ họ tên, địa chỉ hay giới tính.
- Không có văn bản ủy quyền thật, không tách được vai trò, hoặc không chắc đúng người thì không trả
  bất kỳ field Authorization_* nào.
</personal_authorization_task>
"""
