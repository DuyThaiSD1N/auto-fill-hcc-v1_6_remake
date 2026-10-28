"""Phường Cam Đường (Lào Cai): thủ tục đất đai trên cổng dichvucong.laocai.gov.vn LUÔN tách giấy tờ.

Cán bộ hay scan cả bộ hồ sơ thành một PDF (đơn + CCCD + GCN + hợp đồng…), còn planner từng thủ tục phân
loại NGUYÊN TỆP nên cả bộ rơi vào một dòng. Với tài khoản Cam Đường:

1. OCR tệp gốc một lần; LLM đọc chữ từng trang, chỉ ra trang nào MỞ một giấy tờ mới → mỗi tệp chia thành
   các đoạn trang liền nhau, không bỏ trang nào.
2. Cắt mỗi đoạn thành một PDF con rồi chạy CHÍNH planner của thủ tục trên các PDF con (chữ OCR cấp sẵn qua
   ``ocr.preset_texts``, không OCR lần hai) → mỗi giấy vào đúng dòng thành phần hồ sơ của nó.
3. Đổi kế hoạch về tệp gốc bằng ``sourceSegments`` (extension tự cắt trang). Giấy nào planner không đính
   (không có dòng tương ứng) → thêm dòng "Giấy tờ khác" ở mục Thông tin khác, không bỏ giấy nào.

Cờ do server đặt theo tài khoản (``with_account_attach_options``), client không tự bật được. Trợ lý bản cũ
không có engine cắt trang (``supportsSourceSegments`` false) → giữ hành vi cũ. LLM chia giấy lỗi → planner
chạy trên tệp gốc như cũ.
"""

import base64
import json
import re
import time
from pathlib import Path

import fitz  # pymupdf

from app.config import settings
from app.pipelines._shared.naming import fold
from app.process.schemas import FileItem

# Thủ tục đất đai Lào Cai (cổng laocai.gov.vn). Ba thủ tục chủ trương đầu tư không thuộc nhóm này.
PROCEDURE_KEYS = frozenset({
    "cho-thue-dat-thue-rung",
    "chuyen-muc-dich-su-dung-dat-khoan-1-dieu-175",
    "chuyen-muc-dich-su-dung-dat-lao-cai",
    "dang-ky-bien-dong-chia-tach-to-chuc-lao-cai",
    "dang-ky-bien-dong-chuyen-nhuong-thua-ke-tang-cho-dvcqg-lao-cai",
    "dang-ky-bien-dong-dat-dai-lao-cai",
    "dang-ky-bien-dong-doi-ten-nguoi-su-dung-dat-lao-cai",
    "dang-ky-bien-dong-thoa-thuan-thanh-vien-ho-gia-dinh-theo-ban-an",
    "dang-ky-bien-phap-bao-dam-lao-cai",
    "dang-ky-cap-gcn-dien-tich-tang-them-nhan-chuyen-quyen-mot-phan-thua",
    "dang-ky-cap-gcn-dien-tich-tang-them-thay-doi-ranh-gioi",
    "dang-ky-cap-gcn-nhan-chuyen-nhuong-du-an-bat-dong-san-lao-cai",
    "dang-ky-dat-dai-cap-gcn-lan-dau-to-chuc",
    "dang-ky-dat-dai-lan-dau-ho-gia-dinh-lao-cai",
    "dang-ky-gcn-chuyen-quyen-truoc-2024-lao-cai",
    "dang-ky-thay-doi-bien-phap-bao-dam-lao-cai",
    "dieu-chinh-quyet-dinh-giao-dat-cap-xa-lao-cai",
    "dieu-chinh-quyet-dinh-giao-dat-lao-cai",
    "dinh-chinh-gcn-da-cap-dvcqg-lao-cai",
    "dinh-chinh-gcn-da-cap-lao-cai",
    "giao-thue-dat-lao-cai",
    "su-dung-dat-ket-hop-da-muc-dich-cap-xa",
    "tang-cho-qsdd-nha-nuoc-chua-cap-gcn",
    "thu-hoi-gcn-cap-lan-dau-khong-dung-quy-dinh-cap-lai",
    "to-chuc-kinh-te-nhan-chuyen-nhuong-qsdd-du-an",
    "xac-dinh-lai-dien-tich-dat-o-truoc-01-7-2004",
    "xac-nhan-tiep-tuc-su-dung-dat-nong-nghiep",
    "xac-nhan-tiep-tuc-su-dung-dat-nong-nghiep-lao-cai",
    "xoa-dang-ky-bien-phap-bao-dam-lao-cai",
})
ALWAYS_SPLIT_OPTION = "laoCaiAlwaysSplitDocuments"

