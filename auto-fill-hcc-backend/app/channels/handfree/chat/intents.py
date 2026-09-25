"""Hiểu ý định người dân trong ngữ cảnh state hiện tại (docs/03a §3).

Chọn thủ tục + mọi ý định nói/gõ tự do đều do **LLM** quyết (đưa cả danh sách thủ tục
kèm nhãn/mô tả → LLM trả đúng key), KHÔNG dùng khớp từ khóa. Chỉ 2 thứ giữ tất định vì
là giao thức/đã chắc chắn: lệnh máy `__action:*`/`__event:*` (chip/watcher) và số điện thoại.
LLM lỗi/không chắc → Intent("unknown"); flow hiện lại card cho người dân tự chọn.

Flow KHÔNG gọi LLM trực tiếp — mọi suy đoán gói gọn ở đây (router gọi `resolve`).
"""
import json
import logging
import re
import unicodedata
from dataclasses import dataclass, field

from app.channels.handfree.procedure_registry import public_list
from app.services.llm.client import chat as llm_chat

logger = logging.getLogger(__name__)


@dataclass
class Intent:
    kind: str                      # action | event | pick_procedure | pick_doc_method |
                                   # confirm | deny | provide_phone | ask_question | unknown
    value: str = ""               # action name / event name / procedure_key / doc method...
    payload: dict = field(default_factory=dict)


def fold(s: str) -> str:
    """Bỏ dấu + thường hoá + gộp khoảng trắng — chuẩn khớp text toàn dự án."""
    s = unicodedata.normalize("NFD", str(s or ""))
    s = "".join(ch for ch in s if unicodedata.category(ch) != "Mn")
    return re.sub(r"\s+", " ", s.replace("Đ", "D").replace("đ", "d")).strip().lower()


