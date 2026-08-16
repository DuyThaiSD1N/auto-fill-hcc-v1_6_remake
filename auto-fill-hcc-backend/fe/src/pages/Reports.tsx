import { useEffect, useMemo, useRef, useState } from "react";

import { exportReportExcel, getReportOptions } from "../api";
import AccountMultiSelect from "../components/AccountMultiSelect";
import Combobox from "../components/Combobox";
import TopBar, { type View } from "../components/TopBar";
import type {
  ReportAccount,
  ReportOptionsResp,
  ReportSelectionMode,
  User,
} from "../types";


interface Props {
  user: User;
  onLogout: () => void;
  view: View;
  onNavigate: (view: View) => void;
}

const MAX_EXPORT_ACCOUNTS = 200;
const OFFICIAL_ROLES = new Set(["commune", "province"]);

function isOfficialAccount(account: ReportAccount): boolean {
  return OFFICIAL_ROLES.has(account.role);
}

function officialRoleLabel(account: ReportAccount): string {
  return account.role === "province" ? "HCC tỉnh" : "HCC xã";
}

function vietnamDay(): string {
  const parts = new Intl.DateTimeFormat("en", {
    timeZone: "Asia/Ho_Chi_Minh",
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
  }).formatToParts(new Date());
  const values = Object.fromEntries(parts.map((part) => [part.type, part.value]));
  return `${values.year}-${values.month}-${values.day}`;
}

function fold(value: string): string {
  return value
    .replace(/Đ/g, "D")
    .replace(/đ/g, "d")
    .normalize("NFD")
    .replace(/[̀-ͯ]/g, "")
    .toLowerCase()
    .trim();
}

function saveDownload(blob: Blob, filename: string) {
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = filename;
  document.body.appendChild(anchor);
  anchor.click();
  anchor.remove();
  window.setTimeout(() => URL.revokeObjectURL(url), 1_000);
}

