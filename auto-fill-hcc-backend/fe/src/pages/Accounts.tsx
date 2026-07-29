import { useCallback, useEffect, useState } from "react";
import { createUser, deleteUser, listUsers, updateUser } from "../api";
import type { ManagedUser, Role, User } from "../types";
import { fmtDateTime } from "../format";
import TopBar, { type View } from "../components/TopBar";

interface Props {
  user: User;
  onLogout: () => void;
  view: View;
  onNavigate: (v: View) => void;
}

interface FormState {
  id: string | null; // null = tạo mới
  username: string;
  password: string;
  name: string;
  xa: string;
  tinh: string;
  role: Role;
}

const EMPTY_FORM: FormState = {
  id: null,
  username: "",
  password: "",
  name: "",
  xa: "",
  tinh: "",
  role: "user",
};

// Nhãn hiển thị + class badge theo role. commune = "Hành chính công xã" (như user, chỉ khác nhãn).
const ROLE_META: Record<Role, { label: string; cls: string }> = {
  admin: { label: "Quản trị", cls: "role-admin" },
  user: { label: "Người dùng", cls: "role-user" },
  commune: { label: "Hành chính công xã", cls: "role-commune" },
  province: { label: "Hành chính công tỉnh", cls: "role-province" },
};

const PAGE_SIZE = 20;