# Gợi ý cách người dân hay gọi từng thủ tục — CHỈ dùng làm ngữ cảnh cho LLM (không phải bộ
# khớp keyword). Giúp LLM chọn đúng key cho các cách nói dân dã ("lấy vợ nước ngoài"...).
_PROCEDURE_HINTS: dict[str, list[str]] = {
    # Liên thông = khai sinh KÈM đăng ký thường trú + thẻ BHYT cho trẻ dưới 6 tuổi. Câu nói
    # chung chung "đăng ký khai sinh" nay trỏ về bản đơn lẻ bên dưới; chỉ khi công dân nêu rõ
    # liên thông / kèm hộ khẩu / bảo hiểm mới chọn thẻ này.
    "khai-sinh-dang-ky": ["khai sinh liên thông", "làm khai sinh kèm đăng ký thường trú và thẻ bảo hiểm y tế",
                          "khai sinh và nhập hộ khẩu cho trẻ sơ sinh", "liên thông đăng ký khai sinh"],
    "khai-sinh-dang-ky-thuong": ["đăng ký khai sinh", "làm giấy khai sinh cho con", "làm khai sinh",
                                 "khai sinh cho con", "đăng ký khai sinh cho con"],
    "ket-hon": ["đăng ký kết hôn trong nước", "cưới"],
    "khai-tu": ["làm giấy khai tử", "giấy chứng tử", "giấy báo tử"],
    "ket-hon-nuoc-ngoai": ["kết hôn với người nước ngoài", "lấy chồng/vợ nước ngoài",
                           "chồng/vợ là người nước ngoài"],
    "dang-ky-lai-ket-hon": ["đăng ký lại kết hôn", "làm lại giấy kết hôn", "mất giấy kết hôn"],
    "dang-ky-nhan-cha-me-con": ["nhận cha/mẹ/con", "cha nhận con", "con nhận cha/mẹ"],
    "dang-ky-giam-ho": ["đăng ký giám hộ"],
    "trich-luc-ks": ["cấp bản sao giấy khai sinh", "bản sao trích lục hộ tịch"],
    "xac-nhan-tinh-trang-hon-nhan": ["xác nhận độc thân", "xác nhận tình trạng hôn nhân"],
    "thay-doi-cai-chinh-ho-tich": ["cải chính hộ tịch", "thay đổi thông tin hộ tịch",
                                   "sửa thông tin trên giấy khai sinh", "cải chính giấy khai sinh",
                                   "đổi tên trong giấy khai sinh", "xác định lại dân tộc",
                                   "bổ sung thông tin hộ tịch"],
    "dang-ky-kinh-doanh": ["đăng ký thành lập hộ kinh doanh", "mở hộ kinh doanh",
                            "thành lập hộ kinh doanh"],
    # Dân hay gọi "công chứng" thay cho "chứng thực" + gọi kèm tên giấy tờ cụ thể.
    "chung-thuc-ban-sao": ["công chứng căn cước công dân", "công chứng giấy tờ",
                           "chứng thực bản sao căn cước công dân từ bản chính",
                           "photo công chứng", "sao y bản chính",
                           "công chứng sổ đỏ / bằng cấp / giấy khai sinh"],
    "chung-thuc-chu-ky": ["công chứng chữ ký", "xác nhận chữ ký", "chứng thực điểm chỉ"],
    # Chữ ký NGƯỜI DỊCH (bản dịch giấy tờ) — KHÁC chứng thực chữ ký thường của chính công dân.
    "chung-thuc-chu-ky-nguoi-dich-ctv": ["chứng thực chữ ký người dịch", "chứng thực bản dịch",
                                         "công chứng bản dịch", "dịch thuật công chứng",
                                         "chứng thực giấy tờ đã dịch", "cộng tác viên dịch thuật"],
    "chung-thuc-giao-dich-tai-san": ["chứng thực hợp đồng", "chứng thực giao dịch",
                                     "công chứng hợp đồng mua bán", "công chứng hợp đồng tặng cho",
                                     "công chứng hợp đồng thế chấp", "chứng thực hợp đồng mua bán nhà đất",
                                     "chứng thực giao dịch mua bán xe / nhà / đất"],
    # SỬA / BỔ SUNG / HỦY một hợp đồng, giao dịch ĐÃ chứng thực trước đó — KHÁC giao dịch tài sản
    # (chứng thực một hợp đồng MỚI). Cụm "chứng thực hợp đồng" trơn không thuộc thủ tục này.
    "chung-thuc-sua-doi-bo-sung-huy-bo-giao-dich": [
        "chứng thực sửa đổi hợp đồng", "chứng thực hủy bỏ hợp đồng", "hủy hợp đồng đã chứng thực",
        "bổ sung phụ lục hợp đồng đã chứng thực", "sửa đổi, bổ sung, hủy bỏ giao dịch",
        "chứng thực việc hủy giao dịch mua bán",
    ],
    # Chia DI SẢN THỪA KẾ của người đã mất — KHÁC giao dịch tài sản ngay trên (mua bán, tặng cho,
    # thế chấp giữa người còn sống). Cụm "hợp đồng"/"nhà đất" trơn không thuộc thủ tục này.
    "chung-thuc-phan-chia-di-san": ["chứng thực văn bản phân chia di sản",
                                    "chứng thực thỏa thuận phân chia di sản", "chia di sản thừa kế",
                                    "chia thừa kế nhà đất", "làm giấy chia thừa kế",
                                    "phân chia tài sản thừa kế của bố mẹ đã mất"],
    "cap-giay-phep-khai-thac-thuy-san": ["giấy phép khai thác thủy sản", "giấy phép đánh bắt cá",
                                         "cấp lại giấy phép khai thác", "giấy phép tàu cá",
                                         "giấy phép đánh bắt hải sản"],
    "cap-giay-phep-xay-dung-moi-nha-o-rieng-le": ["cấp phép xây dựng", "xin giấy phép xây dựng",
                                                  "xin phép xây nhà", "giấy phép xây nhà ở riêng lẻ",
                                                  "xin phép xây dựng công trình cấp 3 cấp 4",
                                                  "xin giấy phép xây mới"],
    "dieu-chinh-huu-tri-xa-hoi": ["trợ cấp hưu trí xã hội", "hưởng trợ cấp hưu trí",
                                  "xin trợ cấp hưu trí cho người già", "điều chỉnh trợ cấp hưu trí",
                                  "thôi hưởng trợ cấp hưu trí", "chế độ hưu trí xã hội",
                                  "trợ cấp cho người cao tuổi không có lương hưu"],
    # Nhãn dùng chung cụm "trợ cấp hưu trí xã hội" với thủ tục hưu trí → hint chỉ nhận cụm có
    # "mai táng"/"chôn cất", không bao giờ để lọt cụm trợ cấp trơn.
    "ho-tro-mai-tang-huu-tri-xa-hoi": ["hỗ trợ mai táng cho người hưởng trợ cấp hưu trí",
                                       "mai táng cho người hưởng hưu trí xã hội",
                                       "chi phí mai táng người cao tuổi hưởng trợ cấp hưu trí"],
    # Người có công (Bộ Nội vụ) chuyển chỗ ở → chuyển hồ sơ hưởng ưu đãi theo. KHÔNG nhận "chuyển hộ
    # khẩu"/"đổi nơi thường trú" trơn: đó là thủ tục cư trú của công an, không phải thủ tục này.
    "di-chuyen-ho-so-nguoi-huong-tro-cap": ["di chuyển hồ sơ người có công",
                                            "chuyển hồ sơ hưởng trợ cấp ưu đãi",
                                            "chuyển hồ sơ liệt sĩ về nơi ở mới",
                                            "người có công chuyển nơi thường trú",
                                            "di chuyển hồ sơ trợ cấp ưu đãi"],
    # CÙNG cụm "trợ cấp ưu đãi" với thủ tục di chuyển hồ sơ ngay trên, chỉ khác ở chỗ NGƯỜI CÓ
    # CÔNG ĐÃ MẤT và thân nhân đứng ra hưởng chế độ → hint chỉ nhận cụm có người có công qua
    # đời; cụm "trợ cấp ưu đãi" trơn không thuộc bên nào.
    # Giấy chứng nhận ATTP cho quán ăn / cơ sở sản xuất thực phẩm (Bộ Y tế). Người dân thường gọi
    # theo việc mở quán chứ không theo tên giấy.
    "cap-giay-chung-nhan-co-so-du-dieu-kien-an-toan-thuc-pham": [
        "giấy chứng nhận an toàn thực phẩm", "giấy chứng nhận vệ sinh an toàn thực phẩm",
        "xin giấy an toàn thực phẩm cho quán ăn", "mở nhà hàng cần giấy an toàn thực phẩm",
        "giấy phép vệ sinh thực phẩm cho bếp ăn", "cơ sở đủ điều kiện an toàn thực phẩm",
    ],
    # Người được giao THỜ CÚNG liệt sĩ (liệt sĩ không còn thân nhân hưởng trợ cấp hằng tháng).
    # Cụm "thờ cúng" là dấu hiệu riêng, không đụng thủ tục nào khác trong danh mục.
    "tro-cap-tho-cung-liet-si": ["trợ cấp thờ cúng liệt sĩ", "chế độ thờ cúng liệt sĩ",
                                 "tôi đang thờ cúng liệt sĩ muốn hưởng trợ cấp",
                                 "xin tiền thờ cúng liệt sĩ hằng năm",
                                 "người thờ cúng liệt sĩ"],
    "uu-dai-ncc-tu-tran": ["người có công từ trần", "người có công mất hưởng trợ cấp",
                           "chế độ khi người có công qua đời",
                           "trợ cấp tuất cho thân nhân người có công",
                           "trợ cấp mai táng người có công đang hưởng trợ cấp ưu đãi",
                           "bố tôi là thương binh vừa mất muốn làm chế độ"],
    # Giấy XÁC NHẬN khuyết tật — KHÁC "trợ cấp cho người khuyết tật" (tiền hàng tháng) ở trên:
    # cái này là đi giám định để được công nhận mức độ khuyết tật.
    "xac-dinh-muc-do-khuyet-tat": ["xác định mức độ khuyết tật", "xác định lại mức độ khuyết tật",
                                   "cấp giấy xác nhận khuyết tật", "làm giấy khuyết tật",
                                   "giám định mức độ khuyết tật", "xin giấy chứng nhận khuyết tật"],
    # Hai thủ tục mai táng chỉ khác NHÓM ĐỐI TƯỢNG → cụm "mai táng" trơn KHÔNG thuộc bên nào; để
    # LLM đọc cả câu rồi quyết, hoặc hỏi lại. Nhét vào một bên là bên kia không bao giờ được chọn.
    "ho-tro-mai-tang": ["hỗ trợ mai táng cho đối tượng bảo trợ xã hội",
                        "mai táng cho người hưởng trợ cấp bảo trợ xã hội",
                        "chi phí mai táng người khuyết tật",
                        "mai táng cho trẻ mồ côi đang hưởng trợ cấp"],
    # CÙNG cổng Bộ Y tế và tên gần trùng với hưu trí xã hội ở trên: chỉ nhận những cụm gắn với
    # ĐỐI TƯỢNG bảo trợ xã hội (khuyết tật, mồ côi, đơn thân, HIV) hoặc khoản chăm sóc/nuôi dưỡng.
    # Cụm "trợ cấp xã hội" trơn để LLM quyết theo cả câu, không nhét vào đây kẻo nuốt của hưu trí.
    "tro-cap-xa-hoi-hang-thang": ["trợ cấp xã hội hàng tháng", "trợ cấp bảo trợ xã hội",
                                  "hỗ trợ kinh phí chăm sóc nuôi dưỡng",
                                  "trợ cấp cho người khuyết tật", "trợ cấp cho trẻ mồ côi",
                                  "trợ cấp mẹ đơn thân nuôi con nhỏ",
                                  "trợ cấp cho người nhiễm HIV",
                                  "điều chỉnh trợ cấp xã hội hàng tháng",
                                  "thôi hưởng trợ cấp xã hội hàng tháng"],
    "cap-ban-sao-van-bang-so-goc": ["bản sao văn bằng", "bản sao chứng chỉ", "bản sao bằng tốt nghiệp",
                                    "mất bằng tốt nghiệp", "xin lại bằng cấp ba", "trích lục văn bằng"],
    "cho-thue-thue-mua-nha-o-xa-hoi": ["thuê nhà ở xã hội", "thuê mua nhà ở xã hội",
                                       "đăng ký nhà ở xã hội", "xin thuê nhà xã hội",
                                       "mua nhà ở xã hội của nhà nước"],
    "cham-dut-hoat-dong-ho-kinh-doanh": ["chấm dứt hoạt động hộ kinh doanh", "đóng hộ kinh doanh",
                                         "giải thể hộ kinh doanh", "nghỉ kinh doanh hẳn",
                                         "bỏ hộ kinh doanh", "trả giấy phép kinh doanh",
                                         "không kinh doanh nữa"],
    "dang-ky-thay-doi-noi-dung-ho-kinh-doanh": ["thay đổi nội dung đăng ký kinh doanh",
                                                "đổi ngành nghề kinh doanh", "đổi tên hộ kinh doanh",
                                                "thay đổi chủ hộ kinh doanh", "đổi địa chỉ hộ kinh doanh",
                                                "sửa thông tin hộ kinh doanh"],
    "dang-ky-bien-phap-bao-dam-bac-ninh": ["đăng ký biện pháp bảo đảm", "đăng ký thế chấp sổ đỏ",
                                           "thế chấp quyền sử dụng đất", "thế chấp đất vay ngân hàng",
                                           "đăng ký giao dịch bảo đảm đất đai",
                                           "thế chấp nhà đất ở bắc ninh"],
    "xoa-dang-ky-bien-phap-bao-dam-bac-ninh": ["xóa đăng ký biện pháp bảo đảm", "xóa thế chấp sổ đỏ",
                                               "giải chấp quyền sử dụng đất", "xóa thế chấp đất đai",
                                               "xóa đăng ký giao dịch bảo đảm",
                                               "giải chấp sổ đỏ ngân hàng"],
}

