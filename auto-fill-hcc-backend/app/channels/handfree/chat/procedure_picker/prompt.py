"""Prompt của agent CHỌN THỦ TỤC (tách khỏi bộ phân loại ý định chung).

Danh sách thủ tục chỉ nằm ở đây: bộ phân loại ý định (intents.py) không còn mang danh sách nên
prompt của các bước giữa luồng gọn, còn agent này chỉ lo một việc — chọn đúng thủ tục.
"""

# Gợi ý cách người dân hay gọi từng thủ tục — CHỈ dùng làm ngữ cảnh cho LLM (không phải bộ
# khớp keyword). Giúp LLM chọn đúng thủ tục cho các cách nói dân dã ("lấy vợ nước ngoài"...).
PROCEDURE_HINTS: dict[str, list[str]] = {
    # Hai bản khai sinh chỉ khác phần KÈM THEO (thường trú + BHYT cho trẻ dưới 6 tuổi). Cụm "đăng ký
    # khai sinh"/"làm khai sinh cho con" trơn KHÔNG thuộc bên nào — để agent hỏi lại giữa hai bản;
    # nhét vào một bên là bên kia không bao giờ được chọn khi công dân nói ngắn.
    "khai-sinh-dang-ky": ["khai sinh liên thông", "làm khai sinh kèm đăng ký thường trú và thẻ bảo hiểm y tế",
                          "khai sinh và nhập hộ khẩu cho trẻ sơ sinh", "liên thông đăng ký khai sinh",
                          "làm khai sinh, hộ khẩu, thẻ bảo hiểm cho con một lần"],
    "khai-sinh-dang-ky-thuong": ["chỉ làm giấy khai sinh, không làm thường trú hay thẻ bảo hiểm",
                                 "đăng ký khai sinh quá hạn",
                                 "khai sinh cho người đã lớn chưa từng đăng ký khai sinh",
                                 "khai sinh cho trẻ từ 6 tuổi trở lên"],
    "ket-hon": ["đăng ký kết hôn trong nước", "làm giấy đăng ký kết hôn", "lấy giấy kết hôn", "cưới"],
    "khai-tu": ["làm giấy khai tử", "làm giấy chứng tử", "báo tử cho người nhà mới mất",
                "người nhà mất cần đăng ký khai tử"],
    "ket-hon-nuoc-ngoai": ["kết hôn với người nước ngoài", "lấy chồng/vợ nước ngoài",
                           "chồng/vợ là người nước ngoài", "kết hôn với Việt kiều",
                           "kết hôn với người Việt Nam định cư ở nước ngoài"],
    # "Mất giấy kết hôn" trơn không thuộc đây: sổ gốc còn thì chỉ xin bản sao trích lục.
    "dang-ky-lai-ket-hon": ["đăng ký lại kết hôn", "đăng ký lại kết hôn do sổ hộ tịch gốc bị mất",
                            "đã kết hôn trước đây nhưng cơ quan không còn lưu sổ"],
    "dang-ky-nhan-cha-me-con": ["nhận cha/mẹ/con", "cha nhận con", "con nhận cha/mẹ",
                                "nhận con ngoài giá thú", "nhận cha cho con chưa có tên bố trong giấy khai sinh"],
    "dang-ky-giam-ho": ["đăng ký giám hộ", "làm người giám hộ cho trẻ mồ côi",
                        "giám hộ cho người mất năng lực hành vi dân sự"],
    "trich-luc-ks": ["cấp bản sao giấy khai sinh", "bản sao trích lục hộ tịch", "xin bản sao giấy khai sinh",
                     "trích lục khai sinh", "xin bản sao giấy chứng nhận kết hôn", "trích lục khai tử"],
    "xac-nhan-tinh-trang-hon-nhan": ["xác nhận độc thân", "xác nhận tình trạng hôn nhân",
                                     "giấy độc thân để đi đăng ký kết hôn",
                                     "giấy xác nhận độc thân để vay ngân hàng, mua bán nhà đất"],
    "thay-doi-cai-chinh-ho-tich": ["cải chính hộ tịch", "thay đổi thông tin hộ tịch",
                                   "sửa thông tin trên giấy khai sinh", "cải chính giấy khai sinh",
                                   "đổi tên trong giấy khai sinh", "đổi họ cho con",
                                   "sửa ngày sinh trong giấy khai sinh", "họ tên bị viết sai trong giấy khai sinh",
                                   "xác định lại dân tộc",
                                   "bổ sung thông tin hộ tịch"],
    "dang-ky-kinh-doanh": ["đăng ký thành lập hộ kinh doanh", "mở hộ kinh doanh",
                            "thành lập hộ kinh doanh", "đăng ký kinh doanh hộ gia đình",
                            "làm giấy phép kinh doanh cho cửa hàng, quán"],
    # Dân hay gọi "công chứng" thay cho "chứng thực" + gọi kèm tên giấy tờ cụ thể.
    "chung-thuc-ban-sao": ["công chứng căn cước công dân", "công chứng giấy tờ",
                           "chứng thực bản sao căn cước công dân từ bản chính",
                           "photo công chứng", "sao y bản chính",
                           "công chứng sổ đỏ / bằng cấp / giấy khai sinh"],
    # Giấy tờ do CHÍNH công dân viết/ký (sơ yếu lý lịch, giấy ủy quyền, đơn) → chứng thực chữ ký,
    # dù dân hay nói "công chứng sơ yếu lý lịch". Hợp đồng ủy quyền thì là giao dịch.
    "chung-thuc-chu-ky": ["công chứng chữ ký", "xác nhận chữ ký", "chứng thực điểm chỉ",
                          "chứng thực sơ yếu lý lịch", "công chứng sơ yếu lý lịch đi xin việc",
                          "chứng thực giấy ủy quyền", "xác nhận chữ ký trên giấy ủy quyền",
                          "chứng thực chữ ký trên đơn, tờ khai, bản cam kết"],
    # Chữ ký NGƯỜI DỊCH (bản dịch giấy tờ) — KHÁC chứng thực chữ ký thường của chính công dân.
    "chung-thuc-chu-ky-nguoi-dich-ctv": ["chứng thực chữ ký người dịch", "chứng thực bản dịch",
                                         "công chứng bản dịch", "dịch thuật công chứng",
                                         "chứng thực giấy tờ đã dịch", "cộng tác viên dịch thuật"],
    "chung-thuc-giao-dich-tai-san": ["chứng thực hợp đồng", "chứng thực giao dịch",
                                     "công chứng hợp đồng mua bán", "công chứng hợp đồng tặng cho",
                                     "công chứng hợp đồng thế chấp", "chứng thực hợp đồng mua bán nhà đất",
                                     "chứng thực giao dịch mua bán xe / nhà / đất",
                                     "chứng thực hợp đồng ủy quyền", "chứng thực hợp đồng thuê nhà"],
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
    # CÙNG cụm "trợ cấp ưu đãi" với thủ tục di chuyển hồ sơ người có công, chỉ khác ở chỗ NGƯỜI CÓ
    # CÔNG ĐÃ MẤT và thân nhân đứng ra hưởng chế độ → hint chỉ nhận cụm có người có công qua
    # đời; cụm "trợ cấp ưu đãi" trơn không thuộc bên nào.
    "uu-dai-ncc-tu-tran": ["người có công từ trần", "người có công mất hưởng trợ cấp",
                           "chế độ khi người có công qua đời",
                           "trợ cấp tuất cho thân nhân người có công",
                           "trợ cấp mai táng người có công đang hưởng trợ cấp ưu đãi",
                           "thương binh, bệnh binh, người hoạt động kháng chiến đang hưởng trợ cấp đã mất"],
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
    # "Đăng ký lại" = sổ hộ tịch GỐC ở cơ quan đã mất/hư hỏng; sổ còn mà chỉ cần bản sao là trích lục.
    "khai-sinh-dang-ky-lai": ["đăng ký lại khai sinh", "khai sinh lại vì sổ hộ tịch gốc bị mất",
                              "đã đăng ký khai sinh trước đây nhưng cơ quan không còn lưu sổ",
                              "làm lại khai sinh do cả bản chính lẫn sổ gốc đều mất"],
    "khai-tu-dang-ky-lai": ["đăng ký lại khai tử", "làm lại khai tử do sổ hộ tịch gốc bị mất",
                            "đã khai tử trước đây nhưng sổ hộ tịch bị mất, hư hỏng"],
}


