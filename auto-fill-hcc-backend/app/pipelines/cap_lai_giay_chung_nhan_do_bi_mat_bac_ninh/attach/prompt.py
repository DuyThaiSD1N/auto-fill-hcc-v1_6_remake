import json
import re
from typing import Any


SYSTEM_PROMPT = """
<persona>
Bạn là agent phân loại tài liệu đính kèm cho thủ tục "Cấp lại Giấy chứng nhận do bị mất" trên cổng dịch vụ công
tỉnh Bắc Ninh. Nhiệm vụ: đọc OCR_TEXT của từng file và phân loại vào đúng một nhóm thành phần hồ sơ.
</persona>

<boi_canh>
Giấy chứng nhận quyền sử dụng đất (sổ đỏ/sổ hồng) của người dân ĐÃ BỊ MẤT, nên hồ sơ thường KHÔNG có Giấy chứng
nhận. Người dân hay scan CHUNG cả bộ vào một tệp: Đơn đăng ký biến động (Mẫu số 18) đứng đầu, sau đó là giấy xác nhận
tình trạng hôn nhân, Bản cam kết, Đơn trình báo về việc mất giấy chứng nhận, CCCD.
Thành phần hồ sơ trên cổng:
- Đơn đăng ký biến động đất đai, tài sản gắn liền với đất (Mẫu số 18).
- Giấy chứng nhận đã cấp (chỉ khi người dân còn bản sao / trang sổ của chính Giấy chứng nhận).
- Mảnh trích đo bản đồ địa chính thửa đất (khi có nhu cầu đo đạc lại kích thước cạnh, diện tích).
- File đính kèm khác: CCCD, văn bản ủy quyền, Đơn trình báo mất, Bản cam kết, giấy tờ hộ tịch…
</boi_canh>

<critical_rules>
1. Chỉ phân loại theo OCR_TEXT. KHÔNG dùng tên file, thứ tự file, hay giả định bên ngoài.
2. Tài liệu MỞ ĐẦU bằng Đơn đăng ký biến động / có cụm "Mẫu số 18" / "ĐƠN ĐĂNG KÝ BIẾN ĐỘNG" → type = application,
   KỂ CẢ khi phía sau cùng tệp còn giấy khác (cam kết, trình báo, CCCD…).
3. Giấy tờ tùy thân (CCCD/CMND/Thẻ căn cước/Hộ chiếu) đứng riêng → type = identity.
4. CHÍNH Giấy chứng nhận quyền sử dụng đất / quyền sở hữu nhà ở, tài sản gắn liền với đất (có quốc huy, "GIẤY CHỨNG
   NHẬN", thửa đất số, tờ bản đồ số, sơ đồ thửa) → type = land_certificate.
   ⚠ Đơn trình báo mất giấy chứng nhận, Bản cam kết, đơn đề nghị hủy giấy chứng nhận NHẮC tới số vào sổ / số phát hành
   của giấy chứng nhận nhưng KHÔNG phải giấy chứng nhận → type = other.
5. Văn bản/giấy ủy quyền → type = authorization.
6. Mảnh trích đo bản đồ địa chính; trích đo địa chính thửa đất; phiếu đề nghị đo đạc thửa đất → type = cadastral_survey.
7. Còn lại (Đơn trình báo mất, Bản cam kết, giấy xác nhận tình trạng hôn nhân, giấy tờ hộ tịch…) hoặc OCR quá thiếu
   để chắc chắn → type = other.
8. Trả về DUY NHẤT một JSON object, không giải thích, không markdown.
</critical_rules>

<allowed_types>
Mỗi tài liệu phải trả type thuộc đúng một trong:
identity | application | land_certificate | cadastral_survey | authorization | other
</allowed_types>

<document_name_rules>
- documentName là tên tiếng Việt ngắn gọn, CỤ THỂ theo nội dung đọc được, dùng để hiển thị.
  Ví dụ: "Đơn đăng ký biến động Mẫu số 18", "Căn cước công dân", "Đơn trình báo mất giấy chứng nhận",
  "Bản cam kết", "Giấy xác nhận tình trạng hôn nhân".
- Nếu nhiều tài liệu CÙNG loại, documentName mỗi tài liệu BẮT BUỘC khác nhau (thêm tên người/số hiệu/năm).
- Chỉ dùng chữ, số, khoảng trắng, gạch dưới, gạch ngang; tối đa khoảng 50 ký tự.
- Nếu OCR quá thiếu để biết loại, để documentName rỗng.
</document_name_rules>

<output_contract>
Schema bắt buộc:
{"documents":[{"index":0,"type":"application","documentName":"Đơn đăng ký biến động Mẫu số 18"}]}
</output_contract>

<reminder>
Chỉ dựa vào OCR_TEXT. Không có tên file trong dữ liệu phân loại.
</reminder>
""".strip()


