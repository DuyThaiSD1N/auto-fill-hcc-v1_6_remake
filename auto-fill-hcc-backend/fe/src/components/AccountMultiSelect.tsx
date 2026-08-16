import { useMemo, useState } from "react";

import type { ReportAccount, Role } from "../types";


const ROLE_LABEL: Record<Role, string> = {
  admin: "Quản trị",
  user: "Người dùng",
  commune: "HCC xã",
  province: "HCC tỉnh",
};

function fold(value: string): string {
  return value
    .replace(/Đ/g, "D")
    .replace(/đ/g, "d")
    .normalize("NFD")
    .replace(/[̀-ͯ]/g, "")
    .toLowerCase()
    .trim();
}

export default function AccountMultiSelect({
  accounts,
  selectedIds,
  onChange,
}: {
  accounts: ReportAccount[];
  selectedIds: string[];
  onChange: (ids: string[]) => void;
}) {
  const [query, setQuery] = useState("");
  const selected = useMemo(() => new Set(selectedIds), [selectedIds]);
  const filtered = useMemo(() => {
    const needle = fold(query);
    const rows = needle
      ? accounts.filter((account) =>
          fold([
            account.username,
            account.name,
            account.xa,
            account.tinh,
            ROLE_LABEL[account.role],
          ].filter(Boolean).join(" ")).includes(needle),
        )
      : accounts;
    return [...rows].sort((left, right) =>
      [left.tinh || "", left.xa || left.name || "", left.username]
        .join("|")
        .localeCompare(
          [right.tinh || "", right.xa || right.name || "", right.username].join("|"),
          "vi",
        ),
    );
  }, [accounts, query]);

  const allFilteredSelected = filtered.length > 0 && filtered.every((account) => selected.has(account.id));

  function toggle(accountId: string) {
    const next = new Set(selected);
    if (next.has(accountId)) next.delete(accountId);
    else next.add(accountId);
    onChange([...next]);
  }

  function toggleFiltered() {
    const next = new Set(selected);
    if (allFilteredSelected) filtered.forEach((account) => next.delete(account.id));
    else filtered.forEach((account) => next.add(account.id));
    onChange([...next]);
  }

  return (
    <div className="account-picker">
      <div className="account-picker-toolbar">
        <label className="report-search-field">
          <span>Tìm tài khoản</span>
          <input
            type="search"
            value={query}
            onChange={(event) => setQuery(event.target.value)}
            placeholder="Tên đăng nhập, đơn vị, tỉnh hoặc xã…"
          />
        </label>
        <div className="account-picker-actions">
          <button type="button" className="ghost sm" onClick={toggleFiltered} disabled={!filtered.length}>
            {allFilteredSelected ? "Bỏ chọn kết quả" : "Chọn tất cả kết quả"}
          </button>
          <button type="button" className="ghost sm" onClick={() => onChange([])} disabled={!selected.size}>
            Bỏ chọn tất cả
          </button>
        </div>
      </div>

      <div className="account-picker-summary" aria-live="polite">
        Đã chọn <strong>{selected.size.toLocaleString("vi-VN")}</strong> / {accounts.length.toLocaleString("vi-VN")} tài khoản
      </div>

      <div className="account-picker-list" role="group" aria-label="Danh sách tài khoản có thể xuất báo cáo">
        {filtered.map((account) => (
          <label className="account-check-row" key={account.id}>
            <input
              type="checkbox"
              checked={selected.has(account.id)}
              onChange={() => toggle(account.id)}
            />
            <span className="account-check-main">
              <span className="account-check-title">
                {account.name || account.xa || account.username}
                <span className={`badge compact role-${account.role}`}>{ROLE_LABEL[account.role]}</span>
              </span>
              <span className="account-check-meta">
                {account.username} · {account.xa || "Chưa xác định xã"} · {account.tinh || "Chưa xác định tỉnh"}
              </span>
            </span>
          </label>
        ))}
        {!filtered.length && (
          <div className="empty">Không tìm thấy tài khoản phù hợp.</div>
        )}
      </div>
    </div>
  );
}