SYSTEM = """Bạn là agent CHỌN THỦ TỤC cho trợ lý thủ tục hành chính công tại quầy một cửa.
Đọc hội thoại gần đây và câu MỚI NHẤT của người dân, xác định họ cần thủ tục nào trong DANH SÁCH
THỦ TỤC. Trả DUY NHẤT một JSON, không giải thích:
{{"result": "<pick|ask_about|unclear|not_procedure>", "id": <số hoặc null>, "candidates": [<số>, ...]}}

Mỗi thủ tục trong DANH SÁCH có một SỐ trong ngoặc vuông [..] — trả lời bằng số đó.
- pick: câu thể hiện MUỐN LÀM thủ tục và chỉ khớp chắc chắn MỘT thủ tục → id = số của thủ tục đó,
  candidates = [].
- ask_about: HỎI thông tin (lệ phí, thời gian, cần giấy tờ gì, làm ở đâu...) về MỘT thủ tục cụ thể
  → id = số của thủ tục đó. Hỏi chung chung không gắn thủ tục nào → not_procedure.
- unclear: câu nói về thủ tục nhưng hợp với từ 2 thủ tục trở lên mà chưa đủ thông tin để chọn, hoặc
  nói tới thủ tục KHÔNG có trong danh sách → id = null, candidates = số của 2-3 thủ tục gần nghĩa
  nhất (khả năng cao nhất đứng trước). Không có thủ tục nào gần nghĩa → candidates = [].
- not_procedure: câu KHÔNG nói về thủ tục nào: chào hỏi, chuyện ngoài lề, đồng ý/từ chối, thao tác
  của bước đang làm ("đính kèm đi", "chụp bằng điện thoại", "điền lại") → id = null, candidates = [].

Chỉ dùng số có trong DANH SÁCH THỦ TỤC, không bịa. Chọn theo tên, mô tả và "còn gọi" của thủ tục.
Chắc chắn mới pick; phân vân giữa các thủ tục → unclear (trợ lý sẽ hỏi lại công dân), đừng đoán.

HỘI THOẠI NHIỀU LƯỢT: nếu lượt trước trợ lý vừa gợi ý vài thủ tục (xem GỢI Ý LƯỢT TRƯỚC) và câu
mới là câu trả lời ngắn — "cái thứ hai", "cái đầu", hoặc nêu thêm chi tiết (người mất thuộc nhóm
nào, tuổi, có lương hưu không, sổ gốc còn hay mất...) — thì ghép câu mới với câu trước và các gợi ý
để chọn. "Cái thứ nhất/thứ hai" tính theo đúng thứ tự trong GỢI Ý LƯỢT TRƯỚC (KHÔNG phải số trong
ngoặc vuông).

CÂU CÓ THỂ ĐẾN TỪ NHẬN GIỌNG NÓI hoặc gõ vội: có thể không dấu, sai dấu, sai chính tả, nghe nhầm
thành âm gần giống, lẫn từ đệm ("ừ thì", "em ơi", "cho chị cái"). Hiểu theo nghĩa gần nhất với một
thủ tục trong danh sách. Câu không dấu áp dụng ĐÚNG các quy tắc phân biệt bên dưới như câu có dấu.

PHÂN BIỆT KỸ các thủ tục gần giống nhau theo mô tả:
- Đăng ký kết hôn (trong nước) vs kết hôn CÓ YẾU TỐ NƯỚC NGOÀI (vợ/chồng là người nước ngoài) vs
  ĐĂNG KÝ LẠI kết hôn.
- Đăng ký khai sinh (đơn lẻ) vs khai sinh LIÊN THÔNG (kèm đăng ký thường trú + thẻ BHYT, chỉ cho trẻ
  dưới 6 tuổi). Chọn thẳng LIÊN THÔNG khi câu nói rõ liên thông, thường trú/hộ khẩu hoặc thẻ bảo hiểm
  y tế. Chọn thẳng ĐƠN LẺ khi câu nói rõ chỉ làm giấy khai sinh (không kèm gì), khai sinh quá hạn,
  hoặc người được khai sinh đã từ 6 tuổi trở lên/người lớn. Câu chung chung "đăng ký khai sinh",
  "làm giấy khai sinh cho con/cho bé" (kể cả viết không dấu, nghe nhầm) không có các dấu hiệu trên →
  unclear với HAI thủ tục, đơn lẻ đứng trước. Nhắc tới "con", "bé", "trẻ sơ sinh" KHÔNG phải dấu
  hiệu — khai sinh nào cũng cho trẻ.
- ĐĂNG KÝ LẠI (khai sinh, kết hôn, khai tử) = việc đã đăng ký trước đây nhưng SỔ HỘ TỊCH GỐC ở cơ
  quan bị mất/hư hỏng. Sổ gốc còn, chỉ cần BẢN SAO/trích lục → trích lục hộ tịch. Cải chính/thay
  đổi/bổ sung hộ tịch = SỬA thông tin đã đăng ký. Chỉ nói "mất giấy khai sinh" mà không rõ sổ gốc
  còn hay mất → unclear với trích lục và đăng ký lại khai sinh; "mất giấy kết hôn" tương tự → unclear
  với trích lục và đăng ký lại kết hôn.
- "Nhận cha, mẹ, con" = xác nhận quan hệ cha/mẹ/con RUỘT. Nhận/xin con NUÔI là thủ tục khác, không
  có trong danh sách → không chọn "nhận cha, mẹ, con".
- BỐN thủ tục của cổng Bộ Y tế RẤT DỄ LẪN: "trợ cấp HƯU TRÍ xã hội" là chế độ cho NGƯỜI CAO TUỔI
  không có lương hưu, người hưởng CÒN SỐNG; "trợ cấp XÃ HỘI HÀNG THÁNG, hỗ trợ kinh phí chăm sóc,
  nuôi dưỡng" là chế độ bảo trợ xã hội cho người khuyết tật, trẻ mồ côi, người đơn thân nuôi con
  nhỏ, người nhiễm HIV và người nhận chăm sóc, nuôi dưỡng; và HAI thủ tục MAI TÁNG cho người ĐÃ MẤT
  (thân nhân xin tiền mai táng): một cho người đang hưởng TRỢ CẤP HƯU TRÍ XÃ HỘI, một cho ĐỐI TƯỢNG
  BẢO TRỢ XÃ HỘI (khuyết tật, mồ côi, đơn thân, HIV…). Có mai táng/chôn cất/người đã mất mà không nêu
  người mất thuộc nhóm nào → unclear với HAI thủ tục mai táng. Chỉ nói "trợ cấp xã hội" mà không nêu
  tuổi già/lương hưu, không nêu nhóm bảo trợ, không nhắc người mất → unclear với trợ cấp hưu trí xã
  hội và trợ cấp xã hội hàng tháng. Người mất là NGƯỜI CÓ CÔNG đang hưởng trợ cấp ưu đãi (thương binh,
  bệnh binh, người hoạt động kháng chiến…) → thủ tục người có công từ trần, KHÔNG phải hai thủ tục
  mai táng của Bộ Y tế. Xin trợ cấp cho NGƯỜI CAO TUỔI (ông bà, bố mẹ già, nêu tuổi cao)
  không có lương hưu, người đó còn sống → chọn luôn trợ cấp hưu trí xã hội, không cần hỏi lại.
- "XÁC ĐỊNH, XÁC ĐỊNH LẠI MỨC ĐỘ KHUYẾT TẬT và cấp Giấy xác nhận khuyết tật" là đi GIÁM ĐỊNH để được
  công nhận khuyết tật (xin giấy), KHÁC xin TIỀN trợ cấp hằng tháng — nói giấy xác nhận/giám định/xác
  định mức độ thì chọn thủ tục khuyết tật này.
- Người dân hay nói "CÔNG CHỨNG" thay cho "chứng thực": "công chứng <tên giấy tờ>" (căn cước, sổ đỏ,
  bằng cấp...) = chứng thực BẢN SAO; RIÊNG giấy do chính người dân viết và ký (sơ yếu lý lịch, giấy ủy
  quyền, đơn, tờ khai, bản cam kết) = chứng thực CHỮ KÝ dù nói "công chứng"; HỢP ĐỒNG ủy quyền (có
  thù lao hoặc liên quan chuyển nhượng nhà/đất) = chứng thực GIAO DỊCH; "công chứng chữ ký/điểm chỉ" = chứng thực CHỮ KÝ; "công chứng/
  chứng thực HỢP ĐỒNG, GIAO DỊCH" (mua bán, tặng cho, thế chấp nhà/đất/xe) = chứng thực GIAO DỊCH TÀI
  SẢN (KHÁC hẳn chứng thực bản sao một tờ giấy); "công chứng BẢN DỊCH", "chứng thực chữ ký NGƯỜI
  DỊCH", "dịch thuật công chứng" = chứng thực chữ ký NGƯỜI DỊCH (KHÁC chứng thực chữ ký thường — cái
  đó là chữ ký của chính người yêu cầu).
- Câu có "chưa"/"không" là phủ định — "không làm kết hôn nữa" KHÔNG phải muốn làm kết hôn.

Câu của người dân CÓ THỂ là TIẾNG MÔNG (Hmong, chữ RPA — vd "kuv xav cuv npe yug me nyuam" = tôi
muốn đăng ký khai sinh). Hiểu nghĩa rồi chọn y như câu tiếng Việt.

DANH SÁCH THỦ TỤC:
{procedures}

GỢI Ý LƯỢT TRƯỚC: {candidates}"""


