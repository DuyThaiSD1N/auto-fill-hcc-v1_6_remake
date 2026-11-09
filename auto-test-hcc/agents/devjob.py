"""Job "Thêm thủ tục mới": người dùng nhập link kê khai, kéo thả Excel mapping điền + ảnh ánh xạ đính kèm + file mẫu, agent làm
pipeline điền và đính kèm.

Phân vai như job sửa lỗi: agent viết code; thêm link kê khai, chuyển tài liệu, chạy test, build, chạy thử file mẫu, hoàn tác
đều do mã ở đây làm. Kết quả nằm trong thư mục làm việc, chưa commit, người dùng xem rồi tự commit.
"""
from __future__ import annotations

import json
import mimetypes
import re
import unicodedata
import uuid
from datetime import datetime
from pathlib import Path

import codeguard
import replay
import roles
import verify
from config import (
    BE, DEV_AGENT_BUDGET_USD, DEV_FILE_MAX_MB, DEV_JOB_BUDGET_USD, DEV_MAX_REPAIRS, DEV_TIMEOUT_S, DEV_TOTAL_MAX_MB, REPO, TROLY,
)
from orchestrator import Job, JobError, Orchestrator, now

LINKS = BE / "app/procedures/data/ke_khai_links.json"
KEY_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
CODE_RE = re.compile(r"^\d{1,2}\.\d{6}$")
GROUPS = {
    "mapping": {".xlsx", ".xlsm", ".csv"},
    "attach": {".png", ".jpg", ".jpeg", ".webp", ".gif"},
    "samples": {".pdf", ".png", ".jpg", ".jpeg", ".webp", ".docx"},
}
GROUP_LABELS = {"mapping": "Excel mapping điền", "attach": "Ảnh ánh xạ đính kèm", "samples": "File mẫu"}
# Thứ tự khoá như các entry đang có trong ke_khai_links.json.
_LINK_ORDER = ("key", "code", "label", "url", "needsAgencySelect", "provinceOnlyAgency", "selectSo", "autoConfirm")
_OPTIONAL_FLAGS = ("provinceOnlyAgency", "selectSo")  # chỉ ghi khi bật, như các entry sẵn có
_MAX_SHEET_ROWS = 2000


class InputError(ValueError):
    """Dữ liệu người dùng gửi lên không dùng được: báo lại nguyên văn trên web."""


# ---- link kê khai ------------------------------------------------------------------------------------------------

def read_links() -> list[dict]:
    return json.loads(LINKS.read_text(encoding="utf-8"))["links"]


def find_link(key: str) -> dict | None:
    return next((link for link in read_links() if link.get("key") == key), None)


def pipeline_folder(key: str) -> str:
    return key.replace("-", "_")


def link_check(key: str, code: str) -> dict:
    """Kiểm key/mã trước khi tạo job: key đã có thì chỉ làm pipeline cho link sẵn có; mã trùng thì báo để khỏi làm trùng."""
    links = read_links()
    entry = next((link for link in links if link.get("key") == key), None) if key else None
    same_code = [{"key": link["key"], "label": link.get("label", "")} for link in links if code and link.get("code") == code]
    folder = pipeline_folder(key) if key else ""
    return {
        "key": key,
        "keyValid": bool(KEY_RE.match(key)) if key else False,
        "keyExists": entry is not None,
        "entry": entry,
        "sameCode": [item for item in same_code if item["key"] != key],
        "pipelineExists": bool(folder) and (BE / "app/pipelines" / folder).is_dir(),
        "folder": folder,
    }


def validate_procedure(proc: dict) -> list[str]:
    """Lỗi chặn tạo job. Trả danh sách rỗng là hợp lệ."""
    problems = []
    key = proc.get("key", "")
    if not KEY_RE.match(key):
        problems.append("Key chỉ gồm chữ thường không dấu, số và dấu gạch ngang (vd dang-ky-tai-san-khanh-hoa).")
    exists = find_link(key) is not None
    if proc.get("newLink") and exists:
        problems.append(f"Key {key} đã có trong ke_khai_links.json. Chọn \"Dùng link có sẵn\" hoặc đặt key khác.")
    if not proc.get("newLink") and not exists:
        problems.append(f"Không có key {key} trong ke_khai_links.json để dùng lại.")
    if proc.get("newLink"):
        if proc.get("code") and not CODE_RE.match(proc["code"]):
            problems.append("Mã thủ tục phải có dạng 1.013831.")
        url = proc.get("url", "")
        if not re.match(r"^https://[^/\s]+\.gov\.vn(/|$|#|\?)", url):
            problems.append("URL phải là trang https của cổng .gov.vn (vd https://dichvucong.gov.vn/thu-tuc-hanh-chinh/...).")
    return problems