# "profile" (Lấy dữ liệu đã lưu) tạm ẨN khỏi UI + LLM (xem _doc_options_card). Để bật lại: thêm
# "profile" vào set này + mô tả tương ứng vào _DOC_METHOD_DESC.
_DOC_METHODS = {"qr", "scan"}

# Mô tả các cách cung cấp giấy tờ cho LLM. BẮT BUỘC vì tên value trần (qr/scan) khiến LLM đoán mò:
# "chụp bằng điện thoại" bị hiểu "chụp"≈"scan" → chọn nhầm scan. Thứ tự KHỚP card
# (_doc_options_card: qr, scan) nên "cách 1/2" cũng suy ra được.
_DOC_METHOD_DESC: dict[str, str] = {
    "qr": 'dùng ĐIỆN THOẠI chụp/gửi ảnh giấy tờ (quét mã QR). Câu như "chụp bằng điện thoại", '
          '"chụp ảnh", "quét mã", "dùng điện thoại", "cách 1", "cái đầu".',
    "scan": 'dùng MÁY TÍNH tại quầy: đã có sẵn ảnh/PDF/tệp trong máy hoặc scan bản cứng rồi chọn '
            'tệp. Câu như "scan tại quầy", "tải tệp lên", "chọn file trong máy", "upload", "cách 2".',
}