export default function Reports({ user, onLogout, view, onNavigate }: Props) {
  const today = vietnamDay();
  const [dateFrom, setDateFrom] = useState(today);
  const [dateTo, setDateTo] = useState(today);
  const [mode, setMode] = useState<ReportSelectionMode>("province");
  const [province, setProvince] = useState("");
  const [officialOnly, setOfficialOnly] = useState(true);
  const [selectedIds, setSelectedIds] = useState<string[]>([]);
  const [options, setOptions] = useState<ReportOptionsResp>({ provinces: [], accounts: [] });
  const [loadingOptions, setLoadingOptions] = useState(true);
  const [optionsError, setOptionsError] = useState("");
  const [exporting, setExporting] = useState(false);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");
  const exportControllerRef = useRef<AbortController | null>(null);

  useEffect(() => {
    const controller = new AbortController();
    setLoadingOptions(true);
    setOptionsError("");
    getReportOptions(controller.signal)
      .then(setOptions)
      .catch((reason) => {
        if (reason instanceof DOMException && reason.name === "AbortError") return;
        setOptionsError(reason instanceof Error ? reason.message : "Không tải được lựa chọn báo cáo.");
      })
      .finally(() => {
        if (!controller.signal.aborted) setLoadingOptions(false);
      });
    return () => controller.abort();
  }, []);

  useEffect(() => () => {
    const controller = exportControllerRef.current;
    exportControllerRef.current = null;
    controller?.abort();
  }, []);

  const allProvinceAccounts = useMemo(() => {
    const key = fold(province);
    return key ? options.accounts.filter((account) => fold(account.tinh || "") === key) : [];
  }, [options.accounts, province]);
  const officialProvinceAccounts = useMemo(
    () => allProvinceAccounts.filter(isOfficialAccount),
    [allProvinceAccounts],
  );

  const accountById = useMemo(
    () => new Map(options.accounts.map((account) => [account.id, account])),
    [options.accounts],
  );
  const selectedAccounts = selectedIds
    .map((id) => accountById.get(id))
    .filter((account): account is ReportAccount => Boolean(account));
  const provinceAccounts = officialOnly ? officialProvinceAccounts : allProvinceAccounts;
  const exportAccounts = mode === "province" ? provinceAccounts : selectedAccounts;
  const dateInvalid = !dateFrom || !dateTo || dateFrom > dateTo;
  const selectionInvalid = exportAccounts.length === 0;
  const officialProvinceEmpty = mode === "province"
    && Boolean(province)
    && officialOnly
    && allProvinceAccounts.length > 0
    && officialProvinceAccounts.length === 0;
  const tooManyAccounts = exportAccounts.length > MAX_EXPORT_ACCOUNTS;
  const canExport = !loadingOptions
    && !optionsError
    && !dateInvalid
    && !selectionInvalid
    && !tooManyAccounts
    && !exporting;

  const provinceOptions = options.provinces.map((item) => ({
    value: item.value,
    label: officialOnly
      ? `${item.label} (${item.officialAccountCount.toLocaleString("vi-VN")} tài khoản HCC)`
      : `${item.label} (${item.accountCount.toLocaleString("vi-VN")} tài khoản)`,
  }));

  async function submit(event: React.FormEvent) {
    event.preventDefault();
    setError("");
    setSuccess("");
    if (dateInvalid) {
      setError("Vui lòng nhập khoảng ngày hợp lệ; từ ngày phải nhỏ hơn hoặc bằng đến ngày.");
      return;
    }
    if (selectionInvalid) {
      if (officialProvinceEmpty) {
        setError("Tỉnh/thành đã chọn chưa có tài khoản HCC xã hoặc HCC tỉnh.");
      } else {
        setError(mode === "province" ? "Vui lòng chọn một tỉnh có tài khoản." : "Vui lòng chọn ít nhất một tài khoản.");
      }
      return;
    }
    if (tooManyAccounts) {
      setError(`Mỗi file hỗ trợ tối đa ${MAX_EXPORT_ACCOUNTS} tài khoản. Vui lòng thu hẹp phạm vi.`);
      return;
    }

    const controller = new AbortController();
    exportControllerRef.current?.abort();
    exportControllerRef.current = controller;
    setExporting(true);
    try {
      const result = await exportReportExcel({
        dateFrom,
        dateTo,
        selectionMode: mode,
        province: mode === "province" ? province : undefined,
        officialOnly: mode === "province" ? officialOnly : undefined,
        accountIds: mode === "accounts" ? selectedIds : undefined,
      }, controller.signal);
      const fallback = `bao_cao_ho_so_${dateFrom}_${dateTo}.xlsx`;
      const filename = result.filename || fallback;
      saveDownload(result.blob, filename);
      setSuccess(`Đã tạo ${filename} với ${exportAccounts.length.toLocaleString("vi-VN")} sheet.`);
    } catch (reason) {
      if (reason instanceof DOMException && reason.name === "AbortError") return;
      setError(reason instanceof Error ? reason.message : "Không thể tạo file Excel. Vui lòng thử lại.");
    } finally {
      if (exportControllerRef.current === controller) {
        exportControllerRef.current = null;
        setExporting(false);
      }
    }
  }

  return (
    <div className="app">
      <TopBar user={user} view={view} onNavigate={onNavigate} onLogout={onLogout} />

      <div className="stats-head report-heading">
        <div>
          <h1 className="page-title">Kết xuất báo cáo Excel</h1>
          <p className="muted page-sub">Mỗi tài khoản được xuất thành một sheet riêng.</p>
        </div>
      </div>

      <form className="report-form" onSubmit={submit}>
        <section className="report-card" aria-labelledby="report-time-title">
          <div className="report-section-head">
            <span className="report-step" aria-hidden="true">1</span>
            <div>
              <h2 id="report-time-title">Khoảng thời gian</h2>
              <p>Hai ngày đều được tính trọn theo giờ Việt Nam.</p>
            </div>
          </div>
          <div className="report-date-grid">
            <label>
              <span>Từ ngày</span>
              <input type="date" value={dateFrom} onChange={(event) => setDateFrom(event.target.value)} required />
            </label>
            <label>
              <span>Đến ngày</span>
              <input type="date" value={dateTo} onChange={(event) => setDateTo(event.target.value)} required />
            </label>
          </div>
          {dateFrom && dateTo && dateFrom > dateTo && (
            <div className="field-error" role="alert">Từ ngày phải nhỏ hơn hoặc bằng đến ngày.</div>
          )}
        </section>

        <section className="report-card" aria-labelledby="report-scope-title">
          <div className="report-section-head">
            <span className="report-step" aria-hidden="true">2</span>
            <div>
              <h2 id="report-scope-title">Phạm vi xuất</h2>
              <p>Chọn toàn bộ tài khoản của một tỉnh hoặc chọn từng tài khoản.</p>
            </div>
          </div>

          <div className="report-mode" role="group" aria-label="Cách chọn phạm vi báo cáo">
            <button
              type="button"
              className={mode === "province" ? "active" : ""}
              aria-pressed={mode === "province"}
              onClick={() => setMode("province")}
            >
              Theo tỉnh
            </button>
            <button
              type="button"
              className={mode === "accounts" ? "active" : ""}
              aria-pressed={mode === "accounts"}
              onClick={() => setMode("accounts")}
            >
              Theo tài khoản
            </button>
          </div>

          {loadingOptions && <div className="report-loading" aria-live="polite">Đang tải danh sách tài khoản…</div>}
          {optionsError && <div className="error" role="alert">{optionsError}</div>}

          {!loadingOptions && !optionsError && mode === "province" && (
            <div className="province-report-scope">
              <div className="province-report-controls">
                <Combobox
                  label="Tỉnh/thành"
                  value={province}
                  options={provinceOptions}
                  onChange={setProvince}
                  allLabel="Chọn tỉnh/thành"
                  placeholder="Tìm tỉnh/thành…"
                />
                <label className="official-account-toggle">
                  <input
                    type="checkbox"
                    checked={officialOnly}
                    onChange={(event) => setOfficialOnly(event.target.checked)}
                  />
                  <span>
                    <strong>Chỉ lấy tài khoản hành chính công</strong>
                    <small>Bao gồm HCC xã và HCC tỉnh; loại trừ admin và người dùng thường.</small>
                  </span>
                </label>
              </div>
              {province && (
                <div className="province-account-preview">
                  {officialProvinceEmpty ? (
                    <div className="province-account-empty" role="status">
                      <strong>Chưa có tài khoản hành chính công</strong>
                      <span>Tỉnh này chưa có tài khoản mang role HCC xã hoặc HCC tỉnh.</span>
                    </div>
                  ) : (
                    <>
                      <strong>
                        {officialOnly
                          ? `${provinceAccounts.length.toLocaleString("vi-VN")}/${allProvinceAccounts.length.toLocaleString("vi-VN")} tài khoản HCC sẽ được xuất`
                          : `${provinceAccounts.length.toLocaleString("vi-VN")} tài khoản sẽ được xuất`}
                      </strong>
                      <ul>
                        {provinceAccounts.slice(0, 8).map((account) => (
                          <li key={account.id}>
                            <span>{account.name || account.xa || account.username}</span>
                            <span className="province-account-identity">
                              <span className="muted">{account.username}</span>
                              {officialOnly && (
                                <span className={`badge compact role-${account.role}`}>
                                  {officialRoleLabel(account)}
                                </span>
                              )}
                            </span>
                          </li>
                        ))}
                      </ul>
                      {provinceAccounts.length > 8 && (
                        <span className="muted">Và {provinceAccounts.length - 8} tài khoản khác.</span>
                      )}
                    </>
                  )}
                </div>
              )}
            </div>
          )}

          {!loadingOptions && !optionsError && mode === "accounts" && (
            <AccountMultiSelect
              accounts={options.accounts}
              selectedIds={selectedIds}
              onChange={setSelectedIds}
            />
          )}
          {tooManyAccounts && (
            <div className="field-error" role="alert">
              Đã chọn {exportAccounts.length.toLocaleString("vi-VN")} tài khoản; mỗi file hỗ trợ tối đa {MAX_EXPORT_ACCOUNTS}.
            </div>
          )}
        </section>

        <section className="report-submit-card" aria-labelledby="report-summary-title">
          <div>
            <h2 id="report-summary-title">Sẵn sàng kết xuất</h2>
            <p>
              {exportAccounts.length.toLocaleString("vi-VN")} tài khoản · {exportAccounts.length.toLocaleString("vi-VN")} sheet
              {dateFrom && dateTo ? ` · ${dateFrom} đến ${dateTo}` : ""}
            </p>
          </div>
          <button className="btn-primary report-export-btn" type="submit" disabled={!canExport}>
            {exporting ? "Đang tạo file…" : "Xuất file Excel"}
          </button>
        </section>

        <div className="report-feedback" aria-live="polite">
          {error && <div className="error" role="alert">{error}</div>}
          {success && <div className="success">{success}</div>}
        </div>
      </form>
    </div>
  );
}
