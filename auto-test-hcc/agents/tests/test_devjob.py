"""Job "Thêm thủ tục mới" với agent, bộ test và backend giả. Cái được kiểm là luồng và các chốt chặn: link kê khai, hoàn tác
sạch (kể cả file agent tạo mới), trả lỗi lại cho agent, phạm vi sửa, dữ liệu thật của file mẫu."""
import io
import json
from pathlib import Path

import openpyxl
import pytest
from openpyxl.comments import Comment

import claude_runner
import codeguard
import devjob
import orchestrator
import replay
import roles
import verify
from claude_runner import AgentResult
from devjob import DevOrchestrator, InputError
from orchestrator import JobError

KEY = "dang-ky-thu-tuc-moi"
FOLDER = "dang_ky_thu_tuc_moi"
LINKS = [{"key": "ket-hon", "code": "1.000894", "label": "Thủ tục đăng ký kết hôn",
          "url": "https://dichvucong.gov.vn/thu-tuc-hanh-chinh/abc", "needsAgencySelect": True, "autoConfirm": True}]
PROC = {"key": KEY, "code": "1.099999", "label": "Đăng ký thủ tục mới thử", "url": "https://dichvucong.gov.vn/thu-tuc-hanh-chinh/xyz",
        "newLink": True, "needsAgencySelect": True, "provinceOnlyAgency": False, "selectSo": True, "autoConfirm": True, "linkNotes": ""}
SMOKE_OK = {"status": "ok", "ms": 900, "requestId": "req_smoke1",
            "response": {"fields": [{"name": "ChuHo_HoTen", "value": "LÊ VĂN AN"}, {"name": "SoDinhDanh", "value": "001090012345"}]}}
SMOKE_EMPTY = {"status": "ok", "ms": 900, "requestId": "req_smoke0", "response": {"fields": [{"name": "ChuHo_HoTen", "value": ""}]}}


class World:
    """Repo giả + agent giả. ``plans`` là danh sách việc agent làm ở mỗi lượt (lượt đầu, rồi mỗi lần bị trả lỗi)."""

    def __init__(self, repo: Path):
        self.repo = repo
        self.be = repo / "auto-fill-hcc-backend"
        self.calls: list[str] = []
        self.plans = [self.write_pipeline]
        self.smokes = [SMOKE_OK]
        self.pipeline_ok = [True]
        self.full_bad: list[list[str]] = []
        self.deploys = 0
        self.prompts: list[str] = []
        self.on_agent = None
        self.key = KEY

    # việc agent làm
    def write(self, rel: str, text: str) -> str:
        path = self.repo / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
        return str(path)

    def write_pipeline(self) -> list[str]:
        return [
            self.write(f"auto-fill-hcc-backend/app/pipelines/{FOLDER}/__init__.py", '"""Pipeline thủ tục mới."""\n'),
            self.write(f"auto-fill-hcc-backend/tests/unit/test_{FOLDER}.py", "def test_mapper():\n    assert True\n"),
            self.write("auto-fill-hcc-backend/app/procedures/registry.py", "PROCEDURES = ['ket-hon', 'dang-ky-thu-tuc-moi']\n"),
        ]

    def run_agent(self, *, system, prompt, schema, can_edit=False, touched=None, resume=None, write=False, edit_troly=False, **_):
        assert schema is roles.DEV_SCHEMA and can_edit and write
        self.calls.append("agent-resume" if resume else "agent")
        self.prompts.append(prompt)
        self.edit_troly = edit_troly
        if self.on_agent:
            self.on_agent()
        plan = self.plans.pop(0) if self.plans else (lambda: [])
        touched.extend(plan())
        output = {"summary": "đã làm pipeline", "pipelineFolder": f"auto-fill-hcc-backend/app/pipelines/{FOLDER}",
                  "changedFiles": [], "testFiles": [f"auto-fill-hcc-backend/tests/unit/test_{FOLDER}.py"],
                  "assumptions": ["Ô X suy theo thủ tục kết hôn"], "questions": []}
        return AgentResult(output=output, session_id="sess", cost=0.5, turns=3)

    # hệ thống giả
    def pipeline_tests(self, files, cancel):
        self.calls.append("pipeline-tests")
        ok = self.pipeline_ok.pop(0) if self.pipeline_ok else True
        return {"ok": ok, "files": files, "summary": "1 passed" if ok else "1 failed", "output": "" if ok else "AssertionError"}

    def full_tests(self, cancel):
        self.calls.append("full-tests")
        bad = self.full_bad.pop(0) if self.full_bad else []
        return {"bad": bad, "failed": len(bad), "passed": 10, "skipped": 0, "errors": 0}

    def deploy(self, cancel):
        self.deploys += 1
        self.calls.append("deploy")
        return {"ok": True, "ps": "app Up", "health": '{"ok":true}'}

    def run_once(self, case, number, tag, token, out_dir):
        assert token == "tok" and case["procedure"] == self.key
        assert all((self.repo / f["path"]).is_file() for f in case["storedFiles"])
        self.calls.append("smoke")
        return dict(self.smokes.pop(0) if len(self.smokes) > 1 else self.smokes[0], n=number)

    def links(self) -> list[dict]:
        return json.loads((self.be / "app/procedures/data/ke_khai_links.json").read_text(encoding="utf-8"))["links"]