def _doc_method_block() -> str:
    return "\n" + "\n".join(f'    · "{k}" = {v}' for k, v in _DOC_METHOD_DESC.items())

# ── Bảng ý định NÓI/GÕ theo state — nguồn CHÂN LÝ cho value + mô tả (LLM dịch câu về value).
# LLM chỉ được trả value liệt kê ở đây; parse xong validate lại, không cho bịa lệnh.
# delete_data CỐ TÌNH vắng mặt: lệnh xóa dữ liệu chỉ đi qua chip bấm tường minh.
_STATE_INTENTS: dict[str, list[dict]] = {
    # Mỗi thủ tục khai "trường hợp giải quyết" riêng trong registry (variants.options) nên danh
    # sách này là HỢP của mọi biến thể đang dùng; flow còn validate lại theo đúng thủ tục hiện
    # tại nên value của thủ tục khác lọt vào cũng bị loại. Đường chính vẫn là bấm chip (tất định).
    "choose_variant": [
        {"kind": "action", "value": "variant_cap_moi",
         "desc": "muốn CẤP MỚI giấy phép (chưa có giấy phép, xin cấp lần đầu)"},
        {"kind": "action", "value": "variant_cap_lai",
         "desc": "muốn CẤP LẠI giấy phép (đã có nhưng bị mất, hư hỏng, hết hạn hoặc đổi thông tin)"},
        {"kind": "action", "value": "variant_nha_o_rieng_le",
         "desc": "xin phép xây NHÀ Ở RIÊNG LẺ của hộ gia đình, cá nhân"},
        {"kind": "action", "value": "variant_cong_trinh",
         "desc": "xin phép xây CÔNG TRÌNH cấp III, cấp IV (không phải nhà ở riêng lẻ)"},
    ],
    "guide_login": [
        {"kind": "event", "value": "sso_success",
         "desc": "báo đã đăng nhập xong / đã vào được trang kê khai"},
    ],
    "consent": [
        {"kind": "action", "value": "consent_decline",
         "desc": "KHÔNG đồng ý cho xử lý dữ liệu / muốn tự nhập tay"},
        {"kind": "action", "value": "consent_agree",
         "desc": "đồng ý cho Trợ lý đọc giấy tờ và tự động điền (khẳng định tường minh)"},
    ],
    "qr_waiting": [
        {"kind": "action", "value": "reshow_qr",
         "desc": "không quét được mã / muốn hiện lại mã QR"},
        {"kind": "action", "value": "docs_done",
         "desc": "không muốn quét hoặc thêm tệp nữa, muốn dùng các tệp hiện có để điền/đính kèm lại ngay"},
        {"kind": "event", "value": "docs_complete",
         "desc": "báo đã chụp/gửi đủ giấy tờ, hoặc giục xử lý/điền luôn"},
    ],
    "collecting_docs": [
        {"kind": "action", "value": "docs_done",
         "desc": "đã điều chỉnh xong, không muốn thêm tệp nữa và muốn điền/đính kèm lại ngay"},
        {"kind": "event", "value": "docs_complete",
         "desc": "báo đã chụp/gửi đủ giấy tờ, hoặc giục đọc/xử lý/điền form; KHÔNG phải yêu cầu đính kèm"},
        {"kind": "action", "value": "request_attach",
         "desc": "muốn đính kèm/chuyển sang phần đính kèm khi trang hiện tại vẫn là kê khai"},
        {"kind": "action", "value": "reshow_qr",
         "desc": "muốn chụp lại / hiện lại mã QR"},
    ],
    "owner_waiting_next": [
        {"kind": "action", "value": "retry_owner_fill",
         "desc": "yêu cầu điền lại thông tin chủ hồ sơ, ví dụ 'điền đi', 'điền lại', 'thử lại'"},
    ],
    "filling": [
        {"kind": "action", "value": "request_attach",
         "desc": "muốn đính kèm/chuyển sang đính kèm ngay khi vẫn đang ở trang kê khai"},
    ],
    "reviewing": [
        {"kind": "action", "value": "confirm_review",
         "desc": "xác nhận rõ đã rà soát và form đã đúng/chuẩn, cho đính kèm giấy tờ"},
        {"kind": "action", "value": "request_attach",
         "desc": "chỉ yêu cầu đính kèm/chuyển sang đính kèm, chưa nói đã rà soát form"},
        {"kind": "action", "value": "refill",
         "desc": "chê form điền sai, muốn điền lại"},
        {"kind": "action", "value": "add_documents",
         "desc": "muốn xem, thêm hoặc xóa giấy tờ rồi điền lại tờ khai"},
    ],
    "attaching": [
        {"kind": "action", "value": "request_attach",
         "desc": "giục đính kèm giấy tờ hoặc hỏi chuyển qua phần đính kèm"},
        {"kind": "action", "value": "refill",
         "desc": "muốn quay lại điền lại thông tin kê khai/form/tờ khai"},
        {"kind": "action", "value": "add_documents",
         "desc": "đang còn ở trang kê khai và muốn điều chỉnh giấy tờ trước khi điền lại"},
    ],
    "choosing_attach_mode": [
        {"kind": "action", "value": "attach_mode_merge",
         "desc": "muốn đưa tất cả tài liệu vào cùng một hồ sơ"},
        {"kind": "action", "value": "attach_mode_split",
         "desc": "muốn mỗi tài liệu là một hồ sơ riêng / tách thành nhiều hồ sơ"},
    ],
    "done": [
        # save_profile tạm ẨN cùng option "Lấy dữ liệu đã lưu" (nút Lưu hồ sơ đã gỡ khỏi done).
        {"kind": "event", "value": "submitted",
         "desc": "báo đã bấm nộp hồ sơ xong trên trang"},
        {"kind": "action", "value": "add_documents",
         "desc": "muốn bổ sung, thêm hoặc xóa bớt giấy tờ trước khi nộp hồ sơ"},
    ],
}