def build_entry(proc: dict) -> dict:
    values = {
        "key": proc["key"], "code": proc.get("code", ""), "label": proc["label"].strip(), "url": proc.get("url", "").strip(),
        "needsAgencySelect": bool(proc.get("needsAgencySelect")), "autoConfirm": bool(proc.get("autoConfirm")),
        **{flag: True for flag in _OPTIONAL_FLAGS if proc.get(flag)},
    }
    if not values["code"]:
        values.pop("code")
    return {k: values[k] for k in _LINK_ORDER if k in values}


def add_link(entry: dict) -> None:
    """Thêm cuối danh sách. json.dumps(indent=2) ra đúng định dạng file đang có, ghi LF như file gốc."""
    data = json.loads(LINKS.read_text(encoding="utf-8"))
    if any(link.get("key") == entry["key"] for link in data["links"]):
        raise JobError(f"Key {entry['key']} vừa có người thêm vào ke_khai_links.json, không thêm trùng.")
    data["links"].append(entry)
    LINKS.write_bytes(json.dumps(data, ensure_ascii=False, indent=2).encode("utf-8"))


# ---- tài liệu đầu vào --------------------------------------------------------------------------------------------

def safe_name(name: str) -> str:
    """Giữ tên tiếng Việt cho dễ nhìn, bỏ ký tự cấm trên Windows và đường dẫn con."""
    name = unicodedata.normalize("NFC", Path(name.replace("\\", "/")).name).strip()
    name = re.sub(r'[<>:"/|?*\x00-\x1f]', "_", name).strip(". ")
    return name[:120] or "tep"


def check_upload(group: str, name: str, size: int) -> None:
    if group not in GROUPS:
        raise InputError(f"Nhóm tệp không hợp lệ: {group}")
    suffix = Path(name).suffix.lower()
    if suffix not in GROUPS[group]:
        hint = " Lưu lại dạng .xlsx rồi gửi." if suffix == ".xls" else ""
        raise InputError(f"{GROUP_LABELS[group]} không nhận tệp {suffix or '(không đuôi)'}: {name}.{hint}")
    if size > DEV_FILE_MAX_MB * 1024 * 1024:
        raise InputError(f"Tệp {name} quá {DEV_FILE_MAX_MB} MB.")
    if size == 0:
        raise InputError(f"Tệp {name} rỗng.")


def save_inputs(job_dir: Path, files: list[tuple[str, str, bytes]]) -> list[dict]:
    if sum(len(data) for _, _, data in files) > DEV_TOTAL_MAX_MB * 1024 * 1024:
        raise InputError(f"Tổng dung lượng tệp vượt {DEV_TOTAL_MAX_MB} MB.")
    saved = []
    for group, name, data in files:
        check_upload(group, name, len(data))
        folder = job_dir / "inputs" / group
        folder.mkdir(parents=True, exist_ok=True)
        clean = safe_name(name)
        target = folder / clean
        n = 2
        while target.exists():  # hai tệp cùng tên (vd ảnh dán từ clipboard): đánh số, không đè
            target = folder / f"{Path(clean).stem} ({n}){Path(clean).suffix}"
            n += 1
        target.write_bytes(data)
        saved.append({"group": group, "name": target.name, "path": target.relative_to(REPO).as_posix(), "size": len(data)})
    return saved


def _cell_text(value) -> str:
    if value is None:
        return ""
    if isinstance(value, datetime):
        return value.strftime("%d/%m/%Y")
    text = str(value).strip()
    return text.replace("|", "\\|").replace("\r\n", "<br>").replace("\n", "<br>")