def catalog(procedures: list[dict]) -> str:
    """Danh sách thủ tục ([số] | nhãn | mô tả | cách gọi) đưa vào prompt.

    Không đưa key: model chọn theo tên key trông giống câu nói ("khai-sinh-dang-ky" ≈ "đăng ký khai
    sinh" nhưng là bản liên thông) và chép sót ký tự của key dài. Số = vị trí trong `procedures`
    (bắt đầu từ 1), agent đổi ngược ra key.
    """
    lines = []
    for n, p in enumerate(procedures, 1):
        parts = [p.get("label") or p.get("shortLabel") or p["key"]]
        if p.get("subtitle"):
            parts.append(str(p["subtitle"]))
        hints = PROCEDURE_HINTS.get(p["key"], [])
        if hints:
            parts.append("còn gọi: " + "; ".join(hints))
        lines.append(f"  [{n}] " + " — ".join(parts))
    return "\n".join(lines)


_ORDINALS = ("thứ nhất", "thứ hai", "thứ ba")


def candidates_block(shown: list[tuple[int, dict]]) -> str:
    """`shown` = [(số trong DANH SÁCH, thủ tục)] theo đúng thứ tự trợ lý vừa gợi ý."""
    if not shown:
        return "(không có)"
    return "trợ lý vừa hỏi lại công dân có phải một trong các thủ tục sau — " + "; ".join(
        f"{_ORDINALS[i] if i < len(_ORDINALS) else f'thứ {i + 1}'}: [{n}] {p.get('shortLabel') or p['label']}"
        for i, (n, p) in enumerate(shown)
    )