export default function Accounts({ user, onLogout, view, onNavigate }: Props) {
  const [items, setItems] = useState<ManagedUser[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [form, setForm] = useState<FormState | null>(null);
  const [saving, setSaving] = useState(false);
  const [formError, setFormError] = useState("");

  const load = useCallback(async () => {
    setLoading(true);
    setError("");
    try {
      const res = await listUsers(page, PAGE_SIZE);
      setItems(res.items);
      setTotal(res.total);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Lỗi tải danh sách");
    } finally {
      setLoading(false);
    }
  }, [page]);

  useEffect(() => {
    load();
  }, [load]);

  function openCreate() {
    setFormError("");
    setForm({ ...EMPTY_FORM });
  }

  function openEdit(u: ManagedUser) {
    setFormError("");
    setForm({
      id: u.id,
      username: u.username,
      password: "",
      name: u.name ?? "",
      xa: u.xa ?? "",
      tinh: u.tinh ?? "",
      role: u.role,
    });
  }

  async function submitForm(e: React.FormEvent) {
    e.preventDefault();
    if (!form) return;
    setFormError("");
    setSaving(true);
    try {
      if (form.id === null) {
        await createUser({
          username: form.username.trim(),
          password: form.password,
          name: form.name.trim() || null,
          xa: form.xa.trim() || null,
          tinh: form.tinh.trim() || null,
          role: form.role,
        });
      } else {
        await updateUser(form.id, {
          name: form.name.trim(),
          xa: form.xa.trim(),
          tinh: form.tinh.trim(),
          role: form.role,
          password: form.password || undefined,
        });
      }
      setForm(null);
      await load();
    } catch (err) {
      setFormError(err instanceof Error ? err.message : "Lưu thất bại");
    } finally {
      setSaving(false);
    }
  }

  async function handleDelete(u: ManagedUser) {
    if (u.id === user.id) return;
    if (!window.confirm(`Xóa tài khoản "${u.username}"? Thao tác không thể hoàn tác.`)) return;
    setError("");
    try {
      await deleteUser(u.id);
      // Xóa item cuối của trang (không phải trang 1) → lùi 1 trang cho khỏi trống; còn lại reload.
      if (items.length === 1 && page > 1) setPage((p) => p - 1);
      else await load();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Xóa thất bại");
    }
  }

  const isCreate = form?.id === null;
  const canSubmit =
    form &&
    (isCreate
      ? form.username.trim().length >= 3 && form.password.length >= 8
      : form.password === "" || form.password.length >= 8);

  const totalPages = Math.max(1, Math.ceil(total / PAGE_SIZE));

  return (
    <div className="app">
      <TopBar user={user} view={view} onNavigate={onNavigate} onLogout={onLogout} />

      <div className="stats-head">
        <div>
          <h1 className="page-title">Quản lý tài khoản</h1>
          <p className="muted page-sub">Mỗi tài khoản gắn với một xã/phường</p>
        </div>
        <button className="btn-primary" onClick={openCreate}>
          + Thêm tài khoản
        </button>
      </div>

      {error && <div className="error bar">{error}</div>}

      <div className="table-wrap">
        <table>
          <thead>
            <tr>
              <th>Tài khoản</th>
              <th>Tên</th>
              <th>Xã / Phường</th>
              <th>Tỉnh</th>
              <th className="center">Vai trò</th>
              <th>Đăng nhập gần nhất</th>
              <th className="center">Thao tác</th>
            </tr>
          </thead>
          <tbody>
            {loading && (
              <tr>
                <td colSpan={7} className="center muted">
                  Đang tải…
                </td>
              </tr>
            )}
            {!loading && items.length === 0 && (
              <tr>
                <td colSpan={7} className="center muted">
                  Chưa có tài khoản nào
                </td>
              </tr>
            )}
            {!loading &&
              items.map((u) => (
                <tr key={u.id}>
                  <td className="mono">
                    {u.username}
                    {u.id === user.id && <span className="tag-self">bạn</span>}
                  </td>
                  <td>{u.name || <span className="muted">—</span>}</td>
                  <td>{u.xa || <span className="muted">—</span>}</td>
                  <td>{u.tinh || <span className="muted">—</span>}</td>
                  <td className="center">
                    <span className={`badge ${ROLE_META[u.role]?.cls ?? "role-user"}`}>
                      {ROLE_META[u.role]?.label ?? u.role}
                    </span>
                  </td>
                  <td className="muted">
                    {u.last_login_at ? fmtDateTime(u.last_login_at) : "—"}
                  </td>
                  <td className="center">
                    <div className="row-actions">
                      <button className="ghost sm" onClick={() => openEdit(u)}>
                        Sửa
                      </button>
                      <button
                        className="ghost sm danger"
                        disabled={u.id === user.id}
                        title={u.id === user.id ? "Không thể tự xóa" : "Xóa tài khoản"}
                        onClick={() => handleDelete(u)}
                      >
                        Xóa
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
          </tbody>
        </table>
      </div>

      <div className="pager">
        <span className="muted">
          {total} tài khoản · trang {page}/{totalPages}
        </span>
        <div>
          <button className="ghost" disabled={page <= 1 || loading} onClick={() => setPage((p) => p - 1)}>
            ‹ Trước
          </button>
          <button
            className="ghost"
            disabled={page >= totalPages || loading}
            onClick={() => setPage((p) => p + 1)}
          >
            Sau ›
          </button>
        </div>
      </div>

      {form && (
        <div className="modal-backdrop" onClick={() => !saving && setForm(null)}>
          <form className="modal-card" onClick={(e) => e.stopPropagation()} onSubmit={submitForm}>
            <h2>{isCreate ? "Thêm tài khoản" : `Sửa: ${form.username}`}</h2>

            <label>
              Tên đăng nhập
              <input
                value={form.username}
                disabled={!isCreate}
                autoFocus={isCreate}
                onChange={(e) => setForm({ ...form, username: e.target.value })}
                placeholder="vd: hcctanphong"
              />
            </label>

            <label>
              Mật khẩu {isCreate ? "" : "(để trống nếu không đổi)"}
              <input
                type="password"
                value={form.password}
                autoComplete="new-password"
                onChange={(e) => setForm({ ...form, password: e.target.value })}
                placeholder={isCreate ? "≥ 8 ký tự" : "••••••••"}
              />
            </label>

            <label>
              Tên hiển thị
              <input
                value={form.name}
                onChange={(e) => setForm({ ...form, name: e.target.value })}
                placeholder="vd: Phường Tân Phong"
              />
            </label>

            <div className="form-row">
              <label>
                Xã / Phường
                <input
                  value={form.xa}
                  onChange={(e) => setForm({ ...form, xa: e.target.value })}
                  placeholder="vd: Tân Phong"
                />
              </label>
              <label>
                Tỉnh / Thành
                <input
                  value={form.tinh}
                  onChange={(e) => setForm({ ...form, tinh: e.target.value })}
                  placeholder="vd: Lai Châu"
                />
              </label>
            </div>

            <label>
              Vai trò
              <select
                value={form.role}
                onChange={(e) => setForm({ ...form, role: e.target.value as Role })}
              >
                <option value="user">Người dùng</option>
                <option value="commune">Hành chính công xã</option>
                <option value="province">Hành chính công tỉnh</option>
                <option value="admin">Quản trị</option>
              </select>
            </label>

            {formError && <div className="error">{formError}</div>}

            <div className="modal-actions">
              <button type="button" className="ghost" onClick={() => setForm(null)} disabled={saving}>
                Hủy
              </button>
              <button type="submit" className="btn-primary" disabled={saving || !canSubmit}>
                {saving ? "Đang lưu…" : isCreate ? "Tạo tài khoản" : "Lưu thay đổi"}
              </button>
            </div>
          </form>
        </div>
      )}
    </div>
  );
}