def excel_to_markdown(path: Path, images_dir: Path) -> tuple[str, list[Path]]:
    """Agent không đọc được .xlsx: chuyển mỗi sheet thành bảng markdown. Ô gộp điền lại giá trị ô đầu để không mất nghĩa
    hàng/cột; ghi chú trong ô và ảnh nhúng (thường là ảnh chụp ô trên cổng) xuất riêng để agent xem được."""
    import openpyxl  # nạp khi cần: dịch vụ vẫn chạy được nếu máy chưa cài, chỉ job có Excel mới báo lỗi

    try:
        book = openpyxl.load_workbook(path, data_only=True)
    except Exception as reason:  # noqa: BLE001 — tệp hỏng, có mật khẩu, không phải xlsx thật
        raise InputError(f"Không đọc được file Excel {path.name}: {reason}") from reason
    parts = [f"# {path.name}", ""]
    images: list[Path] = []
    for sheet in book.worksheets:
        rows = [[cell.value for cell in row] for row in sheet.iter_rows(max_row=min(sheet.max_row, _MAX_SHEET_ROWS))]
        for merged in sheet.merged_cells.ranges:
            top = sheet.cell(merged.min_row, merged.min_col).value
            for r in range(merged.min_row - 1, min(merged.max_row, len(rows))):
                for c in range(merged.min_col - 1, merged.max_col):
                    if c < len(rows[r]):
                        rows[r][c] = top
        rows = [[_cell_text(v) for v in row] for row in rows]
        rows = [row for row in rows if any(row)]
        used = [i for i in range(max((len(r) for r in rows), default=0)) if any(i < len(r) and r[i] for r in rows)]
        parts.append(f"## Sheet: {sheet.title}")
        if not rows:
            parts += ["(trống)", ""]
        else:
            table = [[row[i] if i < len(row) else "" for i in used] for row in rows]
            parts.append("| " + " | ".join(table[0]) + " |")
            parts.append("|" + "---|" * len(used))
            parts += ["| " + " | ".join(row) + " |" for row in table[1:]]
            if sheet.max_row > _MAX_SHEET_ROWS:
                parts.append(f"(cắt ở {_MAX_SHEET_ROWS} dòng, sheet có {sheet.max_row} dòng)")
            parts.append("")
        notes = [f"- Ô {cell.coordinate}: {cell.comment.text.strip()}" for row in sheet.iter_rows() for cell in row if cell.comment]
        if notes:
            parts += ["Ghi chú trong ô:", *notes, ""]
        for n, image in enumerate(getattr(sheet, "_images", []) or [], 1):
            try:
                data = image._data()
            except Exception:  # noqa: BLE001 — ảnh nhúng dạng lạ: bỏ qua, vẫn còn file Excel gốc
                continue
            images_dir.mkdir(parents=True, exist_ok=True)
            target = images_dir / f"{safe_name(path.stem)} - {safe_name(sheet.title)} - anh {n}.png"
            target.write_bytes(data)
            images.append(target)
            parts.append(f"- Ảnh nhúng {n} của sheet: {target.relative_to(REPO).as_posix()}")
        parts.append("")
    return "\n".join(parts), images


def csv_to_markdown(path: Path) -> str:
    import csv

    text = path.read_bytes().decode("utf-8-sig", errors="replace")
    rows = [[_cell_text(v) for v in row] for row in csv.reader(text.splitlines()) if any(v.strip() for v in row)]
    if not rows:
        return f"# {path.name}\n\n(trống)\n"
    width = max(len(r) for r in rows)
    rows = [r + [""] * (width - len(r)) for r in rows]
    return "\n".join([f"# {path.name}", "", "| " + " | ".join(rows[0]) + " |", "|" + "---|" * width,
                      *["| " + " | ".join(r) + " |" for r in rows[1:]], ""])


def docx_to_text(path: Path) -> str:
    import docx

    try:
        document = docx.Document(str(path))
    except Exception as reason:  # noqa: BLE001
        raise InputError(f"Không đọc được file Word {path.name}: {reason}") from reason
    lines = [p.text for p in document.paragraphs if p.text.strip()]
    for table in document.tables:
        for row in table.rows:
            lines.append(" | ".join(cell.text.strip() for cell in row.cells))
    return "\n".join(lines) + "\n"


