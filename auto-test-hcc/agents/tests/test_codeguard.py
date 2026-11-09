import pytest

import codeguard
from codeguard import Guard, in_scope, leaked_terms, make_patch, private_terms, to_rel


@pytest.fixture
def tree(tmp_path, monkeypatch):
    repo = tmp_path / "repo"
    be = repo / "auto-fill-hcc-backend"
    ext = repo / "auto-fill-hcc-extension"
    (be / "app").mkdir(parents=True)
    (be / "tests").mkdir()
    (ext / "content/form-snapshot").mkdir(parents=True)
    (ext / "api").mkdir()
    (be / "app/a.py").write_text("x = 1\n", encoding="utf-8")
    (be / "tests/test_a.py").write_text("def test(): pass\n", encoding="utf-8")
    (be / "tests/conftest.py").write_text("", encoding="utf-8")
    (be / "compose.prod.yml").write_text("a: 1\n", encoding="utf-8")
    (ext / "content/fill.js").write_text("const a = 1;\n", encoding="utf-8")
    monkeypatch.setattr(codeguard, "REPO", repo)
    return be


def test_pham_vi(tree):
    assert in_scope(to_rel(str(tree / "app/a.py")))
    assert in_scope(to_rel(str(tree / "tests/test_a.py")))
    assert in_scope(to_rel("auto-fill-hcc-backend/app/a.py"))
    assert not in_scope(to_rel(str(tree / "tests/conftest.py")))
    assert not in_scope(to_rel(str(tree / "compose.prod.yml")))
    assert not in_scope(to_rel(str(tree.parent / "CLAUDE.md")))
    assert not in_scope(to_rel(str(tree / "app/../.env")))


def test_pham_vi_extension(tree):
    ext = tree.parent / "auto-fill-hcc-extension"
    assert in_scope(to_rel(str(ext / "content/fill.js")))
    assert not in_scope(to_rel(str(ext / "content/fill.js")), extension=False)
    assert in_scope(to_rel(str(tree / "app/a.py")), extension=False)


@pytest.mark.parametrize("rel", ["api/config.js", "manifest.json", "content/form-snapshot/read.js", "background/form-snapshot.js"])
def test_cam_sua_cau_hinh_quyen_va_thuoc_do(tree, rel):
    assert not in_scope(to_rel(str(tree.parent / "auto-fill-hcc-extension" / rel)))


def test_chi_chup_va_hoan_tac_duoc_ca_extension(tree, tmp_path):
    target = tree.parent / "auto-fill-hcc-extension/content/fill.js"
    guard = Guard(tmp_path / "job")
    guard.take()
    target.write_text("const a = 2;\n", encoding="utf-8")
    changes, _ = guard.changes([str(target)])
    assert codeguard.touches_extension(changes) and not codeguard.touches_backend(changes)
    guard.restore(changes)
    assert target.read_text(encoding="utf-8") == "const a = 1;\n"


def test_chi_hoan_tac_file_agent_cham(tree, tmp_path):
    guard = Guard(tmp_path / "job")
    guard.take()
    (tree / "app/a.py").write_text("x = 2\n", encoding="utf-8")
    (tree / "app/nguoi_dung_dang_sua.py").write_text("y = 1\n", encoding="utf-8")
    changes, outside = guard.changes([str(tree / "app/a.py")])
    assert [c.rel for c in changes] == ["auto-fill-hcc-backend/app/a.py"] and outside == []
    guard.restore(changes)
    assert (tree / "app/a.py").read_text(encoding="utf-8") == "x = 1\n"
    assert (tree / "app/nguoi_dung_dang_sua.py").exists()


def test_file_moi_bi_xoa_khi_hoan_tac(tree, tmp_path):
    guard = Guard(tmp_path / "job")
    guard.take()
    created = tree / "app/moi.py"
    created.write_text("z = 1\n", encoding="utf-8")
    changes, _ = guard.changes([str(created)])
    assert changes[0].before is None
    guard.restore(changes)
    assert not created.exists()


def test_cham_nhung_khong_doi_thi_khong_tinh(tree, tmp_path):
    guard = Guard(tmp_path / "job")
    guard.take()
    assert guard.changes([str(tree / "app/a.py")]) == ([], [])


def test_ngoai_pham_vi_bi_tach_rieng(tree, tmp_path):
    guard = Guard(tmp_path / "job")
    guard.take()
    target = str(tree / "compose.prod.yml")
    assert guard.changes([target]) == ([], [target])