@pytest.fixture
def world(tmp_path, monkeypatch):
    repo = tmp_path / "repo"
    be = repo / "auto-fill-hcc-backend"
    (be / "app/procedures/data").mkdir(parents=True)
    (be / "app/pipelines").mkdir()
    (be / "tests/unit").mkdir(parents=True)
    (be / "app/procedures/registry.py").write_text("PROCEDURES = ['ket-hon']\n", encoding="utf-8")
    links = be / "app/procedures/data/ke_khai_links.json"
    links.write_bytes(json.dumps({"links": LINKS}, ensure_ascii=False, indent=2).encode())
    (repo / "auto-fill-hcc-extension/content").mkdir(parents=True)
    (repo / "auto-fill-hcc-extension/content/fill.js").write_text("const a = 1;\n", encoding="utf-8")
    (repo / "tro-ly-nguoi-dan-extension-main").mkdir()
    (repo / "tro-ly-nguoi-dan-extension-main/sidebar.js").write_text("const b = 1;\n", encoding="utf-8")
    runs = repo / "auto-test-hcc/runs"
    for module in (codeguard, devjob):
        monkeypatch.setattr(module, "REPO", repo)
    monkeypatch.setattr(devjob, "BE", be)
    monkeypatch.setattr(devjob, "LINKS", links)
    monkeypatch.setattr(devjob, "TROLY", repo / "tro-ly-nguoi-dan-extension-main")
    monkeypatch.setattr(orchestrator, "RUNS", runs)
    w = World(repo)
    monkeypatch.setattr(claude_runner, "run_agent", w.run_agent)
    monkeypatch.setattr(verify, "baseline", lambda cancel: {"bad": [], "failed": 0, "passed": 10, "skipped": 0, "errors": 0})
    monkeypatch.setattr(verify, "extension_baseline", lambda cancel, root=None: {"total": 5, "failed": []})
    monkeypatch.setattr(verify, "handfree_baseline", lambda cancel: {"bad": [], "failed": 0, "passed": 5, "skipped": 0, "errors": 0})
    monkeypatch.setattr(verify, "extension_tests", lambda cancel, root=None: (w.calls.append(f"ext-tests:{Path(str(root)).name if root else 'autofill'}"), {"total": 5, "failed": []})[1])
    monkeypatch.setattr(verify, "handfree_tests", lambda cancel: (w.calls.append("handfree-tests"), {"bad": [], "failed": 0, "passed": 5, "skipped": 0, "errors": 0})[1])
    monkeypatch.setattr(verify, "pipeline_tests", w.pipeline_tests)
    monkeypatch.setattr(verify, "full_tests", w.full_tests)
    monkeypatch.setattr(verify, "deploy", w.deploy)
    monkeypatch.setattr(verify, "find_test_files", lambda folder, extra: sorted(
        p.relative_to(be).as_posix() for p in (be / "tests/unit").glob(f"test_{folder}*.py")))
    monkeypatch.setattr(replay, "login", lambda u, p: {"accessToken": "tok", "user": {"username": u}})
    monkeypatch.setattr(replay, "run_once", w.run_once)
    return w


