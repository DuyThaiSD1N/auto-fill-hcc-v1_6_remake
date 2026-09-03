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
- Owner_IssueDate và Owner_IssuePlace chỉ lấy từ giấy tờ định danh của đúng người đó.
- Owner_IssuePlace CHỈ được là chính xác một chuỗi trong enum sau: {issue_place_options}.
  Chuẩn hóa cách viết OCR/viết tắt về đúng nhãn enum. Nếu không xác định chắc chắn thì bỏ field,
  tuyệt đối không trả nguyên văn hoặc tự tạo tên cơ quan khác.
- Owner_PhoneNumber chỉ trả khi tài liệu ghi rõ số điện thoại thuộc đúng chủ hồ sơ; không suy đoán
  và không lấy số của bất kỳ người nào khác trong hồ sơ.
- Owner_DetailedAddress chỉ là phần chi tiết như số nhà/thôn/xóm/tổ; bỏ tên xã/phường, huyện và tỉnh.
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
- Chỉ được dùng giấy tờ định danh khác để bổ sung người ủy quyền khi đã nối chắc chắn bằng họ tên
  hoặc số giấy tờ ghi trên văn bản ủy quyền.
- Authorization_Relationship chỉ trả khi tài liệu ghi rõ quan hệ với người được ủy quyền;
  không suy đoán từ họ tên, địa chỉ hay giới tính.
- Không có văn bản ủy quyền thật, không tách được vai trò, hoặc không chắc đúng người thì không trả
  bất kỳ field Authorization_* nào.
</personal_authorization_task>
"""
