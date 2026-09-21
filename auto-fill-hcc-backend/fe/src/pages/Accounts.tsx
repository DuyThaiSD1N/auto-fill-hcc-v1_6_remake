import { useCallback, useEffect, useRef, useState } from "react";
import {
  createUser,
  deleteUser,
  getProvinces,
  getWards,
  listUsers,
  restoreUser,
  updateUser,
  type Province,
} from "../api";
import type { ManagedUser, Role, User, UserStatusFilter } from "../types";
import { fmtDateTime } from "../format";
import Combobox from "../components/Combobox";
import TopBar, { type View } from "../components/TopBar";

interface Props {
  user: User;
  onLogout: () => void;
  view: View;
  onNavigate: (v: View) => void;
}

interface FormState {
  id: string | null; // null = tạo mới
  originalRole: Role | null;
  originalAccessDisabled: boolean;
  username: string;
  password: string;
  name: string;
  xa: string;
  tinh: string;
  role: Role;
  accessDisabled: boolean;
}

const EMPTY_FORM: FormState = {
  id: null,
  originalRole: null,
  originalAccessDisabled: false,
  username: "",
  password: "",
  name: "",
  xa: "",
  tinh: "",
  role: "user",
  accessDisabled: false,
};

// Nhãn hiển thị + class badge theo role. commune = "Hành chính công xã" (như user, chỉ khác nhãn).
const ROLE_META: Record<Role, { label: string; cls: string }> = {
  admin: { label: "Quản trị", cls: "role-admin" },
  user: { label: "Người dùng", cls: "role-user" },
  commune: { label: "Hành chính công xã", cls: "role-commune" },
  province: { label: "Hành chính công tỉnh", cls: "role-province" },
  province_admin: { label: "Tỉnh (báo cáo)", cls: "role-province" },
};

// Vai trò quyết định địa bàn cần nhập. Tài khoản cấp tỉnh KHÔNG có xã/phường — ép nhập là
// sinh ra một "xã" không có thật trong báo cáo hành chính; để trống mà vẫn hiện ô thì cán bộ
// tưởng mình quên điền. Nên ẩn hẳn.
const ROLE_LOCATION: Record<Role, { tinh: "required" | "optional"; xa: "required" | "optional" | "hidden" }> = {
  admin: { tinh: "optional", xa: "optional" },
  user: { tinh: "optional", xa: "optional" },
  commune: { tinh: "required", xa: "required" },
  province: { tinh: "required", xa: "hidden" },
  province_admin: { tinh: "required", xa: "hidden" },
};

// Hai vai trò "tỉnh" nghe gần giống nhau nhưng hậu quả ngược nhau — một cái là ĐƠN VỊ được
// tính số liệu, một cái chỉ xem. Chọn nhầm là tự đẻ thêm một dòng 0 hồ sơ vào bảng báo cáo.
const ROLE_HINT: Record<Role, string> = {
  admin: "Toàn quyền: quản lý tài khoản, xem thống kê và xuất báo cáo.",
  user: "Chỉ dùng extension để điền và đính kèm hồ sơ. Không vào được trang quản trị.",
  commune: "Là một ĐƠN VỊ cấp xã/phường. Hồ sơ của tài khoản này được tính vào số liệu đơn vị.",
  province: "Là một ĐƠN VỊ cấp tỉnh. Hồ sơ của tài khoản này được tính vào số liệu đơn vị.",
  province_admin:
    "Chỉ XEM báo cáo của mọi xã/phường trong tỉnh. Không xử lý hồ sơ, không tính vào số liệu đơn vị.",
};

const PAGE_SIZE = 20;
const isOfficialRole = (role: Role | null): boolean => role === "commune" || role === "province";
type RoleFilter = "all" | Role;
const ROLE_FILTER_OPTIONS: { key: RoleFilter; label: string }[] = [
  { key: "all", label: "Tất cả vai trò" },
  { key: "admin", label: "Quản trị" },
  { key: "user", label: "Người dùng" },
  { key: "commune", label: "Hành chính công xã" },
  { key: "province", label: "Hành chính công tỉnh" },
  { key: "province_admin", label: "Tỉnh (báo cáo)" },
];