def start(world, proc=None, files=None, troly=False, notes=""):
    job = devjob.create_job(
        procedure={**PROC, **(proc or {})}, notes=notes, created_by="t",
        settings={"troLy": troly, "replayAccount": "u"},
        files=files if files is not None else [("samples", "giay-de-nghi.pdf", b"%PDF-1.4 mau"), ("attach", "anh-xa.png", b"\x89PNG")],
        warnings=[],
    )
    return job, DevOrchestrator(job, {"username": "u", "password": "mat-khau"})


# ---- link kê khai ------------------------------------------------------------------------------------------------

def test_entry_dung_thu_tu_khoa_va_chi_ghi_co_dang_bat():
    entry = devjob.build_entry(PROC)
    assert list(entry) == ["key", "code", "label", "url", "needsAgencySelect", "selectSo", "autoConfirm"]
    assert "provinceOnlyAgency" not in entry
    assert "code" not in devjob.build_entry({**PROC, "code": ""})


def test_them_link_giu_dinh_dang_file(world):
    devjob.add_link(devjob.build_entry(PROC))
    raw = (world.be / "app/procedures/data/ke_khai_links.json").read_bytes()
    assert b"\r\n" not in raw and not raw.endswith(b"\n")
    assert raw.decode() == json.dumps({"links": [*LINKS, devjob.build_entry(PROC)]}, ensure_ascii=False, indent=2)
    with pytest.raises(JobError):
        devjob.add_link(devjob.build_entry(PROC))


@pytest.mark.parametrize("proc, part", [
    ({"key": "Dang Ky"}, "chữ thường"),
    ({"key": "ket-hon"}, "đã có"),
    ({"newLink": False}, "Không có key"),
    ({"url": "http://dichvucong.gov.vn/x"}, "https"),
    ({"url": "https://example.com/x"}, ".gov.vn"),
    ({"code": "1.13831"}, "1.013831"),
])
def test_kiem_tra_thong_tin_thu_tuc(world, proc, part):
    assert any(part in p for p in devjob.validate_procedure({**PROC, **proc}))


def test_dung_link_co_san_khong_doi_url(world):
    assert devjob.validate_procedure({**PROC, "key": "ket-hon", "newLink": False, "url": ""}) == []


def test_tra_key_va_ma(world):
    (world.be / "app/pipelines/ket_hon").mkdir()
    check = devjob.link_check("ket-hon", "1.000894")
    assert check["keyExists"] and check["pipelineExists"] and check["sameCode"] == []
    other = devjob.link_check(KEY, "1.000894")
    assert not other["keyExists"] and other["keyValid"] and other["sameCode"][0]["key"] == "ket-hon"


# ---- tài liệu đầu vào --------------------------------------------------------------------------------------------

def test_excel_thanh_bang_chu_co_o_gop_ghi_chu_va_anh(tmp_path):
    book = openpyxl.Workbook()
    sheet = book.active
    sheet.title = "Trang 1"
    sheet.append(["Nhãn trên cổng", "Tên ô", "Nguồn"])
    sheet.append(["Họ tên chủ hộ", "ChuHo_HoTen", "Giấy đề nghị | mục 1"])
    sheet.append(["Địa chỉ", "ChuHo_DiaChi", None])
    sheet.merge_cells("C3:C4")
    sheet["C3"] = "Giấy đề nghị\nmục 2"
    sheet["A4"] = "Nơi ở"
    sheet["B2"].comment = Comment("ô bắt buộc", "t")
    path = tmp_path / "mapping.xlsx"
    book.save(path)
    text, images = devjob.excel_to_markdown(path, tmp_path / "img")
    assert "## Sheet: Trang 1" in text
    assert "| Họ tên chủ hộ | ChuHo_HoTen | Giấy đề nghị \\| mục 1 |" in text
    assert text.count("Giấy đề nghị<br>mục 2") == 2  # ô gộp điền lại cho cả hai dòng
    assert "Ô B2: ô bắt buộc" in text and images == []


def test_excel_hong_bao_loi_ro(tmp_path):
    path = tmp_path / "hong.xlsx"
    path.write_bytes(b"khong phai excel")
    with pytest.raises(InputError, match="Không đọc được file Excel"):
        devjob.excel_to_markdown(path, tmp_path)


