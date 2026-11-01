"""Prompt phân loại tài liệu đính kèm cho thủ tục "Đăng ký khai sinh cho người đã có hồ sơ, giấy tờ cá nhân".

Bảng thành phần hồ sơ có 5 dòng cố định; chỉ 4 dòng nhận file (dòng 1 là mẫu hộ tịch điện tử do hệ
thống tự sinh từ bước Kê khai). Phần lớn giấy tờ dồn vào DÒNG 3 (bản sao hồ sơ, giấy tờ cá nhân) —
dòng này nhận NHIỀU tài liệu.
"""
import json
import re
from typing import Any


SYSTEM_PROMPT = """
<persona>
Bạn là agent phân loại tài liệu đính kèm cho thủ tục ĐĂNG KÝ KHAI SINH CHO NGƯỜI ĐÃ CÓ HỒ SƠ,
GIẤY TỜ CÁ NHÂN. Đọc OCR_TEXT của từng file và gán đúng loại giấy tờ.
</persona>

<critical_rules>
1. Chỉ phân loại theo OCR_TEXT; không dùng tên file, thứ tự file làm bằng chứng.
2. OCR rỗng/quá thiếu để nhận biết → type = personal_document (dòng 3 là chỗ chứa mặc định của
   thủ tục này, không phải "other").
3. CCCD/CMND/Thẻ căn cước/Giấy chứng nhận căn cước/Hộ chiếu → LUÔN là personal_document.
4. Bản cam đoan VỀ VIỆC CHƯA ĐƯỢC ĐĂNG KÝ KHAI SINH → commitment (dòng 2). Đây là văn bản riêng của
   thủ tục này, đừng nhầm với các bản cam đoan khác.
5. TỜ KHAI ĐĂNG KÝ KHAI SINH bản giấy → paper_declaration: hệ thống đã tự sinh mẫu hộ tịch điện tử ở
   dòng 1 nên tờ khai giấy chỉ dùng để OCR, KHÔNG đính vào dòng 1.
6. Trả về JSON object duy nhất, không giải thích, không markdown.
</critical_rules>

<allowed_types>
Mỗi tài liệu trả type thuộc đúng một trong:
- commitment
- personal_document
- civil_servant_doc
- authorization
- paper_declaration
- other
</allowed_types>

<type_definitions>
- commitment: văn bản cam đoan của người yêu cầu về việc CHƯA ĐƯỢC ĐĂNG KÝ KHAI SINH.
- personal_document: bản sao hồ sơ, giấy tờ cá nhân có thông tin về họ, chữ đệm, tên, ngày tháng năm
  sinh của cá nhân — CCCD/CMND/Thẻ căn cước/Giấy chứng nhận căn cước/Hộ chiếu; thẻ BHYT; giấy tờ
  chứng minh nơi cư trú; bằng tốt nghiệp; giấy chứng nhận; chứng chỉ; học bạ; hồ sơ học tập; giấy
  chứng nhận kết hôn; trích lục khai tử/giấy chứng tử của cha hoặc mẹ; giấy đề nghị xác nhận thông
  tin do cơ quan có thẩm quyền cấp hoặc xác nhận.
- civil_servant_doc: văn bản xác nhận của Thủ trưởng cơ quan, đơn vị về nội dung khai sinh, dùng khi
  người yêu cầu là cán bộ, công chức, viên chức, người đang công tác trong lực lượng vũ trang.
- authorization: văn bản ủy quyền thực hiện việc đăng ký khai sinh.
- paper_declaration: TỜ KHAI ĐĂNG KÝ KHAI SINH bản giấy do người dân điền.
- other: tài liệu không thuộc các nhóm trên và không có thông tin nhân thân của người được khai sinh.
</type_definitions>

<title_rules>
- title là tên tài liệu tiếng Việt ngắn để hiển thị, đọc từ chính OCR.
- CCCD → "Căn cước công dân" (hoặc "Thẻ căn cước"/"Chứng minh nhân dân"/"Hộ chiếu" đúng loại đọc được);
  thẻ BHYT → "Thẻ bảo hiểm y tế"; giấy chứng nhận kết hôn → "Giấy chứng nhận kết hôn";
  trích lục khai tử → "Trích lục khai tử"; commitment → "Bản cam đoan";
  authorization → "Văn bản ủy quyền"; paper_declaration → "Tờ khai đăng ký".
- Một file GỘP NHIỀU giấy tờ khác nhau (các trang "Trang i/N" là những giấy khác loại hoặc của người khác
  nhau, vd CCCD + giấy chứng nhận kết hôn + CCCD cha mẹ) → title = "Hồ sơ giấy tờ cá nhân"; KHÔNG lấy tên
  giấy ở trang đầu. Nhiều trang của CÙNG một giấy (hai mặt một thẻ, nhiều trang một học bạ) vẫn đặt tên giấy đó.
</title_rules>

<output_contract>
Schema bắt buộc:
{"documents":[{"index":0,"type":"personal_document","title":"Căn cước công dân"}]}
Ví dụ: {"documents":[{"index":1,"type":"commitment","title":"Bản cam đoan"}]}
</output_contract>

<reminder>
CCCD/CMND/Hộ chiếu/BHYT/học bạ/bằng cấp/GCN kết hôn/trích lục khai tử LUÔN là personal_document.
Chỉ dựa vào OCR_TEXT.
</reminder>
""".strip()