const STATUS_FILTER_OPTIONS: { key: UserStatusFilter; label: string }[] = [
  { key: "all", label: "Đang dùng" },
  { key: "active", label: "Hoạt động" },
  { key: "disabled", label: "Tạm khóa" },
  { key: "deleted", label: "Đã xóa" },
];

const foldLocation = (value: string): string =>
  value
    .replace(/Đ/g, "D")
    .replace(/đ/g, "d")
    .normalize("NFD")
    .replace(/[̀-ͯ]/g, "")
    .toLowerCase()
    .trim();

const withoutWardType = (value: string): string =>
  value.replace(/^(Phường|Xã|Đặc khu)\s+/i, "").trim();

function findProvince(provinces: Province[], value: string): Province | undefined {
  const folded = foldLocation(value);
  return provinces.find(
    (province) =>
      foldLocation(province.text) === folded || foldLocation(province.name) === folded,
  );
}

function findWard(wards: string[], value: string): string | undefined {
  const folded = foldLocation(value);
  const exact = wards.find((ward) => foldLocation(ward) === folded);
  if (exact) return exact;
  const legacyMatches = wards.filter(
    (ward) => foldLocation(withoutWardType(ward)) === folded,
  );
  return legacyMatches.length === 1 ? legacyMatches[0] : undefined;
}