def test_docx_va_csv_thanh_chu(tmp_path):
    import docx

    document = docx.Document()
    document.add_paragraph("GIẤY ĐỀ NGHỊ")
    table = document.add_table(rows=1, cols=2)
    table.rows[0].cells[0].text, table.rows[0].cells[1].text = "Họ tên", "............"
    document.save(tmp_path / "mau.docx")
    text = devjob.docx_to_text(tmp_path / "mau.docx")
    assert "GIẤY ĐỀ NGHỊ" in text and "Họ tên | ............" in text
    (tmp_path / "m.csv").write_bytes("Tên ô,Nguồn\nHoTen,CCCD\n".encode("utf-8-sig"))
    assert "| HoTen | CCCD |" in devjob.csv_to_markdown(tmp_path / "m.csv")


@pytest.mark.parametrize("group, name, size, part", [
    ("mapping", "mapping.xls", 10, ".xlsx"),
    ("attach", "anh.pdf", 10, "không nhận"),
    ("samples", "mau.exe", 10, "không nhận"),
    ("samples", "mau.pdf", 0, "rỗng"),
    ("samples", "mau.pdf", (devjob.DEV_FILE_MAX_MB + 1) * 1024 * 1024, "quá"),
    ("khac", "a.pdf", 10, "Nhóm"),
])
def test_chan_tep_sai(group, name, size, part):
    with pytest.raises(InputError, match=part):
        devjob.check_upload(group, name, size)


def test_luu_tep_trung_ten_va_ten_nguy_hiem(world, tmp_path):
    saved = devjob.save_inputs(world.repo / "auto-test-hcc/runs/x", [
        ("attach", "image.png", b"1"), ("attach", "image.png", b"2"), ("samples", "..\\..\\evil.pdf", b"3"),
    ])
    assert [s["name"] for s in saved] == ["image.png", "image (2).png", "evil.pdf"]
    assert all(s["path"].startswith("auto-test-hcc/runs/x/inputs/") for s in saved)


def test_dia_chi_khong_co_so_khong_coi_la_du_lieu_ca_nhan():
    terms = devjob.private_terms([
        {"name": "ChuHo_HoTen", "value": "Lê Văn An"},
        {"name": "ChuHo_SoDinhDanh", "value": "001090012345"},
        {"name": "TruSo_DiaChi", "value": "Phường Nam Nha Trang"},
        {"name": "ChuHo_DiaChi", "value": "Số 12, ngõ 3, đường Lê Lợi"},
    ])
    assert terms == {"lê văn an", "001090012345", "số 12, ngõ 3, đường lê lợi"}


# ---- luồng job ---------------------------------------------------------------------------------------------------

def test_lam_xong_thu_tuc_giu_ban_sua(world):
    job, orch = start(world)
    orch.run()
    data = job.data
    assert data["outcome"] == "built", data["error"]
    assert world.links()[-1] == devjob.build_entry(PROC)
    assert data["link"] == {"added": True, "entry": devjob.build_entry(PROC)}
    order = ["agent", "pipeline-tests", "full-tests", "deploy", "smoke"]
    assert [c for c in world.calls if c in order] == order
    files = {f["path"] for f in data["fix"]["files"]}
    assert "auto-fill-hcc-backend/app/procedures/data/ke_khai_links.json" in files
    assert f"auto-fill-hcc-backend/app/pipelines/{FOLDER}/__init__.py" in files
    smoke = data["attempts"][0]["smoke"]
    assert smoke["requestId"] == "req_smoke1" and smoke["filled"] == 2
    assert "req_smoke1" in data["report"]["reason"] and "1 chỗ agent tự suy ra" in data["report"]["reason"]
    assert not (job.dir / "snapshot").exists() and not data["stackDirty"]


def test_prompt_chi_duong_dan_tai_lieu_va_ban_chu_excel(world, tmp_path):
    book = openpyxl.Workbook()
    book.active.append(["Tên ô", "Nguồn"])
    buf = io.BytesIO()
    book.save(buf)
    job, orch = start(world, files=[("mapping", "Mapping thu tuc.xlsx", buf.getvalue()), ("samples", "mau.pdf", b"%PDF")],
                      notes="ở tro-ly có phần lựa chọn này")
    orch.run()
    prompt = world.prompts[0]
    assert "Mapping thu tuc.xlsx.md (bản chữ của Mapping thu tuc.xlsx)" in prompt
    assert f"auto-fill-hcc-backend/app/pipelines/{FOLDER}/" in prompt
    assert "<user_notes>\nở tro-ly có phần lựa chọn này\n</user_notes>" in prompt
    assert (world.repo / job.data["inputs"][-1]["path"]).read_text(encoding="utf-8").startswith("# Mapping thu tuc.xlsx")