# Lệnh dùng được ở MỌI state.
_GLOBAL_INTENTS: list[dict] = [
    {"kind": "action", "value": "new_procedure",
     "desc": "muốn bỏ thủ tục đang làm, chọn thủ tục khác"},
]


def _resolve_machine(message: str) -> Intent | None:
    """Nhánh TẤT ĐỊNH: lệnh máy (chip/watcher) + số điện thoại. None nếu là câu tự do (→ LLM)."""
    text = str(message or "").strip()

    # Lệnh máy từ chip/card/watcher — bỏ qua mọi suy đoán.
    if text.startswith("__event:"):
        # __event:<name>[:<chi tiết>] — chi tiết là JSON object thì thành payload
        # (page_status, agency_selected...), còn lại (vd thông điệp lỗi) vào payload.value.
        rest = text[len("__event:"):]
        name, _, detail = rest.partition(":")
        payload: dict = {}
        if detail:
            if detail.lstrip().startswith("{"):
                try:
                    parsed = json.loads(detail)
                    payload = parsed if isinstance(parsed, dict) else {"value": detail}
                except (ValueError, TypeError):
                    payload = {"value": detail}
            else:
                payload = {"value": detail}
        return Intent("event", name, payload)
    if text.startswith("__action:"):
        rest = text[len("__action:"):]
        name, _, raw = rest.partition(":")
        payload = {}
        if raw:
            try:
                payload = json.loads(raw)
            except (ValueError, TypeError):
                payload = {"value": raw}
        return Intent("action", name, payload)

    # Số điện thoại đọc/gõ (done: đăng ký thông báo; ask_doc_method: tra profile) — regex trích,
    # không cần LLM.
    cleaned = re.sub(r"[\s.\-()]", "", text)
    m = re.search(r"(?<!\d)(?:\+84|0)\d{9,10}(?!\d)", cleaned)
    if m:
        return Intent("provide_phone", m.group(0))

    return None