export default function Accounts({ user, onLogout, view, onNavigate }: Props) {
  const [items, setItems] = useState<ManagedUser[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [roleFilter, setRoleFilter] = useState<RoleFilter>("all");
  const [statusFilter, setStatusFilter] = useState<UserStatusFilter>("all");
  const [tinhFilter, setTinhFilter] = useState("");
  const [search, setSearch] = useState("");      // giá trị đang gõ
  const [keyword, setKeyword] = useState("");    // giá trị đã chốt (debounce) → mới gọi API
  const [confirmDelete, setConfirmDelete] = useState<ManagedUser | null>(null);
  const [deleteTyped, setDeleteTyped] = useState("");
  const [busyRow, setBusyRow] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [form, setForm] = useState<FormState | null>(null);
  const [saving, setSaving] = useState(false);
  const [formError, setFormError] = useState("");
  const [provinces, setProvinces] = useState<Province[]>([]);
  const [wards, setWards] = useState<string[]>([]);
  const [provincesLoading, setProvincesLoading] = useState(true);
  const [wardsLoading, setWardsLoading] = useState(false);
  const [provincesError, setProvincesError] = useState("");
  const [locationError, setLocationError] = useState("");
  const wardsCache = useRef(new Map<string, string[]>());
  const wardsRequestId = useRef(0);

  const load = useCallback(async () => {
    setLoading(true);
    setError("");
    try {
      const res = await listUsers(page, PAGE_SIZE, {
        role: roleFilter === "all" ? undefined : roleFilter,
        status: statusFilter,
        tinh: tinhFilter || undefined,
        q: keyword,
      });
      const lastPage = Math.max(1, Math.ceil(res.total / PAGE_SIZE));
      if (page > lastPage) {
        setPage(lastPage);
        return;
      }
      setItems(res.items);
      setTotal(res.total);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Lỗi tải danh sách");
    } finally {
      setLoading(false);
    }
  }, [page, roleFilter, statusFilter, tinhFilter, keyword]);

  useEffect(() => {
    load();
  }, [load]);

  // Gõ tới đâu gọi API tới đó là mỗi phím một request. Chốt sau 300ms ngừng gõ.
  useEffect(() => {
    const next = search.trim();
    if (next === keyword) return;
    const timer = setTimeout(() => {
      setKeyword(next);
      setPage(1); // từ khóa mới → kết quả mới, đứng ở trang 3 là thấy bảng rỗng
    }, 300);
    return () => clearTimeout(timer);
  }, [search, keyword]);

  useEffect(() => {
    const controller = new AbortController();
    let active = true;
    setProvincesLoading(true);
    getProvinces(controller.signal)
      .then((result) => {
        if (!active) return;
        setProvinces(result.provinces);
        setProvincesError("");
      })
      .catch((reason) => {
        if (!active || (reason instanceof DOMException && reason.name === "AbortError")) return;
        setProvincesError(
          reason instanceof Error ? reason.message : "Không tải được danh mục tỉnh/thành",
        );
      })
      .finally(() => {
        if (active) setProvincesLoading(false);
      });
    return () => {
      active = false;
      controller.abort();
    };
  }, []);

  useEffect(() => {
    const requestId = ++wardsRequestId.current;
    if (!form) {
      setWards([]);
      setWardsLoading(false);
      return;
    }
    const province = findProvince(provinces, form.tinh);
    if (!province) {
      setWards([]);
      setWardsLoading(false);
      return;
    }

    // Tài khoản cũ có thể lưu tên ngắn. Chỉ chuẩn hóa trong form; DB chỉ thay đổi
    // khi quản trị viên chủ động bấm Lưu thay đổi.
    if (form.tinh !== province.text) {
      setForm((current) => current ? { ...current, tinh: province.text } : current);
      return;
    }

    const applyWards = (items: string[]) => {
      setWards(items);
      setForm((current) => {
        if (!current || current.tinh !== province.text || !current.xa) return current;
        const canonicalWard = findWard(items, current.xa);
        return canonicalWard && canonicalWard !== current.xa
          ? { ...current, xa: canonicalWard }
          : current;
      });
    };

    const cached = wardsCache.current.get(province.slug);
    if (cached) {
      applyWards(cached);
      setWardsLoading(false);
      return;
    }

    const controller = new AbortController();
    setWards([]);
    setWardsLoading(true);
    setLocationError("");
    getWards(province.slug, controller.signal)
      .then((result) => {
        if (requestId !== wardsRequestId.current) return;
        wardsCache.current.set(province.slug, result.communes);
        applyWards(result.communes);
      })
      .catch((reason) => {
        if (reason instanceof DOMException && reason.name === "AbortError") return;
        if (requestId !== wardsRequestId.current) return;
        setLocationError(
          reason instanceof Error ? reason.message : "Không tải được danh mục xã/phường",
        );
      })
      .finally(() => {
        if (requestId === wardsRequestId.current) setWardsLoading(false);
      });
    return () => controller.abort();
  }, [form?.tinh, provinces]);

  function openCreate() {
    setFormError("");
    setLocationError("");
    setForm({ ...EMPTY_FORM });
  }

  function openEdit(u: ManagedUser) {
    setFormError("");
    setLocationError("");
    setForm({
      id: u.id,
      originalRole: u.role,
      originalAccessDisabled: u.access_disabled,
      username: u.username,
      password: "",
      // Tài khoản cấp tỉnh có thể còn sót `xa` từ dữ liệu cũ. Ô đó bị ẩn theo vai trò, nên
      // mang giá trị vào form là lưu ngầm một thứ cán bộ không nhìn thấy.
      xa: ROLE_LOCATION[u.role].xa === "hidden" ? "" : u.xa ?? "",
      tinh: u.tinh ?? "",
      role: u.role,
      accessDisabled: u.access_disabled,
      name: u.name ?? "",
    });
  }

  async function submitForm(e: React.FormEvent) {
    e.preventDefault();
    if (!form) return;
    setFormError("");
    const changesOfficialScope =
      form.id !== null &&
      form.originalRole !== null &&
      isOfficialRole(form.originalRole) !== isOfficialRole(form.role);
    if (changesOfficialScope) {
      const entersOfficialScope = isOfficialRole(form.role);
      const message = entersOfficialScope
        ? "Đổi sang vai trò HCC sẽ cộng toàn bộ lịch sử của tài khoản này vào \"Hồ sơ thực tế\". Bạn có muốn tiếp tục?"
        : "Bỏ vai trò HCC sẽ loại toàn bộ lịch sử của tài khoản này khỏi \"Hồ sơ thực tế\". Dữ liệu vẫn còn trong \"Tất cả hồ sơ\". Bạn có muốn tiếp tục?";
      if (!window.confirm(message)) return;
    }
    if (
      form.id !== null &&
      !form.originalAccessDisabled &&
      form.accessDisabled &&
      !window.confirm(
        `Tạm khóa tài khoản "${form.username}"? Các phiên đang đăng nhập sẽ bị ngắt.`,
      )
    ) return;
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
          // Vai trò của CHÍNH MÌNH không gửi lên: BE chặn tự đổi vai trò, gửi nguyên giá trị
          // cũ thì không sao, nhưng không gửi mới là đúng ý định của form đang khóa ô đó.
          role: form.id === user.id ? undefined : form.role,
          access_disabled: form.accessDisabled,
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

  function askDelete(u: ManagedUser) {
    if (u.id === user.id) return;
    setError("");
    setDeleteTyped("");
    setConfirmDelete(u);
  }

  async function doDelete() {
    const target = confirmDelete;
    if (!target) return;
    setError("");
    setBusyRow(target.id);
    try {
      await deleteUser(target.id);
      setConfirmDelete(null);
      // Xóa item cuối của trang (không phải trang 1) → lùi 1 trang cho khỏi trống; còn lại reload.
      if (items.length === 1 && page > 1) setPage((p) => p - 1);
      else await load();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Xóa thất bại");
      setConfirmDelete(null);
    } finally {
      setBusyRow("");
    }
  }

  /** Khóa nhanh từ hộp thoại xóa — lối thoát được khuyến nghị thay cho xóa hẳn. */
  async function lockInstead() {
    const target = confirmDelete;
    if (!target) return;
    setError("");
    setBusyRow(target.id);
    try {
      await updateUser(target.id, { access_disabled: true });
      setConfirmDelete(null);
      await load();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Tạm khóa thất bại");
    } finally {
      setBusyRow("");
    }
  }

  async function handleRestore(u: ManagedUser) {
    setError("");
    setBusyRow(u.id);
    try {
      await restoreUser(u.id);
      await load();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Khôi phục thất bại");
    } finally {
      setBusyRow("");
    }
  }

  const isCreate = form?.id === null;
  const roleChangesOfficialScope = Boolean(
    form &&
      form.id !== null &&
      form.originalRole !== null &&
      isOfficialRole(form.originalRole) !== isOfficialRole(form.role),
  );
  const selectedProvince = form ? findProvince(provinces, form.tinh) : undefined;
  const rule = ROLE_LOCATION[form?.role ?? "user"];
  const showWard = rule.xa !== "hidden";
  // Giá trị đã nhập phải khớp danh mục hiện hành (tài khoản cũ lưu tên ngắn thì form đã tự
  // chuẩn hóa ở effect bên trên).
  const locationValid = Boolean(
    form &&
      ((!form.tinh.trim() && !form.xa.trim()) ||
        (selectedProvince && (!form.xa.trim() || Boolean(findWard(wards, form.xa))))),
  );
  // Ràng buộc theo vai trò CHỈ áp khi TẠO MỚI. Tài khoản cũ đang thiếu địa bàn thì vẫn phải
  // sửa được tên hiển thị hay mật khẩu — chặn ở đây là biến một thao tác vặt thành việc dọn
  // dữ liệu bắt buộc.
  const roleLocationOk =
    !form ||
    !isCreate ||
    ((rule.tinh !== "required" || Boolean(form.tinh.trim())) &&
      (rule.xa !== "required" || Boolean(form.xa.trim())));
  const canSubmit =
    form &&
    locationValid &&
    roleLocationOk &&
    (isCreate
      ? form.username.trim().length >= 3 && form.password.length >= 8
      : form.password === "" || form.password.length >= 8);

  const totalPages = Math.max(1, Math.ceil(total / PAGE_SIZE));

  /** Mọi bộ lọc đều phải đưa về trang 1 — đứng ở trang 3 rồi lọc lại là thấy bảng rỗng. */
  function changeFilter(apply: () => void) {
    apply();
    setPage(1);
  }

  return (
    <div className="app">
      <TopBar user={user} view={view} onNavigate={onNavigate} onLogout={onLogout} />

      <div className="stats-head">
        <div>
          <h1 className="page-title">Quản lý tài khoản</h1>
          <p className="muted page-sub">
            Vai trò quyết định địa bàn cần nhập — tài khoản cấp tỉnh không gắn xã/phường
          </p>
        </div>
        <div className="accounts-head-actions">
          <label className="accounts-role-filter accounts-search">
            <span>Tìm tài khoản</span>
            <input
              value={search}
              onChange={(event) => setSearch(event.target.value)}
              placeholder="Tên đăng nhập hoặc tên hiển thị…"
            />
          </label>
          <label className="accounts-role-filter">
            <span>Tỉnh / Thành</span>
            <select
              value={tinhFilter}
              onChange={(event) => changeFilter(() => setTinhFilter(event.target.value))}
              disabled={loading || provincesLoading || Boolean(provincesError)}
            >
              <option value="">Tất cả tỉnh/thành</option>
              {provinces.map((province) => (
                <option value={province.text} key={province.slug}>{province.text}</option>
              ))}
            </select>
          </label>
          <label className="accounts-role-filter">
            <span>Trạng thái</span>
            <select
              value={statusFilter}
              onChange={(event) =>
                changeFilter(() => setStatusFilter(event.target.value as UserStatusFilter))
              }
              disabled={loading}
            >
              {STATUS_FILTER_OPTIONS.map((option) => (
                <option value={option.key} key={option.key}>{option.label}</option>
              ))}
            </select>
          </label>
          <label className="accounts-role-filter">
            <span>Vai trò</span>
            <select
              value={roleFilter}
              onChange={(event) => changeFilter(() => setRoleFilter(event.target.value as RoleFilter))}
              disabled={loading}
            >
              {ROLE_FILTER_OPTIONS.map((option) => (
                <option value={option.key} key={option.key}>{option.label}</option>
              ))}
            </select>
          </label>
          <button className="btn-primary" onClick={openCreate}>
            + Thêm tài khoản
          </button>
        </div>
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
              <th className="center">Trạng thái</th>
              <th>Đăng nhập gần nhất</th>
              <th className="center">Thao tác</th>
            </tr>
          </thead>
          <tbody>
            {loading && (
              <tr>
                <td colSpan={8} className="center muted">
                  Đang tải…
                </td>
              </tr>
            )}
            {!loading && items.length === 0 && (
              <tr>
                <td colSpan={8} className="center muted">
                  {roleFilter === "all" && statusFilter === "all" && !tinhFilter && !keyword
                    ? "Chưa có tài khoản nào"
                    : "Không có tài khoản khớp bộ lọc đang chọn"}
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
                  <td className="center">
                    <span
                      className={`badge ${
                        u.deleted_at ? "role-user" : u.access_disabled ? "warn" : "ok"
                      }`}
                    >
                      {u.deleted_at ? "Đã xóa" : u.access_disabled ? "Tạm khóa" : "Hoạt động"}
                    </span>
                  </td>
                  <td className="muted">
                    {u.last_login_at ? fmtDateTime(u.last_login_at) : "—"}
                  </td>
                  <td className="center">
                    <div className="row-actions">
                      {u.deleted_at ? (
                        // Tài khoản đã xóa mềm: không sửa được (BE cũng chặn), chỉ khôi phục.
                        <button
                          className="ghost sm"
                          disabled={busyRow === u.id}
                          onClick={() => handleRestore(u)}
                        >
                          {busyRow === u.id ? "Đang khôi phục…" : "Khôi phục"}
                        </button>
                      ) : (
                        <>
                          <button className="ghost sm" onClick={() => openEdit(u)}>
                            Sửa
                          </button>
                          <button
                            className="ghost sm danger"
                            disabled={u.id === user.id}
                            title={u.id === user.id ? "Không thể tự xóa" : "Xóa tài khoản"}
                            onClick={() => askDelete(u)}
                          >
                            Xóa
                          </button>
                        </>
                      )}
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

      {confirmDelete && (
        <div className="modal-backdrop" onClick={() => !busyRow && setConfirmDelete(null)}>
          <div className="modal-card" onClick={(e) => e.stopPropagation()}>
            <h2>Xóa tài khoản {confirmDelete.username}</h2>

            <p className="muted">
              Tài khoản sẽ ngừng đăng nhập được và <b>biến khỏi bảng theo đơn vị</b> của trang
              Thống kê, kèm toàn bộ hồ sơ đã làm. Dữ liệu vẫn được giữ lại trong hệ thống nên
              khôi phục được — xem ở bộ lọc trạng thái <b>Đã xóa</b>.
            </p>

            <div className="role-impact-note" role="note">
              <strong>Chỉ tạm dừng dùng tài khoản?</strong>
              <span>
                Chọn <b>Tạm khóa</b>: tài khoản không đăng nhập được nữa nhưng đơn vị vẫn nằm
                trong báo cáo và số hồ sơ vẫn được tính.
              </span>
            </div>

            <label>
              Gõ <b>{confirmDelete.username}</b> để xác nhận
              <input
                value={deleteTyped}
                autoFocus
                autoComplete="off"
                onChange={(e) => setDeleteTyped(e.target.value)}
                placeholder={confirmDelete.username}
              />
            </label>

            <div className="modal-actions">
              <button
                type="button"
                className="ghost"
                onClick={() => setConfirmDelete(null)}
                disabled={Boolean(busyRow)}
              >
                Hủy
              </button>
              <button
                type="button"
                className="ghost"
                onClick={lockInstead}
                disabled={Boolean(busyRow) || confirmDelete.access_disabled}
                title={confirmDelete.access_disabled ? "Tài khoản đã bị tạm khóa" : ""}
              >
                Tạm khóa thay vì xóa
              </button>
              <button
                type="button"
                className="btn-primary danger"
                onClick={doDelete}
                disabled={Boolean(busyRow) || deleteTyped.trim() !== confirmDelete.username}
              >
                {busyRow ? "Đang xử lý…" : "Xóa tài khoản"}
              </button>
            </div>
          </div>
        </div>
      )}

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

            {/* VAI TRÒ đứng TRƯỚC địa bàn: nó quyết định có phải nhập xã/phường hay không.
                Để sau thì cán bộ điền xong địa bàn mới biết ô vừa điền bị ẩn đi. */}
            <label>
              Vai trò
              <select
                value={form.role}
                disabled={form.id === user.id}
                onChange={(e) => {
                  const nextRole = e.target.value as Role;
                  setLocationError("");
                  // Vai trò cấp tỉnh không có xã — xóa luôn giá trị cũ, không giữ lại một
                  // giá trị đã bị ẩn khỏi màn hình rồi âm thầm lưu xuống DB.
                  const clearWard = ROLE_LOCATION[nextRole].xa === "hidden";
                  setForm({ ...form, role: nextRole, xa: clearWard ? "" : form.xa });
                }}
              >
                <option value="user">Người dùng</option>
                <option value="commune">Hành chính công xã</option>
                <option value="province">Hành chính công tỉnh</option>
                <option value="province_admin">Tỉnh (xem báo cáo thống kê)</option>
                <option value="admin">Quản trị</option>
              </select>
            </label>
            <p className="form-hint">{ROLE_HINT[form.role]}</p>
            {form.id === user.id && (
              <p className="form-hint">
                Không thể tự đổi vai trò của chính mình — hãy nhờ một quản trị viên khác.
              </p>
            )}

            <div className="form-row">
              <Combobox
                label={rule.tinh === "required" ? "Tỉnh / Thành *" : "Tỉnh / Thành"}
                value={selectedProvince?.text ?? form.tinh}
                options={provinces.map((province) => ({
                  value: province.text,
                  label: province.text,
                }))}
                allLabel="Chưa chọn"
                placeholder="Tìm tỉnh/thành…"
                disabled={provincesLoading || Boolean(provincesError)}
                onChange={(value) => {
                  setLocationError("");
                  setForm({ ...form, tinh: value, xa: "" });
                }}
              />
              {showWard && (
                <Combobox
                  label={rule.xa === "required" ? "Xã / Phường *" : "Xã / Phường"}
                  value={findWard(wards, form.xa) ?? form.xa}
                  options={wards.map((ward) => ({ value: ward, label: ward }))}
                  allLabel="Chưa chọn"
                  placeholder="Tìm xã/phường…"
                  disabled={!selectedProvince || wardsLoading}
                  onChange={(value) => {
                    setLocationError("");
                    setForm({ ...form, xa: value });
                  }}
                />
              )}
            </div>
            {!showWard && (
              <p className="form-hint">Vai trò cấp tỉnh không gắn với xã/phường.</p>
            )}

            {(provincesLoading || wardsLoading) && (
              <div className="location-status">
                {provincesLoading
                  ? "Đang tải danh mục tỉnh/thành…"
                  : "Đang tải danh mục xã/phường…"}
              </div>
            )}
            {(provincesError || locationError) && (
              <div className="error">{provincesError || locationError}</div>
            )}
            {!provincesError &&
              !locationError &&
              !provincesLoading &&
              form.tinh &&
              !selectedProvince && (
                <div className="error">
                  Tỉnh/thành cũ không còn trong danh mục. Vui lòng chọn lại.
                </div>
              )}
            {!provincesError &&
              !locationError &&
              showWard &&
              selectedProvince &&
              form.xa &&
              !wardsLoading &&
              !findWard(wards, form.xa) && (
                <div className="error">
                  Xã/phường cũ không thuộc tỉnh đã chọn. Vui lòng chọn lại.
                </div>
              )}

            {!isCreate && (
              <label>
                Trạng thái tài khoản
                <select
                  value={form.accessDisabled ? "off" : "on"}
                  disabled={form.id === user.id}
                  onChange={(e) => setForm({ ...form, accessDisabled: e.target.value === "off" })}
                >
                  <option value="on">Đang hoạt động</option>
                  <option value="off">Tạm khóa</option>
                </select>
              </label>
            )}

            {roleChangesOfficialScope && form && (
              <div className="role-impact-note" role="note">
                <strong>Ảnh hưởng số liệu thống kê</strong>
                <span>
                  {isOfficialRole(form.role)
                    ? "Toàn bộ lịch sử của tài khoản sẽ được tính vào Hồ sơ thực tế."
                    : "Toàn bộ lịch sử của tài khoản sẽ không còn được tính vào Hồ sơ thực tế; dữ liệu vẫn còn trong Tất cả hồ sơ."}
                </span>
              </div>
            )}

            {!roleLocationOk && (
              <div className="error">
                Vai trò &ldquo;{ROLE_META[form.role].label}&rdquo; cần
                {rule.xa === "required" ? " tỉnh/thành và xã/phường." : " tỉnh/thành."}
              </div>
            )}

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