def test_hoan_tac_sau_khi_giu_go_ca_link_lan_file_moi(world):
    job, orch = start(world)
    orch.run()
    orchestrator.revert_fix(job)
    assert [l["key"] for l in world.links()] == ["ket-hon"]
    assert not (world.be / f"app/pipelines/{FOLDER}/__init__.py").exists()
    assert (world.be / "app/procedures/registry.py").read_text(encoding="utf-8") == "PROCEDURES = ['ket-hon']\n"
    assert job.data["fix"]["reverted"] and world.deploys == 2


def test_chay_thu_ra_0_o_thi_tra_lai_agent(world):
    world.smokes = [SMOKE_EMPTY, SMOKE_OK]
    world.plans = [world.write_pipeline, lambda: [world.write(f"auto-fill-hcc-backend/app/pipelines/{FOLDER}/mapper.py", "x = 1\n")]]
    job, orch = start(world)
    orch.run()
    assert job.data["outcome"] == "built"
    assert world.calls.count("agent") == 1 and world.calls.count("agent-resume") == 1
    assert "0 ô có giá trị" in world.prompts[1] and "Hệ thống kiểm tra báo lỗi" in world.prompts[1]
    assert [a["n"] for a in job.data["attempts"]] == [1, 2] and job.data["attempts"][0]["problem"]


def test_thieu_test_pipeline_thi_tra_lai_agent(world):
    def no_test():
        return [world.write(f"auto-fill-hcc-backend/app/pipelines/{FOLDER}/__init__.py", "")]

    world.plans = [no_test, lambda: [world.write(f"auto-fill-hcc-backend/tests/unit/test_{FOLDER}.py", "def test(): pass\n")]]
    job, orch = start(world)
    orch.run()
    assert job.data["outcome"] == "built"
    assert f"tests/unit/test_{FOLDER}.py" in job.data["attempts"][0]["problem"]


def test_sai_ten_thu_muc_pipeline_thi_tra_lai_agent(world):
    world.plans = [lambda: [world.write("auto-fill-hcc-backend/app/pipelines/ten_khac/__init__.py", "")], world.write_pipeline]
    job, orch = start(world)
    orch.run()
    assert "đổi - thành _" in job.data["attempts"][0]["problem"] and job.data["outcome"] == "built"


def test_khong_dat_sau_so_lan_cho_phep_thi_hoan_tac_sach(world, monkeypatch):
    monkeypatch.setattr(devjob, "DEV_MAX_REPAIRS", 1)
    world.pipeline_ok = [False, False]
    job, orch = start(world)
    orch.run()
    assert job.data["outcome"] == "dev_failed" and job.data["status"] == "done"
    assert [l["key"] for l in world.links()] == ["ket-hon"]
    assert not (world.be / f"app/pipelines/{FOLDER}/__init__.py").exists()
    assert (world.be / "app/procedures/registry.py").read_text(encoding="utf-8") == "PROCEDURES = ['ket-hon']\n"
    assert job.data["fix"] is None and world.deploys == 0


def test_build_roi_truot_thi_build_lai_ve_code_cu(world, monkeypatch):
    monkeypatch.setattr(devjob, "DEV_MAX_REPAIRS", 0)
    world.smokes = [SMOKE_EMPTY]
    job, orch = start(world)
    orch.run()
    assert job.data["outcome"] == "dev_failed"
    assert world.deploys == 2 and not job.data["stackDirty"]  # build bản mới để chạy thử, rồi build lại sau hoàn tác


def test_du_lieu_that_cua_file_mau_lot_vao_code_thi_tra_lai(world):
    def leaky():
        return [*world.write_pipeline(), world.write(f"auto-fill-hcc-backend/tests/unit/test_{FOLDER}.py",
                                                     "def test():\n    assert map_id('001090012345')\n")]

    world.plans = [leaky, lambda: [world.write(f"auto-fill-hcc-backend/tests/unit/test_{FOLDER}.py", "def test():\n    assert map_id('012345678901')\n")]]
    job, orch = start(world)
    orch.run()
    assert "dữ liệu thật" in job.data["attempts"][0]["problem"] and "001090012345" in job.data["attempts"][0]["problem"]
    assert job.data["outcome"] == "built"