_WARD_PREFIXES = ("xa ", "phuong ", "thi tran ")
# Header trang dịch vụ OCR chèn vào text: "───── Trang 2/4 ─────".
_PAGE_HEADER_RE = re.compile(r"(?im)^[\t ─-╿-]*(?:trang|page)\s+(\d+)\s*/\s*(\d+)[\t ─-╿-]*$")
_FALLBACK_NAME = "Tài liệu khác"
_MAX_NAME = 60


def is_lao_cai_cam_duong(user: dict | None) -> bool:
    """Tỉnh Lào Cai + phường Cam Đường; xã khớp ĐÚNG tên sau khi bỏ tiền tố."""
    if not user:
        return False
    xa = fold(user.get("xa") or "")
    for prefix in _WARD_PREFIXES:
        if xa.startswith(prefix):
            xa = xa[len(prefix):].strip()
            break
    return "lao cai" in fold(user.get("tinh") or "") and xa == "cam duong"


def with_account_attach_options(options: dict | None, user: dict | None, procedure: str) -> dict:
    """Bản sao options với cờ luôn tách giấy tờ do server quyết theo tài khoản."""
    result = dict(options or {})
    result.pop(ALWAYS_SPLIT_OPTION, None)
    if procedure in PROCEDURE_KEYS and is_lao_cai_cam_duong(user):
        result[ALWAYS_SPLIT_OPTION] = True
    return result


def always_split(options: dict | None) -> bool:
    opts = options or {}
    return opts.get(ALWAYS_SPLIT_OPTION) is True and opts.get("supportsSourceSegments") is not False


SYSTEM_PROMPT = """
<persona>
Bạn chia bộ hồ sơ scan của thủ tục đất đai thành từng GIẤY TỜ riêng. Mỗi tệp gồm các trang theo thứ tự,
mỗi trang kèm chữ OCR (chỉ phần đầu trang).
</persona>

<rules>
1. Trang 1 của mỗi tệp luôn mở một giấy.
2. Một trang MỞ GIẤY MỚI khi nó là trang đầu của một văn bản KHÁC với giấy trước: có quốc hiệu/tiêu đề
   riêng (đơn, tờ khai, CCCD, Giấy chứng nhận quyền sử dụng đất, hợp đồng, quyết định, biên bản, trích
   lục/trích đo/sơ đồ thửa đất, giấy ủy quyền, giấy khai sinh/kết hôn/khai tử, văn bản thuế, bản án...)
   hoặc cùng loại nhưng khác số hiệu/khác người.
3. KHÔNG mở giấy mới cho trang nối tiếp của cùng văn bản: nội dung tiếp theo, trang ký, phụ lục, mặt
   sau, trang 2-3-4 và trang bổ sung của Giấy chứng nhận, lời chứng của công chứng/chứng thực ở cuối hợp
   đồng. Mặt trước + mặt sau CCCD của CÙNG một người là MỘT giấy.
4. Trang trắng hoặc không đọc được thuộc giấy liền trước.
5. Không chắc → KHÔNG tách. Tách sai tệ hơn không tách.
6. Chỉ dùng chữ OCR, không dùng tên tệp. Trả DUY NHẤT một JSON object, không markdown, không giải thích.
</rules>

<ten>
"ten": tên tiếng Việt ngắn gọn (tối đa khoảng 60 ký tự) theo nội dung giấy, sẽ được gõ vào ô "Tên giấy tờ"
khi giấy không có dòng riêng: "Hợp đồng chuyển nhượng QSDĐ", "CCCD Trần Thị B", "GCN QSDĐ số CS 01234".
OCR quá thiếu → để trống, đừng bịa.
</ten>

<output_contract>
{"tep":[{"fileIndex":0,"giayTo":[{"trangDau":1,"ten":"Đơn đăng ký biến động"},{"trangDau":3,"ten":"CCCD Trần Thị B"}]}]}
Mỗi tệp đầu vào đúng một phần tử "tep"; "giayTo" xếp theo trangDau tăng dần.
</output_contract>
""".strip()