def test_revert_khong_de_file_da_bi_sua_tiep(tree, tmp_path):
    guard = Guard(tmp_path / "job")
    guard.take()
    (tree / "app/a.py").write_text("x = 2\n", encoding="utf-8")
    (tree / "tests/test_a.py").write_text("def test(): assert 1\n", encoding="utf-8")
    changes, _ = guard.changes([str(tree / "app/a.py"), str(tree / "tests/test_a.py")])
    records = guard.keep_preimages(changes)
    guard.discard_snapshot()
    (tree / "tests/test_a.py").write_text("def test(): assert 2\n", encoding="utf-8")
    reverted, skipped = guard.revert(records)
    assert reverted == ["auto-fill-hcc-backend/app/a.py"] and skipped == ["auto-fill-hcc-backend/tests/test_a.py"]
    assert (tree / "app/a.py").read_text(encoding="utf-8") == "x = 1\n"
    assert "assert 2" in (tree / "tests/test_a.py").read_text(encoding="utf-8")


def test_patch_ghi_ca_file_khong_co_xuong_dong_cuoi(tree, tmp_path):
    guard = Guard(tmp_path / "job")
    guard.take()
    (tree / "app/a.py").write_text("x = 3", encoding="utf-8")
    changes, _ = guard.changes([str(tree / "app/a.py")])
    patch = make_patch(changes)
    assert "-x = 1" in patch and "+x = 3" in patch and patch.endswith("\n")


FIELDS = [
    {"name": "hoTenNguoiYeuCau", "value": "Trần Thị Mẫu"},
    {"name": "soCCCD", "value": "012345678901"},
    {"name": "soDienThoai", "value": "0912 345 678"},
    {"name": "diaChiThuongTru", "value": "Số 1 đường Bịa Đặt, phường Ví Dụ"},
    {"name": "quocTich", "value": "Việt Nam"},
    {"name": "gioiTinh", "value": "Nữ"},
    {"name": "coUyQuyen", "value": True},
]


def test_quet_du_lieu_that():
    terms = private_terms(FIELDS, "req_abc123")
    assert "012345678901" in terms and "0912345678" in terms and "req_abc123" in terms
    assert "trần thị mẫu" in terms
    assert "việt nam" not in terms and "nữ" not in terms


@pytest.mark.parametrize("line", [
    '+    assert ten == "Trần Thị Mẫu"',
    '+    assert ten == "TRẦN THỊ MẪU"',
    '+    so = "012345678901"',
    '+    so = "012 345 678 901"',
    '+    # lỗi từ req_abc123',
    '+    dc = "Số 1 đường Bịa Đặt, phường Ví Dụ"',
])
def test_patch_lo_du_lieu_that_bi_bat(line):
    assert leaked_terms(f"+++ b/app/a.py\n{line}\n", private_terms(FIELDS, "req_abc123"))


def test_dong_bi_xoa_va_du_lieu_bia_khong_tinh():
    patch = '--- a/x\n+++ b/x\n-    ten = "Trần Thị Mẫu"\n+    ten = "Nguyễn Văn Bịa"\n+    so = "000000000000"[:3]\n'
    assert leaked_terms(patch, private_terms(FIELDS, "req_abc123")) == []


def test_hoan_tac_file_moi_don_ca_thu_muc_rong_va_pycache(tree, tmp_path):
    """Thư mục pipeline rỗng còn lại thì job sau tưởng pipeline đã có."""
    guard = Guard(tmp_path / "job")
    guard.take()
    created = tree / "app/pipelines/thu_tuc_moi/process/mapper.py"
    created.parent.mkdir(parents=True)
    created.write_text("x = 1\n", encoding="utf-8")
    (created.parent / "__pycache__").mkdir()
    (created.parent / "__pycache__/mapper.cpython-311.pyc").write_bytes(b"pyc")
    keep = tree / "app/pipelines/da_co"
    keep.mkdir()
    changes, _ = guard.changes([str(created)])
    guard.restore(changes)
    assert not (tree / "app/pipelines/thu_tuc_moi").exists()
    assert keep.is_dir() and (tree / "app").is_dir()  # không đụng thư mục khác, không xoá gốc phạm vi


def test_hoan_tac_khong_xoa_thu_muc_con_file_khac(tree, tmp_path):
    folder = tree / "app/pipelines/chung"
    folder.mkdir(parents=True)
    (folder / "co_san.py").write_text("y = 1\n", encoding="utf-8")
    guard = Guard(tmp_path / "job")
    guard.take()
    (folder / "moi.py").write_text("z = 1\n", encoding="utf-8")
    changes, _ = guard.changes([str(folder / "moi.py")])
    guard.restore(changes)
    assert not (folder / "moi.py").exists() and (folder / "co_san.py").exists()


def test_tro_ly_chi_trong_pham_vi_khi_bat(tree):
    troly = to_rel(str(tree.parent / "tro-ly-nguoi-dan-extension-main/sidebar.js"))
    assert not in_scope(troly) and in_scope(troly, troly=True)
    assert not in_scope(to_rel(str(tree.parent / "tro-ly-nguoi-dan-extension-main/api/config.js")), troly=True)
    assert not in_scope(to_rel(str(tree.parent / "tro-ly-nguoi-dan-extension-main/manifest.json")), troly=True)