def test_sua_ngoai_pham_vi_thi_dung_va_hoan_tac(world):
    def outside():
        return [*world.write_pipeline(), world.write("auto-fill-hcc-backend/compose.prod.yml", "x\n")]

    world.plans = [outside]
    job, orch = start(world)
    orch.run()
    assert job.data["status"] == "failed" and "ngoài phạm vi" in job.data["error"]
    assert [l["key"] for l in world.links()] == ["ket-hon"]
    assert not (world.be / f"app/pipelines/{FOLDER}/__init__.py").exists()


def test_dung_giua_chung_thi_hoan_tac(world):
    job, orch = start(world)
    world.on_agent = job.cancel.set
    orch.run()
    assert job.data["status"] == "stopped"
    assert [l["key"] for l in world.links()] == ["ket-hon"] and not (world.be / f"app/pipelines/{FOLDER}").exists()


def test_dua_len_tro_ly_thi_chay_ca_test_tro_ly_va_hoan_tac_duoc_extension_tro_ly(world):
    def with_troly():
        return [*world.write_pipeline(), world.write("tro-ly-nguoi-dan-extension-main/sidebar.js", "const b = 2;\n")]

    world.plans = [with_troly]
    job, orch = start(world, troly=True)
    orch.run()
    assert job.data["outcome"] == "built" and world.edit_troly
    assert "ext-tests:tro-ly-nguoi-dan-extension-main" in world.calls and "handfree-tests" in world.calls
    assert "tro-ly-nguoi-dan-extension-main/sidebar.js" in {f["path"] for f in job.data["fix"]["files"]}
    orchestrator.revert_fix(job)
    assert (world.repo / "tro-ly-nguoi-dan-extension-main/sidebar.js").read_text(encoding="utf-8") == "const b = 1;\n"


def test_khong_dua_len_tro_ly_thi_khong_duoc_sua_extension_tro_ly(world):
    """Ngoài đời lệnh claude đã từ chối ghi; nếu lọt qua thì codeguard dừng job và nêu tên file để người xem (như job sửa lỗi),
    còn phần trong phạm vi vẫn được hoàn tác."""
    def with_troly():
        return [*world.write_pipeline(), world.write("tro-ly-nguoi-dan-extension-main/sidebar.js", "const b = 2;\n")]

    world.plans = [with_troly]
    job, orch = start(world, troly=False)
    orch.run()
    assert job.data["status"] == "failed" and "ngoài phạm vi" in job.data["error"] and "sidebar.js" in job.data["error"]
    assert not world.edit_troly
    assert not (world.be / f"app/pipelines/{FOLDER}").exists() and [l["key"] for l in world.links()] == ["ket-hon"]


def test_dung_link_co_san_thi_khong_them_link(world):
    job, orch = start(world, proc={"key": "ket-hon", "newLink": False})
    world.key = "ket-hon"
    world.plans = [lambda: [world.write("auto-fill-hcc-backend/app/pipelines/ket_hon/__init__.py", ""),
                            world.write("auto-fill-hcc-backend/tests/unit/test_ket_hon.py", "def test(): pass\n")]]
    orch.run()
    assert job.data["outcome"] == "built" and job.data["link"]["added"] is False
    assert len(world.links()) == 1


def test_khong_co_file_mau_thi_bo_qua_chay_thu(world):
    job, orch = start(world, files=[("attach", "anh.png", b"\x89PNG")])
    orch.run()
    assert job.data["outcome"] == "built" and "smoke" not in world.calls
    assert any("không chạy thử" in w for w in job.data["warnings"])


def test_khoi_phuc_sau_khi_dich_vu_tat_giua_chung(world):
    job, orch = start(world, troly=True)
    orch.guard.take()
    touched = world.write_pipeline() + [world.write("tro-ly-nguoi-dan-extension-main/sidebar.js", "const b = 9;\n")]
    job.update(touched=touched, status="running")
    orchestrator.recover_interrupted(job)
    assert not (world.be / f"app/pipelines/{FOLDER}/__init__.py").exists()
    assert (world.repo / "tro-ly-nguoi-dan-extension-main/sidebar.js").read_text(encoding="utf-8") == "const b = 1;\n"
