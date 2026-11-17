"""Khu làm việc: clone riêng, đặt đúng tag release mới nhất, dọn sạch, lưu phần ca trước để lại, trỏ extension sang backend thử."""
import json
import subprocess

import pytest

import publish
import verify
import workspace
from codeguard import Change


def git(cwd, *args) -> str:
    return subprocess.run(["git", "-c", "core.autocrlf=false", *args], cwd=cwd, capture_output=True, text=True,
                          check=True).stdout.strip()


def make_repo(path, files: dict, tags: list[str]):
    path.mkdir(parents=True)
    git(path, "init", "-q", "-b", "main")
    git(path, "config", "user.name", "t")
    git(path, "config", "user.email", "t@example.com")
    for index, tag in enumerate(tags):
        for rel, text in files.items():
            target = path / rel
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(text.replace("{n}", str(index)), encoding="utf-8", newline="")
        git(path, "add", "-A")
        git(path, "commit", "-q", "-m", f"ban {tag}")
        git(path, "tag", tag)
    return path


@pytest.fixture
def ws(tmp_path, monkeypatch):
    src = tmp_path / "src"
    be = make_repo(src / "be", {"app/a.py": "x = {n}\n"}, ["v2026.11.9.1", "v2026.11.16.2", "v2026.11.1"])
    ext = make_repo(src / "ext", {
        "api/config.js": 'const BACKEND_URL = "https://trolyhoso.example";     // ghi chú\nconst B = {n};\n',
        "manifest.json": json.dumps({"name": "x", "host_permissions": ["https://trolyhoso.example/*"]}),
    }, ["autofill-v1.28.8", "autofill-v1.28.10"])
    troly = make_repo(src / "troly", {"sidebar.js": "// {n}\n"}, ["handfree-v1.9.9"])
    components = [
        {"dir": "auto-fill-hcc-backend", "url": str(be), "tags": "v20*", "ref": "", "base": "main"},
        {"dir": "auto-fill-hcc-extension", "url": str(ext), "tags": "autofill-v*", "ref": "", "base": "main"},
        {"dir": "tro-ly-nguoi-dan-extension-main", "url": str(troly), "tags": "handfree-v*", "ref": "", "base": "main"},
    ]
    root = tmp_path / "ws"
    runs = tmp_path / "runs"
    monkeypatch.setattr(workspace, "COMPONENTS", components)
    monkeypatch.setattr(workspace, "WORKSPACE", root)
    monkeypatch.setattr(workspace, "_OWNER", root / ".autotest-job")
    monkeypatch.setattr(workspace, "RUNS", runs)
    monkeypatch.setattr(workspace, "USE_WORKSPACE", True)
    monkeypatch.setattr(workspace, "EXTENSION_BACKEND", "http://localhost:12015")
    return {"root": root, "runs": runs, "src": src, "components": components}


def test_dat_ve_tag_release_moi_nhat_va_tro_extension_sang_backend_thu(ws):
    logs = []
    info = workspace.prepare("at_1", logs.append)
    root = ws["root"]
    assert info["auto-fill-hcc-backend"]["ref"] == "v2026.11.16.2"  # so theo số phiên bản, không theo chữ
    assert (root / "auto-fill-hcc-backend/app/a.py").read_text(encoding="utf-8") == "x = 1\n"
    assert info["auto-fill-hcc-extension"]["ref"] == "autofill-v1.28.10"
    assert info["tro-ly-nguoi-dan-extension-main"]["commit"] == git(ws["src"] / "troly", "rev-parse", "HEAD")
    config = (root / "auto-fill-hcc-extension/api/config.js").read_text(encoding="utf-8")
    assert config.startswith('const BACKEND_URL = "http://localhost:12015";')
    hosts = json.loads((root / "auto-fill-hcc-extension/manifest.json").read_text(encoding="utf-8"))["host_permissions"]
    assert "http://localhost:12015/*" in hosts and "ws://localhost:12015/*" in hosts
    assert workspace.owner() == "at_1"
    assert (root / "auto-test-hcc/runs").is_dir()


