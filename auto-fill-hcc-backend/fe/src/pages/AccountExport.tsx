import { useEffect, useMemo, useState } from "react";

import { exportAccounts, getAccountExportOptions } from "../api";
import TopBar, { type View } from "../components/TopBar";
import type { AccountExportOptions, User } from "../types";

interface Props {
  user: User;
  onLogout: () => void;
  view: View;
  onNavigate: (view: View) => void;
}

const ALL = "";
const num = (value: number) => value.toLocaleString("vi-VN");

function saveBlob(blob: Blob, filename: string) {
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  a.click();
  URL.revokeObjectURL(url);
}

export default function AccountExport({ user, onLogout, view, onNavigate }: Props) {
  const [options, setOptions] = useState<AccountExportOptions | null>(null);
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState("");
  const [province, setProvince] = useState(ALL);
  const [exporting, setExporting] = useState(false);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");

  useEffect(() => {
    const controller = new AbortController();
    getAccountExportOptions(controller.signal)
      .then(setOptions)
      .catch((reason) => {
        if (reason instanceof DOMException && reason.name === "AbortError") return;
        setLoadError(reason instanceof Error ? reason.message : "Không tải được danh sách tỉnh.");
      })
      .finally(() => setLoading(false));
    return () => controller.abort();
  }, []);

  const provinces = options?.provinces ?? [];
  const selected = useMemo(() => {
    const rows = province === ALL ? provinces : provinces.filter((p) => p.value === province);
    return rows.reduce(
      (sum, p) => ({
        commune: sum.commune + p.communeCount,
        province: sum.province + p.provinceCount,
        missing: sum.missing + p.missingPasswordCount,
      }),
      { commune: 0, province: 0, missing: 0 },
    );
  }, [provinces, province]);
  const totalSelected = selected.commune + selected.province;
  const selectedLabel = province === ALL ? "tất cả tỉnh/thành" : province;

  async function runExport(event: React.FormEvent) {
    event.preventDefault();
    setExporting(true);
    setError("");
    setSuccess("");
    try {
      const { blob, filename } = await exportAccounts(province);
      const name = filename || "tai-khoan-hcc.xlsx";
      saveBlob(blob, name);
      setSuccess(`Đã tạo ${name} với ${num(totalSelected)} tài khoản.`);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Không xuất được danh sách.");
    } finally {
      setExporting(false);
    }
  }

  return (
    <div className="app">
      <TopBar user={user} view={view} onNavigate={onNavigate} onLogout={onLogout} />

      <div className="stats-head report-heading">
        <div>
          <button type="button" className="back-link" onClick={() => onNavigate("accounts")}>
            ‹ Tài khoản
          </button>
          <h1 className="page-title">Xuất danh sách tài khoản</h1>
          <p className="muted page-sub">
            Tài khoản Hành chính công xã và Hành chính công tỉnh, kèm mật khẩu nếu hệ thống có lưu.
          </p>
        </div>
      </div>

      <form className="report-form" onSubmit={runExport}>
        <section className="report-card" aria-labelledby="export-province-title">
          <div className="report-section-head">
            <div>
              <h2 id="export-province-title">Tỉnh / thành</h2>
              <p>Chỉ liệt kê tỉnh/thành đang có tài khoản HCC. Tài khoản chưa gán tỉnh không được xuất.</p>
            </div>
          </div>

          {loading && <div className="report-loading" aria-live="polite">Đang tải danh sách tỉnh…</div>}
          {loadError && <div className="error" role="alert">{loadError}</div>}
          {!loading && !loadError && provinces.length === 0 && (
            <div className="muted">Chưa có tài khoản Hành chính công nào để xuất.</div>
          )}

          {!loading && !loadError && provinces.length > 0 && (
            <fieldset className="export-province-list">
              <legend className="sr-only">Chọn tỉnh/thành cần xuất</legend>
              <div className="table-wrap">
                <table>
                  <thead>
                    <tr>
                      <th>Tỉnh / thành</th>
                      <th className="num">HCC xã</th>
                      <th className="num">HCC tỉnh</th>
                      <th className="num">Chưa lưu mật khẩu</th>
                    </tr>
                  </thead>
                  <tbody>
                    {[
                      {
                        value: ALL,
                        label: "Tất cả tỉnh/thành",
                        communeCount: provinces.reduce((s, p) => s + p.communeCount, 0),
                        provinceCount: provinces.reduce((s, p) => s + p.provinceCount, 0),
                        missingPasswordCount: provinces.reduce((s, p) => s + p.missingPasswordCount, 0),
                      },
                      ...provinces,
                    ].map((p) => (
                      <tr
                        key={p.value || "__all"}
                        className={`${province === p.value ? "selected" : ""}${p.value === ALL ? " export-all-row" : ""}`}
                        onClick={() => setProvince(p.value)}
                      >
                        <td>
                          <label className="export-radio">
                            <input
                              type="radio"
                              name="export-province"
                              value={p.value}
                              checked={province === p.value}
                              onChange={() => setProvince(p.value)}
                            />
                            <span>{p.label}</span>
                          </label>
                        </td>
                        <td className="num">{num(p.communeCount)}</td>
                        <td className="num">{num(p.provinceCount)}</td>
                        <td className="num">
                          {p.missingPasswordCount ? num(p.missingPasswordCount) : <span className="muted">0</span>}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </fieldset>
          )}
        </section>

        <div className="role-impact-note" role="note">
          <strong>File có mật khẩu dạng chữ thường</strong>
          <span>
            Không gửi file qua nhóm chat chung; xoá file sau khi đã bàn giao. Lượt xuất được ghi vào
            nhật ký. Tài khoản chưa lưu mật khẩu sẽ để trống cột Mật khẩu.
          </span>
        </div>
        {options && !options.vaultEnabled && (
          <div className="error" role="status">
            Máy chủ chưa cấu hình khoá lưu mật khẩu — cột Mật khẩu sẽ trống với mọi tài khoản.
          </div>
        )}

        <section className="report-submit-card" aria-labelledby="export-summary-title">
          <div>
            <h2 id="export-summary-title">Xuất {selectedLabel}</h2>
            <p>
              {num(totalSelected)} tài khoản · {num(selected.commune)} HCC xã · {num(selected.province)} HCC tỉnh
              {selected.missing ? ` · ${num(selected.missing)} chưa lưu mật khẩu` : ""}
              {province === ALL && provinces.length > 1 ? ` · mỗi tỉnh/thành một sheet (${num(provinces.length)} sheet)` : ""}
            </p>
          </div>
          <div className="report-export-actions">
            <button
              className="btn-primary report-export-btn"
              type="submit"
              disabled={exporting || loading || Boolean(loadError) || totalSelected === 0}
            >
              {exporting ? "Đang tạo file…" : "Xuất Excel"}
            </button>
          </div>
        </section>

        <div className="report-feedback" aria-live="polite">
          {error && <div className="error" role="alert">{error}</div>}
          {success && <div className="success">{success}</div>}
        </div>
      </form>
    </div>
  );
}