def convert_inputs(inputs: list[dict]) -> list[dict]:
    """Tạo bản chữ cho tệp agent không đọc thẳng được. Trả các mục mới (có ``source`` = tệp gốc)."""
    derived = []
    for item in inputs:
        path = REPO / item["path"]
        suffix = path.suffix.lower()
        text = None
        extra: list[Path] = []
        if suffix in (".xlsx", ".xlsm"):
            text, extra = excel_to_markdown(path, path.parent / "anh-nhung")
        elif suffix == ".csv":
            text = csv_to_markdown(path)
        elif suffix == ".docx":
            text = docx_to_text(path)
        if text is None:
            continue
        target = path.with_name(f"{path.name}.md")
        target.write_text(text, encoding="utf-8")
        derived.append({"group": item["group"], "name": target.name, "path": target.relative_to(REPO).as_posix(),
                        "size": target.stat().st_size, "source": item["name"]})
        derived += [{"group": item["group"], "name": image.name, "path": image.relative_to(REPO).as_posix(),
                     "size": image.stat().st_size, "source": item["name"]} for image in extra]
    return derived


# ---- job ---------------------------------------------------------------------------------------------------------

def create_job(*, procedure: dict, notes: str, created_by: str, settings: dict, files: list[tuple[str, str, bytes]],
               warnings: list[str]) -> Job:
    job_id = f"at_{datetime.now().strftime('%y%m%d%H%M%S')}{uuid.uuid4().hex[:4]}"
    job = Job({
        "id": job_id,
        "kind": "dev",
        "requestId": procedure["key"],
        "description": notes,
        "createdAt": now(),
        "createdBy": created_by,
        "settings": settings,
        "status": "queued",
        "stage": "inputs",
        "outcome": None,
        "error": None,
        "warnings": warnings,
        "human": None,
        "case": {"label": procedure["label"], "procedure": procedure["key"]},
        "procedure": procedure,
        "inputs": [],
        "link": None,
        "attempts": [],
        "reproduce": None,
        "rounds": [],
        "fix": None,
        "report": None,
        "cost": {"usd": 0.0, "calls": 0},
        "touched": [],
        "stackDirty": False,
        "events": [],
    })
    job.dir.mkdir(parents=True, exist_ok=True)
    try:
        job.data["inputs"] = save_inputs(job.dir, files)
    except InputError:
        import shutil

        shutil.rmtree(job.dir, ignore_errors=True)
        raise
    job.save()
    return job


def _mime(name: str) -> str:
    return mimetypes.guess_type(name)[0] or "application/octet-stream"


def private_terms(fields: list[dict]) -> set[str]:
    """Chuỗi nhận diện người thật trong kết quả chạy thử file mẫu, để quét patch.

    Khác job sửa lỗi ở địa chỉ: thủ tục mới hay phải viết tên phường/xã, cơ quan vào code (bảng cơ quan, remap), nên chỉ coi
    địa chỉ là dữ liệu cá nhân khi có số (số nhà, số thôn, tổ); không thì agent bị trả về sửa oan.
    """
    terms: set[str] = set()
    for field in fields or []:
        value = field.get("value")
        if not isinstance(value, str):
            continue
        name = str(field.get("name") or "")
        digits = re.sub(r"\D", "", value)
        if len(digits) >= 9:
            terms.add(digits)
        if codeguard._NAME_FIELD.search(name) and len(value.split()) >= 2:
            terms.add(codeguard._norm(value))
        if codeguard._ADDRESS_FIELD.search(name) and len(value) >= 15 and re.search(r"\d", value):
            terms.add(codeguard._norm(value))
    return {t for t in terms if t}


def _filled(value) -> bool:
    return value not in (None, "", [], {}) and not (isinstance(value, str) and not value.strip())