def _user_prompt(pages_by_file: dict[int, list[str]]) -> str:
    payload = [
        {"fileIndex": i, "soTrang": len(pages),
         "trang": [{"trang": n + 1, "ocr": re.sub(r"\s+", " ", t).strip()[:1200]} for n, t in enumerate(pages)]}
        for i, pages in pages_by_file.items()
    ]
    return "HỒ SƠ:\n" + json.dumps(payload, ensure_ascii=False)


def split_pages(text: str) -> list[str]:
    """Text OCR theo trang (header "───── Trang i/n ─────"). Không có header → 1 trang."""
    matches = list(_PAGE_HEADER_RE.finditer(text or ""))
    if not matches:
        return [text or ""]
    total = max(int(m.group(2)) for m in matches)
    pages = [""] * max(total, len(matches))
    for pos, match in enumerate(matches):
        end = matches[pos + 1].start() if pos + 1 < len(matches) else len(text)
        number = int(match.group(1))
        if 1 <= number <= len(pages):
            pages[number - 1] = text[match.end():end].strip()
    return pages


def _join_pages(pages: list[str]) -> str:
    return "\n".join(f"───── Trang {n + 1}/{len(pages)} ─────\n{page}" for n, page in enumerate(pages))


def _pdf_bytes(file: dict) -> bytes | None:
    header, sep, payload = str(file.get("dataUrl") or "").partition(",")
    if not sep or "pdf" not in (header.lower() + str(file.get("type") or "").lower()):
        return None
    try:
        return base64.b64decode(payload)
    except ValueError:
        return None


def _cut_pdf(raw: bytes, pages: list[int]) -> str:
    """PDF con gồm các trang (0-based, liền nhau) → data URL."""
    with fitz.open(stream=raw, filetype="pdf") as doc, fitz.open() as out:
        out.insert_pdf(doc, from_page=pages[0], to_page=pages[-1])
        data = out.tobytes(garbage=3, deflate=True)
    return "data:application/pdf;base64," + base64.b64encode(data).decode("ascii")


def _clean_name(raw: str) -> str:
    text = re.sub(r"[^\w\s,.()\-]", " ", str(raw or "").replace("/", "-"))
    return re.sub(r"\s+", " ", text).strip(" -,.")[:_MAX_NAME].strip(" -,.")


def _page_starts(data: dict, pages_by_file: dict[int, list[str]]) -> dict[int, list[tuple[int, str]]]:
    """JSON LLM → {tệp: [(trang đầu 0-based, tên)]}; trang 1 luôn mở giấy, bỏ số trang ngoài tệp."""
    out: dict[int, list[tuple[int, str]]] = {}
    for item in data.get("tep") or []:
        if not isinstance(item, dict):
            continue
        try:
            file_index = int(item.get("fileIndex"))
        except (TypeError, ValueError):
            continue
        count = len(pages_by_file.get(file_index) or [])
        if not count or file_index in out:
            continue
        starts: dict[int, str] = {0: ""}
        for doc in item.get("giayTo") or []:
            try:
                page = int(doc.get("trangDau")) - 1
            except (AttributeError, TypeError, ValueError):
                continue
            if 0 <= page < count and not starts.get(page):
                starts[page] = _clean_name(doc.get("ten") or "")
        out[file_index] = sorted(starts.items())
    return out