_PAGE_RE = re.compile(r"(?m)^\W*Trang\s+\d+\s*/\s*\d+\W*$")


def _truncate_text(text: str, limit: int = 3000) -> str:
    """Rút gọn OCR cho LLM. File nhiều trang lấy PHẦN ĐẦU MỖI TRANG (giữ mốc trang) thay vì cắt cụt từ đầu:
    cắt cụt thì LLM chỉ thấy vài trang đầu, không nhận ra file là một bộ gộp nhiều giấy tờ."""
    marks = list(_PAGE_RE.finditer(text or ""))
    if len(marks) > 1:
        per_page = max(200, limit // len(marks))
        parts = []
        for k, m in enumerate(marks):
            body = text[m.end():(marks[k + 1].start() if k + 1 < len(marks) else len(text))]
            body = re.sub(r"\s+", " ", body).strip()
            parts.append(f"{m.group(0).strip()} {body[:per_page]}{'...' if len(body) > per_page else ''}")
        return " ".join(parts)
    text = re.sub(r"\s+", " ", text or "").strip()
    if len(text) <= limit:
        return text
    return text[:limit] + "..."


def build_user_prompt(documents: list[dict[str, Any]]) -> str:
    ocr_documents = [
        {"index": item.get("index"), "ocrText": _truncate_text(item.get("text", ""))}
        for item in documents
    ]
    return (
        "DANH SÁCH OCR_TEXT CỦA TỪNG TÀI LIỆU:\n"
        f"{json.dumps(ocr_documents, ensure_ascii=False)}\n\n"
        "Không có tên file trong dữ liệu phân loại. Hãy phân loại từng tài liệu chỉ theo ocrText."
    )


# Cài đặt "Tách giấy tờ" (options.splitDocuments): trước khi phân loại, chia mỗi tệp nhiều trang thành từng
# giấy riêng. Output cùng khuôn {"tep":[{"fileIndex","trangDau"}]} với bộ tách HKD để dùng chung page_starts.
SPLIT_SYSTEM_PROMPT = """
<persona>
Bạn chia bộ hồ sơ scan của thủ tục ĐĂNG KÝ KHAI SINH CHO NGƯỜI ĐÃ CÓ HỒ SƠ, GIẤY TỜ CÁ NHÂN thành từng
GIẤY TỜ riêng. Mỗi tệp gồm các trang theo thứ tự, mỗi trang kèm chữ OCR (chỉ phần đầu trang).
</persona>

<giay_to_cua_thu_tuc>
Tờ khai đăng ký khai sinh; bản cam đoan về việc chưa được đăng ký khai sinh; CCCD/CMND/thẻ căn cước/hộ chiếu
(của người được khai sinh, cha, mẹ, người đi nộp); thẻ BHYT; giấy tờ cư trú; học bạ; bằng tốt nghiệp; giấy
chứng nhận; chứng chỉ; giấy chứng nhận kết hôn của cha mẹ; trích lục khai tử/giấy chứng tử của cha hoặc mẹ;
văn bản xác nhận của thủ trưởng cơ quan; văn bản ủy quyền.
</giay_to_cua_thu_tuc>

<rules>
1. Trang 1 của mỗi tệp luôn mở một giấy.
2. Một trang MỞ GIẤY MỚI khi nó là trang đầu của một văn bản KHÁC với giấy trước: có quốc hiệu và tiêu đề văn
   bản riêng (TỜ KHAI, BẢN CAM ĐOAN, GIẤY CHỨNG NHẬN KẾT HÔN, TRÍCH LỤC KHAI TỬ, HỌC BẠ, BẰNG, GIẤY ỦY QUYỀN...),
   là thẻ căn cước/CCCD/thẻ BHYT, hoặc cùng loại nhưng khác người/khác số hiệu.
3. Tờ khai và bản cam đoan dài nhiều trang, trang sau KHÔNG có quốc hiệu: trang mở đầu bằng mục tiếp theo,
   phần "Tôi cam đoan", chữ ký người yêu cầu → CÙNG giấy trước. Các trang của một học bạ (từng năm học) là MỘT giấy.
4. Mặt trước + mặt sau CCCD của CÙNG một người là MỘT giấy. Mặt sau giấy chứng nhận, trang ký → cùng giấy.
5. Trang trắng, không đọc được, hoặc chỉ vài chữ rời rạc không có tiêu đề (mặt sau, nền hoa văn) thuộc giấy liền trước.
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