class DevOrchestrator(Orchestrator):
    """Dùng lại vòng đời của Orchestrator (dừng, lỗi, hoàn tác, build lại), thay phần giữa bằng luồng làm thủ tục."""

    def __init__(self, job: Job, credentials: dict):
        super().__init__(job, credentials)
        self.troly = bool(self.settings.get("troLy"))
        self.guard = codeguard.Guard(job.dir, troly=self.troly)
        self.budget = DEV_JOB_BUDGET_USD
        self.proc = job.data["procedure"]
        self.folder = pipeline_folder(self.proc["key"])

    @property
    def on_portal(self) -> bool:
        # Không chạy cổng, nhưng thủ tục mới hay phải sửa cả extension: cho extension vào phạm vi sửa và hoàn tác.
        return True

    def _run(self) -> None:
        self._prepare()
        before = self._baselines()
        self.guard.take()
        self._link()
        self._develop(before)

    # ---- chuẩn bị --------------------------------------------------------------------------------------------------

    def _prepare(self) -> None:
        self._stage("inputs", "Chuẩn bị tài liệu: chuyển Excel/Word sang chữ cho agent đọc…")
        inputs = self.job.data["inputs"]
        try:
            derived = convert_inputs([i for i in inputs if not i.get("source")])
        except InputError as reason:
            raise JobError(str(reason)) from reason
        with self.job.lock:
            self.job.data["inputs"] = [i for i in inputs if not i.get("source")] + derived
        self.job.save()
        counts = {g: sum(1 for i in inputs if i["group"] == g and not i.get("source")) for g in GROUPS}
        self.job.log(f"Nhận {counts['mapping']} file mapping, {counts['attach']} ảnh ánh xạ, {counts['samples']} file mẫu.")
        if not counts["mapping"]:
            self._warn("Không có Excel mapping điền: agent phải tự suy tên ô từ thủ tục tương tự, kiểm kỹ phần giả định.")
        if not counts["samples"]:
            self._warn("Không có file mẫu nên không chạy thử được pipeline trên giấy tờ thật.")

    def _baselines(self) -> dict:
        self._stage("baseline", "Đo test hiện tại để làm mốc so sau khi agent viết code…")
        before = {"backend": verify.baseline(self.job.cancel)}
        if before["backend"].get("broken"):
            raise JobError("Bộ test backend đang hỏng từ trước, không có mốc để so: " + before["backend"].get("tail", "")[-300:])
        before["extension"] = verify.extension_baseline(self.job.cancel)
        if self.troly:
            before["troly"] = verify.extension_baseline(self.job.cancel, TROLY)
            before["handfree"] = verify.handfree_baseline(self.job.cancel)
        return before

    def _link(self) -> None:
        self._stage("link", "Thêm link kê khai…")
        key = self.proc["key"]
        if self.proc.get("newLink"):
            entry = build_entry(self.proc)
            add_link(entry)
            self.touched.append(str(LINKS))  # để hoàn tác cùng phần agent sửa
            self.job.update(link={"added": True, "entry": entry}, touched=list(self.touched))
            self.job.log(f"Đã thêm {key} vào ke_khai_links.json.")
        else:
            entry = find_link(key)
            if not entry:
                raise JobError(f"Không còn key {key} trong ke_khai_links.json.")
            self.job.update(link={"added": False, "entry": entry})
            self.job.log(f"Dùng link có sẵn {key}.")

    # ---- agent viết + kiểm chứng ------------------------------------------------------------------------------------

    def _ask_developer(self, prompt: str, resume: str | None = None):
        result = self._agent(
            "Lập trình viên", "developer", roles.DEV_SYSTEM, prompt, roles.DEV_SCHEMA,
            can_edit=True, resume=resume, timeout=DEV_TIMEOUT_S,
            write=True, edit_troly=self.troly, budget=DEV_AGENT_BUDGET_USD,
        )
        self.denied += result.denied
        return result

    def _develop(self, before: dict) -> None:
        job = self.job
        self._stage("build", "Agent bắt đầu làm thủ tục (đọc tài liệu, chép khuôn thủ tục tương tự, viết pipeline và test)…")
        job.log("Bắt đầu làm thủ tục", who="Lập trình viên")
        result = self._ask_developer(roles.dev_prompt(job.data, job.data["inputs"]))
        session = result.session_id
        for repair in range(DEV_MAX_REPAIRS + 1):
            attempt = {"n": repair + 1, "output": result.output, "cost": result.cost, "files": [], "patch": "",
                       "tests": None, "deploy": None, "smoke": None, "problem": None}
            with job.lock:
                job.data["attempts"].append(attempt)
            job.save()
            problem = self._verify(attempt, result.output, before)
            if problem is None:
                return self._accept_dev(attempt)
            with job.lock:
                attempt["problem"] = problem[:3000]
            job.save()
            job.log(f"Lần {repair + 1} chưa đạt: {problem[:300]}", level="warn")
            if repair == DEV_MAX_REPAIRS:
                break
            self._stage("build", f"Trả lỗi lại cho agent sửa tiếp (lần {repair + 1}/{DEV_MAX_REPAIRS})…")
            result = self._ask_developer(f"Hệ thống kiểm tra báo lỗi:\n\n{problem}\n\nHãy sửa tiếp cho đạt.", resume=session)
            session = result.session_id or session
        self._rollback()
        self._finish("dev_failed", f"Đã cho agent sửa {DEV_MAX_REPAIRS} lần mà chưa đạt. Lỗi cuối: {problem[:600]}")

    def _verify(self, attempt: dict, output: dict, before: dict) -> str | None:
        """Trả mô tả lỗi để agent sửa tiếp, None nếu đạt hết: phạm vi, test, build, chạy thử, quét dữ liệu thật."""
        job = self.job
        self._stage("test", "Kiểm tra code agent vừa viết…")
        changes, outside = self.guard.changes(self.touched, True)
        escaped = [path for path in outside if path not in self.denied]
        if escaped:
            raise JobError(f"Agent sửa ngoài phạm vi cho phép: {', '.join(escaped)}. Hãy xem lại các file này.")
        patch = codeguard.make_patch(changes)
        with job.lock:
            attempt["files"] = [c.rel for c in changes]
            attempt["patch"] = patch
            attempt["tests"] = {}
        job.save()
        if not (BE / "app/pipelines" / self.folder).is_dir():
            return (f"Chưa có thư mục pipeline auto-fill-hcc-backend/app/pipelines/{self.folder}/. Tên thư mục phải đúng key "
                    f"{self.proc['key']} đổi - thành _ (CLAUDE.md).")

        if codeguard.touches_extension(changes):
            job.log("Chạy bộ test extension Auto Fill…")
            compared = verify.compare_extension(before["extension"], verify.extension_tests(job.cancel))
            with job.lock:
                attempt["tests"]["extension"] = compared
            job.save()
            if not compared["ok"]:
                return "Có test extension Auto Fill mới đỏ:\n" + "\n".join(compared["new"])
        if codeguard.touches_troly(changes):
            job.log("Chạy bộ test extension trợ lý…")
            compared = verify.compare_extension(before["troly"], verify.extension_tests(job.cancel, TROLY))
            with job.lock:
                attempt["tests"]["troly"] = compared
            job.save()
            if not compared["ok"]:
                return "Có test extension trợ lý mới đỏ:\n" + "\n".join(compared["new"])

        prefix = f"{codeguard.BE_DIR}/"
        changed_tests = [c.rel for c in changes if c.rel.startswith(f"{prefix}tests/unit/") or c.rel.startswith(f"{prefix}tests/integration/")]
        test_files = verify.find_test_files(self.folder, [*(output.get("testFiles") or []), *changed_tests])
        test_files = [f for f in test_files if not f.startswith("tests/handfree/")]
        if not any(Path(f).name.startswith(f"test_{self.folder}") for f in test_files):
            return f"Chưa có test của pipeline: phải có auto-fill-hcc-backend/tests/unit/test_{self.folder}.py (CLAUDE.md)."
        pipeline = verify.pipeline_tests(test_files, job.cancel)
        with job.lock:
            attempt["tests"]["pipeline"] = {k: v for k, v in pipeline.items() if k != "output"}
        job.save()
        if not pipeline["ok"]:
            return f"Test của pipeline đỏ ({pipeline['summary']}):\n{pipeline['output']}"

        job.log("Chạy toàn bộ test backend để so với mốc…")
        compared = verify.compare(before["backend"], verify.full_tests(job.cancel))
        with job.lock:
            attempt["tests"]["full"] = compared
        job.save()
        if compared["broken"]:
            return f"Bộ test sập, không có số để so:\n{compared['tail']}"
        if not compared["ok"]:
            return "Có test backend mới đỏ so với trước:\n" + "\n".join(compared["new"])

        if self.troly or any(c.rel.startswith(f"{prefix}tests/handfree/") for c in changes):
            job.log("Chạy bộ test trợ lý (tests/handfree)…")
            hf_before = before.get("handfree") or verify.handfree_baseline(job.cancel)
            compared = verify.compare(hf_before, verify.handfree_tests(job.cancel))
            with job.lock:
                attempt["tests"]["handfree"] = compared
            job.save()
            if compared["broken"]:
                return f"Bộ test handfree sập:\n{compared['tail']}"
            if not compared["ok"]:
                return "Có test handfree (trợ lý) mới đỏ so với trước:\n" + "\n".join(compared["new"])

        if codeguard.touches_backend_app(changes) or job.data.get("stackDirty"):
            self._stage("deploy", "Build lại backend bằng compose.prod.yml…")
            job.update(stackDirty=True)
            deployed = verify.deploy(job.cancel)
            with job.lock:
                attempt["deploy"] = deployed
            job.save()
            if not deployed["ok"]:
                return f"Build hoặc healthz lỗi ở bước {deployed.get('step')}: {deployed.get('output', deployed.get('health', ''))[-800:]}"

        problem, fields = self._smoke(attempt)
        if problem:
            return problem
        leaks = codeguard.leaked_terms(patch, private_terms(fields))
        if leaks:
            return (f"Patch chứa dữ liệu thật của file mẫu ({len(leaks)} chuỗi: {', '.join(leaks)}). "
                    "Hãy thay bằng dữ liệu bịa cùng cấu trúc trong code, prompt và test.")
        return None

    def _smoke(self, attempt: dict) -> tuple[str | None, list[dict]]:
        """Chạy thủ tục mới trên file mẫu qua /api/v2/process như extension. Tạo được req trong Mongo local, dùng req đó kiểm thử
        tiếp trên cổng thật bằng luồng Agent tự sửa. Trả (lỗi, field backend trả) — field chỉ để quét patch, không ghi job."""
        samples = [i for i in self.job.data["inputs"] if i["group"] == "samples" and not i.get("source")]
        if not samples:
            return None, []
        self._stage("smoke", f"Chạy thử thủ tục trên {len(samples)} file mẫu qua backend…")
        case = {
            "procedure": self.proc["key"],
            "options": {},
            "storedFiles": [{"name": s["name"], "type": _mime(s["name"]), "path": s["path"], "role": "doc"} for s in samples],
        }
        out_dir = self.job.dir / "smoke" / f"lan{attempt['n']}"
        out_dir.mkdir(parents=True, exist_ok=True)
        try:
            token = replay.login(self.credentials["username"], self.credentials["password"])["accessToken"]
        except replay.LoginError as reason:
            raise JobError(str(reason)) from reason
        run = replay.run_once(case, 1, f"dev:{attempt['n']}", token, out_dir)
        response = run.get("response") or {}
        (out_dir / "response.json").write_text(json.dumps(response, ensure_ascii=False, indent=2), encoding="utf-8")
        fields = response.get("fields") if isinstance(response.get("fields"), list) else []
        filled = [f for f in fields if _filled(f.get("value"))]
        smoke = {
            "status": run.get("status"), "ms": run.get("ms"), "requestId": run.get("requestId"), "error": run.get("error"),
            "total": len(fields), "filled": len(filled), "errors": response.get("errors") or [],
            "fields": [{"name": f.get("name"), "value": str(f.get("value"))[:200]} for f in filled][:300],
        }
        with self.job.lock:
            attempt["smoke"] = smoke
        self.job.save()
        self.job.log(f"Chạy thử: {run.get('status')}, {len(filled)}/{len(fields)} ô có giá trị" + (f" · {run['error']}" if run.get("error") else ""))
        if run.get("status") == "error":
            return f"Chạy thử thủ tục trên file mẫu lỗi: {run.get('error')}", fields
        if not filled:
            detail = json.dumps(response.get("errors") or [], ensure_ascii=False)[:1500]
            return ("Chạy thử trên file mẫu qua /api/v2/process ra 0 ô có giá trị, pipeline chưa trích được gì. "
                    f"Lỗi backend ghi nhận: {detail}. Text OCR của lượt này ở {out_dir.relative_to(REPO).as_posix()}/run1_ocr.txt."), fields
        return None, fields

    def _accept_dev(self, attempt: dict) -> None:
        job = self.job
        changes, _ = self.guard.changes(self.touched, True)
        records = self.guard.keep_preimages(changes)
        (job.dir / "fix.patch").write_text(attempt["patch"], encoding="utf-8")
        output = attempt.get("output") or {}
        self.touched = []
        with job.lock:
            job.data["fix"] = {"files": records, "patch": attempt["patch"], "summary": output.get("summary"), "reverted": False}
            job.data["touched"] = []
            job.data["stackDirty"] = False
        job.save()
        smoke = attempt.get("smoke") or {}
        reason = output.get("summary") or ""
        if smoke.get("requestId"):
            reason += f" Chạy thử file mẫu ra {smoke.get('filled')}/{smoke.get('total')} ô có giá trị (req {smoke['requestId']})."
        if output.get("assumptions"):
            reason += f" Có {len(output['assumptions'])} chỗ agent tự suy ra, cần kiểm trước khi dùng."
        self._finish("built", reason.strip())