async def _segment(pages_by_file: dict[int, list[str]]) -> dict[int, list[tuple[int, str]]]:
    from app.services.llm import client

    messages = [{"role": "system", "content": SYSTEM_PROMPT}, {"role": "user", "content": _user_prompt(pages_by_file)}]
    total = sum(len(p) for p in pages_by_file.values())
    for attempt in range(2):  # JSON hỏng → hỏi lại một lần
        raw = await client.chat(messages, max_tokens=max(400, min(4000, 120 + 60 * total)),
                                enable_thinking=settings.agent_reasoning)
        try:
            return _page_starts(client.extract_json_block(raw), pages_by_file)
        except Exception:  # noqa: BLE001
            if attempt:
                raise
    return {}


def build_segments(raw_files: list[dict], texts: dict[int, str], starts: dict[int, list[tuple[int, str]]]) -> list[dict]:
    """Đoạn = một giấy: {source, pages (0-based; None = cả tệp), name, file (tệp ảo cho planner), text}."""
    segments: list[dict] = []
    for index, file in enumerate(raw_files):
        text = texts.get(index)
        pages = split_pages(text) if text else []
        file_starts = starts.get(index) or []
        raw = _pdf_bytes(file) if len(file_starts) > 1 else None
        count = None
        if raw is not None:
            with fitz.open(stream=raw, filetype="pdf") as doc:
                count = doc.page_count
        if raw is None or count != len(pages):
            # Không tách được (ảnh, một giấy, số trang OCR lệch PDF) → nguyên tệp.
            name = file_starts[0][1] if file_starts else ""
            segments.append({"source": index, "pages": None, "name": name, "file": file, "text": text})
            continue
        stem = Path(str(file.get("name") or f"file-{index + 1}")).stem
        bounds = [s for s, _ in file_starts] + [count]
        for (first, name), end in zip(file_starts, bounds[1:]):
            part = list(range(first, end))
            label = f"{first + 1}" if len(part) == 1 else f"{first + 1}-{end}"
            segments.append({
                "source": index,
                "pages": part,
                "name": name,
                "file": {**file, "name": f"{stem}_trang_{label}.pdf", "type": "application/pdf",
                         "dataUrl": _cut_pdf(raw, part)},
                "text": _join_pages(pages[first:end]),
            })
    return segments


def _sources(item: dict, segments: list[dict]) -> list[tuple[int, list[int] | None, int]]:
    """(tệp gốc, trang 0-based hoặc None = cả tệp, chỉ số đoạn) mà một mục kế hoạch lấy từ các tệp ảo."""
    out = []
    for seg_ref in item.get("sourceSegments") or []:
        v = int(seg_ref["fileIndex"])
        seg, rel = segments[v], seg_ref.get("pageIndexes")
        if seg["pages"] is None:
            out.append((seg["source"], rel, v))
        else:
            out.append((seg["source"], list(seg["pages"]) if rel is None else [seg["pages"][k] for k in rel], v))
    if out:
        return out
    merged = item.get("sourceFileIndexes") or []
    for v in (merged if len(merged) > 1 else [item["fileIndex"]]):
        out.append((segments[int(v)]["source"], segments[int(v)]["pages"], int(v)))
    return out


def _with_sources(item: dict, sources: list[tuple[int, list[int] | None, int]]) -> dict:
    out = {k: v for k, v in item.items() if k not in ("sourceSegments", "sourceFileIndexes")}
    out["fileIndex"] = sources[0][0]
    if all(pages is None for _, pages, _ in sources):
        if len(sources) > 1:
            out["sourceFileIndexes"] = [source for source, _, _ in sources]
    else:
        out["sourceSegments"] = [{"fileIndex": source, "pageIndexes": pages} for source, pages, _ in sources]
    return out