def resolve_deterministic(message: str, state: str | None = None) -> Intent | None:
    """Nhánh TẤT ĐỊNH duy nhất còn lại: lệnh máy + số điện thoại (state không còn ảnh hưởng).
    Câu tự do → None (router gọi `resolve` để LLM phân loại)."""
    return _resolve_machine(message)


def resolve_logout_choice(message: str) -> str | None:
    """Khi ĐANG hỏi "đăng xuất / nộp thêm hồ sơ" (2 nút sau đánh giá): công dân NÓI/GÕ câu tương
    đương thì nhận diện tất định, trả "logout_citizen" / "continue_dossiers" / None.

    Cần vì chế độ rảnh tay gửi GIỌNG NÓI dạng text tự do — LLM hay trả unknown → trợ lý báo "chưa
    nhận rõ yêu cầu" dù công dân đã nói "đăng xuất". CHỈ gọi khi đang chờ lựa chọn nên "có" đứng một
    mình cũng hiểu là đồng ý đăng xuất; "không"/"nộp thêm" là ở lại nộp tiếp."""
    t = fold(message)
    if not t:
        return None
    # Phủ định / nộp thêm — kiểm TRƯỚC vì "không đăng xuất" cũng chứa "dang xuat".
    if any(k in t for k in (
        "nop them", "khong", "chua", "o lai", "tiep tuc", "lam tiep", "con ho so", "them ho so", "van lam",
    )):
        return "continue_dossiers"
    # Đồng ý đăng xuất / kết thúc.
    if any(k in t for k in (
        "dang xuat", "dang xuat tai khoan", "thoat", "log out", "logout", "ket thuc", "xong roi", "roi di",
        "dong y", "dung vay", "dung roi",
    )):
        return "logout_citizen"
    # "Có"/"ừ"/"vâng" đứng một mình = đồng ý (đang trả lời đúng câu hỏi đăng xuất).
    if t in ("co", "co a", "co.", "u", "um", "vang", "vang a", "ok, dang xuat", "ok"):
        return "logout_citizen"
    return None


def _procedure_catalog() -> str:
    """Danh sách thủ tục (key | nhãn | mô tả | cách gọi) đưa vào prompt LLM chọn thủ tục."""
    lines = []
    for p in public_list():
        label = p.get("label") or p.get("shortLabel") or p["key"]
        parts = [label]
        if p.get("subtitle"):
            parts.append(str(p["subtitle"]))
        hints = _PROCEDURE_HINTS.get(p["key"], [])
        if hints:
            parts.append("còn gọi: " + "; ".join(hints))
        lines.append(f'  + "{p["key"]}" = ' + " — ".join(parts))
    return "\n".join(lines)