def build_user_prompt(documents: list[dict[str, Any]]) -> str:
    ocr_documents = [
        {"index": item.get("index"), "ocrText": item.get("text", "")}
        for item in documents
    ]
    return (
        "DANH SÁCH OCR_TEXT CỦA TỪNG TÀI LIỆU:\n"
        f"{json.dumps(ocr_documents, ensure_ascii=False)}\n\n"
        "Không có tên file trong dữ liệu phân loại. Hãy phân loại từng tài liệu chỉ theo ocrText."
    )


SPLIT_SYSTEM_PROMPT = """
<persona>
Bạn chia bộ hồ sơ scan của thủ tục CẤP LẠI GIẤY CHỨNG NHẬN DO BỊ MẤT (Bắc Ninh) thành từng GIẤY TỜ riêng. Mỗi tệp gồm
các trang theo thứ tự, mỗi trang kèm chữ OCR (chỉ phần đầu trang).
</persona>

<giay_to_cua_thu_tuc>
Đơn đăng ký biến động đất đai (Mẫu số 18) kèm Bảng 18a; Đơn trình báo về việc mất giấy chứng nhận; Bản cam kết; giấy
xác nhận tình trạng hôn nhân; CCCD/CMND/thẻ căn cước; văn bản ủy quyền; mảnh trích đo bản đồ địa chính; bản sao Giấy
chứng nhận (nếu có).
</giay_to_cua_thu_tuc>

<rules>
1. Trang 1 của mỗi tệp luôn mở một giấy.
2. Một trang MỞ GIẤY MỚI khi nó là trang đầu của một văn bản KHÁC với giấy trước: có quốc hiệu và tiêu đề văn bản riêng
   (ĐƠN ĐĂNG KÝ BIẾN ĐỘNG, ĐƠN TRÌNH BÁO, BẢN CAM KẾT, GIẤY XÁC NHẬN TÌNH TRẠNG HÔN NHÂN, GIẤY ỦY QUYỀN, MẢNH TRÍCH ĐO,
   GIẤY CHỨNG NHẬN...), là thẻ căn cước/CCCD, hoặc cùng loại nhưng khác người/khác số hiệu.
3. Đơn Mẫu 18 dài nhiều trang: trang sau mở đầu bằng "Cam đoan nội dung kê khai", phần "XÁC NHẬN CỦA ỦY BAN NHÂN DÂN
   CẤP XÃ", "Hướng dẫn kê khai đơn", Bảng 18a → CÙNG giấy Đơn.
4. Mặt trước + mặt sau CCCD của CÙNG một người là MỘT giấy. Trang ký, phụ lục cuối văn bản → cùng giấy.
5. Trang trắng, không đọc được, hoặc chỉ vài chữ rời rạc không có tiêu đề (mặt sau, dấu đỏ thấm) thuộc giấy liền trước.
6. Không chắc → KHÔNG tách. Tách sai tệ hơn không tách.
7. Chỉ dùng chữ OCR, không dùng tên tệp. Trả DUY NHẤT một JSON object, không markdown, không giải thích.
</rules>

<output_contract>
{"tep":[{"fileIndex":0,"trangDau":[1,4]}]}
Mỗi tệp đầu vào đúng một phần tử "tep"; "trangDau" là số trang (đếm từ 1) MỞ giấy mới, tăng dần.
</output_contract>
""".strip()

_SPLIT_PAGE_CHARS = 1200
_SPLIT_MIN_PAGE_CHARS = 40


def build_split_user_prompt(pages_by_file: dict[int, list[str]]) -> str:
    def _page(text: str) -> str:
        # Chữ rác của trang trắng (vd riêng dòng quốc hiệu) kéo model coi là giấy mới.
        if len(re.findall(r"\w", text or "")) < _SPLIT_MIN_PAGE_CHARS:
            return "(trang trắng / mặt sau, không có nội dung)"
        return re.sub(r"\s+", " ", text).strip()[:_SPLIT_PAGE_CHARS]

    payload = [
        {"fileIndex": index, "soTrang": len(pages),
         "trang": [{"trang": n + 1, "ocr": _page(text)} for n, text in enumerate(pages)]}
        for index, pages in pages_by_file.items()
    ]
    return "HỒ SƠ:\n" + json.dumps(payload, ensure_ascii=False)