def remap_plan(attachments: list[dict], segments: list[dict]) -> tuple[list[dict], list[str]]:
    """Kế hoạch trên tệp ảo → kế hoạch trên tệp gốc; đoạn không mục nào đính → dòng "Giấy tờ khác"."""
    out: list[dict] = []
    used: set[int] = set()
    for item in attachments:
        sources = _sources(item, segments)
        used.update(v for _, _, v in sources)
        out.append(_with_sources(item, sources))

    taken = {fold(str(a.get("componentName") or "")) for a in out if a.get("target") == "new"}
    added: list[str] = []
    for v, seg in enumerate(segments):
        if v in used:
            continue
        base = seg["name"] or _FALLBACK_NAME
        name, suffix = base, 2
        while fold(name) in taken:
            name, suffix = f"{base[:52].strip()} {suffix}", suffix + 1
        taken.add(fold(name))
        out.append(_with_sources({
            "fileIndex": v,
            "fileName": seg["file"].get("name"),
            "documentName": name,
            # Engine otherListFile của FE thêm dòng "Giấy tờ khác", gõ tên rồi mới gán tệp.
            "componentName": name,
            "target": "new",
            "needsAddComponent": True,
            "detectedType": "other",
            # Cổng iGate VNPT: bấm "Chọn tệp tin" mở hộp thoại file của hệ điều hành → gán thẳng.
            "noChooserClick": True,
        }, [(seg["source"], seg["pages"], v)]))
        added.append(f"{seg['file'].get('name')} → \"{name}\"")
    return out, added


async def plan_with_split(plan_fn, files: list[FileItem], options: dict | None = None,
                          session: dict | None = None) -> dict:
    from app.services import ocr

    raw_files = [{"name": f.name, "type": f.type, "dataUrl": f.dataUrl, "role": f.role} for f in files]
    started = time.monotonic()
    ocr_results = await ocr.ocr_per_file(raw_files)
    ocr_ms = int((time.monotonic() - started) * 1000)
    texts = {i: str(r.get("text") or "") for i, r in enumerate(ocr_results)
             if not r.get("error") and str(r.get("text") or "").strip()}
    pages_by_file = {i: split_pages(t) for i, t in texts.items()}

    errors: list[str] = []
    started = time.monotonic()
    starts: dict[int, list[tuple[int, str]]] = {}
    try:
        if pages_by_file:
            starts = await _segment(pages_by_file)
    except Exception as exc:  # noqa: BLE001 — chia giấy hỏng thì planner chạy trên tệp gốc
        errors.append(f"Tách giấy tờ (Cam Đường): {exc} — đính nguyên tệp.")
    split_ms = int((time.monotonic() - started) * 1000)

    segments = build_segments(raw_files, texts, starts)
    virtual = [FileItem(**seg["file"]) for seg in segments]
    with ocr.preset_texts({seg["file"]["dataUrl"]: seg["text"] for seg in segments if seg["text"]}):
        result = await plan_fn(virtual, options, session)

    result.pop("replaceFiles", None)  # chỉ số tệp ảo — Lào Cai không nén tệp
    attachments, added = remap_plan(result.get("attachments") or [], segments)
    result["attachments"] = attachments
    if added:
        errors.append("Giấy không có dòng thành phần hồ sơ tương ứng, đã đính vào \"Giấy tờ khác\" (Thông tin "
                      f"khác): {', '.join(added)}.")
    result["errors"] = [*errors, *(result.get("errors") or [])]
    result["extracted"] = {
        **(result.get("extracted") or {}),
        "tachGiayTo": [
            {"fileName": raw_files[seg["source"]]["name"], "name": seg["name"],
             "pages": "cả tệp" if seg["pages"] is None else [p + 1 for p in seg["pages"]]}
            for seg in segments
        ],
    }
    stats = dict(result.get("stats") or {})
    stats["ocr_latency_ms"] = int(stats.get("ocr_latency_ms") or 0) + ocr_ms
    stats["llm_latency_ms"] = int(stats.get("llm_latency_ms") or 0) + split_ms
    stats["total_latency_ms"] = int(stats.get("total_latency_ms") or 0) + ocr_ms + split_ms
    result["stats"] = stats
    return result