def _state_action_block(state: str) -> str:
    entries = _GLOBAL_INTENTS + _STATE_INTENTS.get(state, [])
    if not entries:
        return ' (bước này không có state_action nào → đừng dùng kind "state_action")'
    return "\n" + "\n".join(f'  + "{e["value"]}": người dân {e["desc"]}' for e in entries)


_LLM_SYSTEM = """Bạn là bộ phân loại ý định cho trợ lý thủ tục hành chính công Việt Nam.
Người dân đang ở bước "{state}". Đọc câu của họ và trả DUY NHẤT một JSON:
{{"kind": "<pick_procedure|pick_doc_method|state_action|confirm|deny|ask_question|unknown>", "value": "<xem dưới>", "procedure": "<key, chỉ cho ask_question>"}}

- pick_procedure: người dân muốn LÀM một thủ tục → value = ĐÚNG MỘT key trong DANH SÁCH THỦ TỤC.
  PHÂN BIỆT KỸ các thủ tục gần giống nhau theo mô tả: đăng ký kết hôn (trong nước) vs kết hôn
  CÓ YẾU TỐ NƯỚC NGOÀI vs ĐĂNG KÝ LẠI kết hôn; đăng ký khai sinh (đơn lẻ) vs khai sinh LIÊN THÔNG
  (kèm thường trú + BHYT cho trẻ dưới 6 tuổi) vs ĐĂNG KÝ LẠI khai sinh vs cấp bản sao/trích lục
  khai sinh vs CẢI CHÍNH/thay đổi/bổ sung hộ tịch (sửa thông tin đã đăng ký). Câu chung chung
  "đăng ký khai sinh" không nêu liên thông/hộ khẩu/bảo hiểm → chọn bản đơn lẻ...
  BỐN thủ tục của cổng Bộ Y tế RẤT DỄ LẪN: "trợ cấp HƯU TRÍ xã hội" là chế độ cho NGƯỜI CAO TUỔI
  không có lương hưu, người hưởng CÒN SỐNG; "trợ cấp XÃ HỘI HÀNG THÁNG, hỗ trợ kinh phí chăm sóc,
  nuôi dưỡng" là chế độ bảo trợ xã hội cho người khuyết tật, trẻ mồ côi, người đơn thân nuôi con
  nhỏ, người nhiễm HIV và người nhận chăm sóc, nuôi dưỡng; và HAI thủ tục MAI TÁNG cho người
  ĐÃ MẤT (thân nhân xin tiền mai táng): một dành cho người đang hưởng TRỢ CẤP HƯU TRÍ XÃ HỘI, một
  dành cho ĐỐI TƯỢNG BẢO TRỢ XÃ HỘI (khuyết tật, mồ côi, đơn thân, HIV…). Có mai táng/chôn cất/
  giấy chứng tử/người đã mất thì chắc chắn thuộc hai thủ tục mai táng, nhưng phải xem người mất
  thuộc nhóm nào mới chọn được; câu không nêu nhóm → kind="unknown" để bot hỏi lại. Tương tự, câu
  chỉ nói "trợ cấp xã hội" mà KHÔNG nêu tuổi già/lương hưu, KHÔNG nêu nhóm bảo trợ, KHÔNG nhắc
  người mất → kind="unknown", đừng đoán. Cũng của cổng này, "XÁC ĐỊNH, XÁC ĐỊNH LẠI MỨC ĐỘ KHUYẾT
  TẬT và cấp Giấy xác nhận khuyết tật" là đi GIÁM ĐỊNH để được công nhận khuyết tật (xin giấy),
  KHÁC "trợ cấp cho người khuyết tật" là xin TIỀN hằng tháng — cứ nói giấy xác nhận/giám định/xác
  định mức độ thì chọn thủ tục khuyết tật này.
  Người dân hay nói "CÔNG CHỨNG" thay cho "chứng thực": "công chứng <tên giấy tờ>" (căn cước,
  sổ đỏ, bằng cấp...) = chứng thực BẢN SAO; "công chứng chữ ký/điểm chỉ" = chứng thực CHỮ KÝ;
  "công chứng/chứng thực HỢP ĐỒNG, GIAO DỊCH" (mua bán, tặng cho, thế chấp nhà/đất/xe) =
  chứng thực GIAO DỊCH TÀI SẢN (KHÁC hẳn chứng thực bản sao một tờ giấy); "công chứng BẢN DỊCH",
  "chứng thực chữ ký NGƯỜI DỊCH", "dịch thuật công chứng" = chứng thực chữ ký NGƯỜI DỊCH
  (KHÁC chứng thực chữ ký thường — cái đó là chữ ký của chính người yêu cầu).
  Chỉ chọn khi câu thể hiện MUỐN LÀM thủ tục. Không chắc thuộc key nào → kind="unknown".
- pick_doc_method: khi người dân CHỌN hoặc ĐỔI cách cung cấp giấy tờ — kể cả đang ở bước chụp/quét QR
  mà muốn ĐỔI sang cách kia (vd đang QR nói "scan đi", đang scan nói "chụp bằng điện thoại") →
  value là MỘT trong:{doc_methods}
  CHÚ Ý QUAN TRỌNG: "chụp"/"chụp ảnh"/"chụp bằng điện thoại"/"dùng điện thoại" LUÔN là "qr"
  (KHÔNG phải "scan" — dù chữ "chụp" nghĩa gần "quét"). "scan"/"tải tệp"/"chọn file" mới là "scan".
- state_action: hành động của bước hiện tại → value là MỘT trong:{state_actions}
  Tại bước collecting_docs/filling/reviewing/attaching: câu chỉ nói "đính kèm đi", "chuyển qua
  đính kèm" mà CHƯA xác nhận đã rà soát form → request_attach; KHÔNG coi là docs_complete.
  Chỉ dùng confirm_review khi người dân nói rõ form đã đúng/đã rà soát xong/chuẩn rồi.
- confirm / deny: đồng ý / từ chối câu bot vừa hỏi → value = "".
- ask_question: hỏi thông tin (lệ phí, thời gian, giấy tờ cần...) → value = câu hỏi rút gọn;
  nếu hỏi về một thủ tục cụ thể thì thêm "procedure" = key của thủ tục đó.
- unknown: không xếp được → value = "".

DANH SÁCH THỦ TỤC (dùng cho pick_procedure và trường procedure):
{procedures}

LƯU Ý: câu có "chưa"/"không"/"chưa được" là PHỦ ĐỊNH — KHÔNG coi là hành động đã-xong
(vd "chưa đăng nhập được" KHÔNG phải sso_success). Chỉ trả JSON, không giải thích.

Câu của người dân CÓ THỂ là TIẾNG MÔNG (Hmong, chữ RPA — vd "kuv xav cuv npe yug me nyuam" =
tôi muốn đăng ký khai sinh; "thaij duab xov tooj" = chụp bằng điện thoại → "qr"; "pom zoo"/"yog" =
đồng ý; "tsis yog"/"tsis pom zoo" = từ chối). Hiểu nghĩa rồi phân loại y như câu tiếng Việt."""