def test_ca_sau_don_sach_va_luu_phan_ca_truoc_de_lai(ws):
    workspace.prepare("at_1", lambda _: None)
    root = ws["root"]
    (ws["runs"] / "at_1").mkdir(parents=True)
    (root / "auto-fill-hcc-backend/app/a.py").write_text("x = 99\n", encoding="utf-8")
    (root / "auto-fill-hcc-backend/app/moi.py").write_text("moi = 1\n", encoding="utf-8")
    (root / "auto-test-hcc/runs/at_1/case").mkdir(parents=True)  # chứng cứ (giấy tờ) của ca trước

    workspace.prepare("at_2", lambda _: None)

    left = (ws["runs"] / "at_1/workspace-left.patch").read_text(encoding="utf-8")
    assert "x = 99" in left and "moi.py" in left
    assert "BACKEND_URL" not in left  # 2 file trỏ backend thử không tính là phần để lại
    assert (root / "auto-fill-hcc-backend/app/a.py").read_text(encoding="utf-8") == "x = 1\n"
    assert not (root / "auto-fill-hcc-backend/app/moi.py").exists()
    assert not (root / "auto-test-hcc/runs/at_1").exists()
    assert workspace.owner() == "at_2"


def test_ref_ep_trong_cau_hinh_thang_tag(ws, monkeypatch):
    ws["components"][0]["ref"] = "v2026.11.1"
    info = workspace.prepare("at_1", lambda _: None)
    assert info["auto-fill-hcc-backend"]["ref"] == "v2026.11.1"
    assert (ws["root"] / "auto-fill-hcc-backend/app/a.py").read_text(encoding="utf-8") == "x = 2\n"


def test_khong_co_tag_thi_bao_ro(ws):
    ws["components"][2]["tags"] = "khong-co-*"
    with pytest.raises(workspace.WorkspaceError, match="không có tag release"):
        workspace.prepare("at_1", lambda _: None)


def test_khoa_baseline_theo_commit_khong_theo_mtime(ws):
    workspace.prepare("at_1", lambda _: None)
    be = ws["root"] / "auto-fill-hcc-backend"
    key = verify.tree_key(be, ("app",))
    (be / "app/a.py").touch()
    assert verify.tree_key(be, ("app",)) == key
    (be / "app/a.py").write_text("x = 7\n", encoding="utf-8")
    assert verify.tree_key(be, ("app",)) != key


def test_push_moi_repo_mot_nhanh_dung_tren_tag(ws, monkeypatch, tmp_path):
    info = workspace.prepare("at_1", lambda _: None)
    root = ws["root"]
    monkeypatch.setattr(publish, "WORKSPACE", root)
    monkeypatch.setattr(publish, "COMPONENTS", ws["components"])
    monkeypatch.setattr(publish, "USE_WORKSPACE", True)
    monkeypatch.setattr(publish, "WORKSPACE_PUSH", True)
    (root / "auto-fill-hcc-backend/app/a.py").write_text("x = 5\n", encoding="utf-8")
    changes = [Change("auto-fill-hcc-backend/app/a.py", b"x = 1\n", b"x = 5\n")]
    pushes = publish.push_components("at_1", tmp_path, changes, "agent: sửa\n", info)

    assert len(pushes) == 1 and not pushes[0].get("error")
    item = pushes[0]
    assert item["component"] == "auto-fill-hcc-backend" and item["branch"] == "agent/at_1" and item["drift"] == []
    src = ws["src"] / "be"
    assert git(src, "show", "agent/at_1:app/a.py") == "x = 5"
    assert git(src, "rev-parse", "agent/at_1^") == info["auto-fill-hcc-backend"]["commit"]  # dựng trên tag production
    assert git(src, "rev-parse", "main") == git(src, "rev-parse", "v2026.11.1")  # main không đổi


def test_link_mo_pr():
    assert publish.compare_url("https://github.com/dev-f19/auto-fill-hcc-backend.git", "main", "agent/at_1") == (
        "https://github.com/dev-f19/auto-fill-hcc-backend/compare/main...agent%2Fat_1?expand=1")
    assert publish.compare_url("git@github.com:dev-f19/x.git", "main", "agent/a").startswith("https://github.com/dev-f19/x/")
    assert publish.compare_url("C:/repo", "main", "agent/a") is None


def test_so_ca_hoi_quy_chi_tinh_ca_dang_dat_ma_nay_truot():
    before = {"results": {"a": {"ok": True}, "b": {"ok": False}, "c": {"ok": True}}, "total": 3}
    after = {"results": {"a": {"ok": False, "error": "x"}, "b": {"ok": False}, "c": {"ok": True}, "d": {"ok": True}}, "total": 4}
    compared = verify.compare_regression(before, after)
    assert compared["new"] == ["a"] and not compared["ok"] and compared["errors"] == {"a": "x"}
    assert compared["fixed"] == ["d"] and compared["passed"] == 2
    assert verify.compare_regression(before, {"results": {}, "broken": True})["ok"] is False