async def resolve(message: str, state: str) -> Intent:
    # (1) Lệnh máy + số điện thoại: tất định tuyệt đối, không đụng LLM.
    machine = _resolve_machine(message)
    if machine is not None:
        return machine

    text = str(message or "").strip()
    if not text:
        return Intent("unknown")

    proc_keys = {p["key"] for p in public_list()}
    # (2) Mọi câu tự do → LLM phân loại (1 lượt). Lỗi/không chắc → unknown (flow hiện lại card).
    try:
        raw = await llm_chat(
            [
                {"role": "system", "content": _LLM_SYSTEM.format(
                    state=state, state_actions=_state_action_block(state),
                    doc_methods=_doc_method_block(), procedures=_procedure_catalog())},
                {"role": "user", "content": text[:500]},
            ],
            temperature=0.0,
            max_tokens=120,
        )
        m = re.search(r"\{[\s\S]*\}", raw or "")
        data = json.loads(m.group(0)) if m else {}
        kind = str(data.get("kind", "unknown"))
        value = str(data.get("value", ""))

        if kind == "pick_procedure":
            # Key phải có thật — LLM không được bịa; không hợp lệ → unknown → card.
            return Intent("pick_procedure", value) if value in proc_keys else Intent("unknown")
        if kind == "pick_doc_method":
            return Intent("pick_doc_method", value) if value in _DOC_METHODS else Intent("unknown")
        if kind == "state_action":
            # Chỉ chấp nhận value có trong bảng của state — không cho bịa lệnh.
            entry = next((e for e in _GLOBAL_INTENTS + _STATE_INTENTS.get(state, [])
                          if e["value"] == value), None)
            return Intent(entry["kind"], entry["value"]) if entry else Intent("unknown")
        if kind == "confirm":
            return Intent("confirm")
        if kind == "deny":
            return Intent("deny")
        if kind == "ask_question":
            proc = str(data.get("procedure", ""))
            payload = {"procedure_key": proc} if proc in proc_keys else {}
            return Intent("ask_question", value or text, payload)
    except Exception as e:  # noqa: BLE001 — LLM là best-effort, flow phải sống tiếp
        logger.warning("[intents] LLM phân loại lỗi: %s", e)

    return Intent("unknown")
