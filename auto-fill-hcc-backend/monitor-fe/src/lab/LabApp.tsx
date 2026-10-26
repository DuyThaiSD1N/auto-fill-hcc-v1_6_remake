import { useCallback, useEffect, useMemo, useRef, useState, type FormEvent } from "react";
import Icon from "../components/Icon";
import { PageLoading, Spinner } from "../components/Status";
import { LAB_AUTH_EXPIRED_EVENT, labSession, listProcedures, loginLab, validateLabSession, type BeProcedure, type LabUser } from "./api";
import { createBatch, importBatch, MAX_SETS, runKey, startBatch, type Batch, type DocSet, type LabRun, type RunnerHandle } from "./engine";
import { findLabProcedure, LAB_PROCEDURES } from "./procedures";
import Results from "./Results";
import Setup, { type SetupState } from "./Setup";

const THEME_KEY = "hcc_monitor_theme";
const PREFS_KEY = "hcc_lab_prefs";

function useTheme() {
  const [theme, setTheme] = useState<string>(() => {
    try { return localStorage.getItem(THEME_KEY) || ""; } catch { return ""; }
  });
  useEffect(() => {
    const root = document.documentElement;
    if (theme) root.dataset.theme = theme; else delete root.dataset.theme;
    try {
      if (theme) localStorage.setItem(THEME_KEY, theme); else localStorage.removeItem(THEME_KEY);
    } catch { /* storage bị chặn → chỉ áp dụng trong phiên */ }
  }, [theme]);
  const dark = theme === "dark" || (!theme && window.matchMedia("(prefers-color-scheme: dark)").matches);
  return { dark, toggle: () => setTheme(dark ? "light" : "dark") };
}

function Brand() {
  return (
    <div className="brand">
      <span className="brand__mark" aria-hidden="true"><span /><span /><span /><span /></span>
      <span className="brand__words"><strong>Kiểm thử</strong><span>Trợ lý nhân dân</span></span>
    </div>
  );
}

function LoginPage({ onSuccess }: { onSuccess: (user: LabUser) => void }) {
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!username.trim() || !password) return;
    setLoading(true);
    setError("");
    try {
      onSuccess(await loginLab(username.trim(), password));
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Không đăng nhập được. Thử lại.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <main id="main-content" className="login">
      <form className="login-card" onSubmit={submit}>
        <Brand />
        <p className="muted lab-login-hint">Đăng nhập bằng tài khoản trợ lý của đơn vị cần thử — Kính gửi, nơi đăng ký… điền theo xã/tỉnh của tài khoản, đúng như extension.</p>
        <label className="field">
          <span>Tên đăng nhập</span>
          <input className="input" autoComplete="username" autoFocus disabled={loading} value={username} onChange={(e) => setUsername(e.target.value)} />
        </label>
        <label className="field">
          <span>Mật khẩu</span>
          <span className="field__pw">
            <input className="input" autoComplete="current-password" disabled={loading} type={showPassword ? "text" : "password"}
                   value={password} onChange={(e) => setPassword(e.target.value)} />
            <button className="btn btn--icon btn--ghost" type="button" onClick={() => setShowPassword((v) => !v)}
                    aria-label={showPassword ? "Ẩn mật khẩu" : "Hiện mật khẩu"}>
              <Icon name={showPassword ? "eye-off" : "eye"} size={16} />
            </button>
          </span>
        </label>
        {error ? <div className="form-error" role="alert">{error}</div> : null}
        <button className="btn btn--primary" style={{ height: 38 }} type="submit" disabled={loading || !username.trim() || !password}>
          {loading ? <Spinner label="Đang đăng nhập" /> : "Đăng nhập"}
        </button>
      </form>
    </main>
  );
}

export default function LabApp() {
  const [auth, setAuth] = useState<"checking" | "signed-out" | "signed-in">("checking");
  const [user, setUser] = useState<LabUser | null>(labSession.user);

  const signOut = useCallback(() => {
    labSession.clear();
    setUser(null);
    setAuth("signed-out");
  }, []);

  useEffect(() => {
    let active = true;
    validateLabSession().then((u) => {
      if (!active) return;
      setUser(u);
      setAuth(u ? "signed-in" : "signed-out");
    });
    return () => { active = false; };
  }, []);

  useEffect(() => {
    window.addEventListener(LAB_AUTH_EXPIRED_EVENT, signOut);
    return () => window.removeEventListener(LAB_AUTH_EXPIRED_EVENT, signOut);
  }, [signOut]);

  if (auth === "checking") return <PageLoading label="Đang kiểm tra phiên…" />;
  if (auth === "signed-out" || !user) return <LoginPage onSuccess={(u) => { setUser(u); setAuth("signed-in"); }} />;
  return <Workbench user={user} onLogout={signOut} />;
}

const emptySet = (i: number): DocSet => ({ name: `Bộ ${i + 1}`, files: [], applicant: { name: "", id: "", birthday: "" } });

function loadPrefs(): Partial<SetupState> {
  try { return JSON.parse(localStorage.getItem(PREFS_KEY) || "{}") as Partial<SetupState>; } catch { return {}; }
}

function Workbench({ user, onLogout }: { user: LabUser; onLogout: () => void }) {
  const { dark, toggle } = useTheme();
  const [setup, setSetup] = useState<SetupState>(() => {
    const prefs = loadPrefs();
    return {
      procedure: findLabProcedure(prefs.procedure)?.key ?? LAB_PROCEDURES[0].key,
      setCount: prefs.setCount ?? 1,
      runCount: prefs.runCount ?? 3,
      attach: prefs.attach ?? true,
      split: prefs.split ?? false,
      variant: prefs.variant ?? "",
    };
  });
  const [sets, setSets] = useState<DocSet[]>(() => Array.from({ length: MAX_SETS }, (_, i) => emptySet(i)));
  const [beProcedures, setBeProcedures] = useState<Map<string, BeProcedure>>(new Map());
  const [batch, setBatch] = useState<Batch | null>(null);
  const [running, setRunning] = useState(false);
  const [importError, setImportError] = useState("");
  const runner = useRef<RunnerHandle | null>(null);

  useEffect(() => {
    try { localStorage.setItem(PREFS_KEY, JSON.stringify(setup)); } catch { /* bỏ qua */ }
  }, [setup]);

  useEffect(() => {
    listProcedures().then((list) => setBeProcedures(new Map(list.map((p) => [p.key, p])))).catch(() => undefined);
  }, []);

  useEffect(() => () => runner.current?.stop(), []);

  const proc = findLabProcedure(setup.procedure) ?? LAB_PROCEDURES[0];
  const label = beProcedures.get(proc.key)?.label || proc.label;
  const variant = proc.variants?.find((v) => v.value === setup.variant) ?? proc.variants?.[0];

  useEffect(() => {
    document.title = running ? `Đang chạy · ${label} — Kiểm thử` : "Kiểm thử — Trợ lý nhân dân";
  }, [running, label]);

  const updateRun = useCallback((run: LabRun) => {
    setBatch((b) => (b ? { ...b, runs: b.runs.map((r) => (runKey(r) === runKey(run) ? run : r)) } : b));
  }, []);

  function start() {
    if (running) return;
    if (batch && batch.runs.some((r) => r.status === "done") && !window.confirm("Chạy đợt mới sẽ thay kết quả đang xem. Muốn giữ thì bấm Huỷ rồi “Xuất JSON” trước.")) return;
    const active = sets.slice(0, setup.setCount);
    const next = createBatch(proc.key, label, user.name || user.username, {
      fill: true,
      attach: proc.attach && setup.attach,
      split: proc.attach && setup.split,
      variant: variant?.value ?? "",
    }, active, setup.runCount);
    setBatch(next);
    setRunning(true);
    const handle = startBatch(next, active, variant, updateRun);
    runner.current = handle;
    handle.done.finally(() => {
      if (runner.current === handle) runner.current = null;
      setRunning(false);
    });
  }

  async function onImport(file: File) {
    setImportError("");
    try {
      setBatch(await importBatch(file));
    } catch (reason) {
      setImportError(reason instanceof Error ? reason.message : String(reason));
    }
  }

  const ready = useMemo(() => sets.slice(0, setup.setCount).every((s) => s.files.length > 0), [sets, setup.setCount]);

  return (
    <div className="lab-shell">
      <header className="lab-top">
        <Brand />
        <span className="lab-top__title">Chạy nhiều bộ tài liệu × nhiều lần cho một thủ tục, so kết quả điền / đính kèm giữa các lần</span>
        <div className="topbar__right">
          <button className="btn btn--icon btn--ghost" type="button" onClick={toggle} aria-label={dark ? "Chuyển giao diện sáng" : "Chuyển giao diện tối"}>
            <Icon name={dark ? "sun" : "moon"} size={16} />
          </button>
          <span className="account" title={[user.username, user.xa, user.tinh].filter(Boolean).join(" · ")}>
            {user.name || user.username}{user.xa ? <small> · {user.xa}</small> : null}
          </span>
          <button className="btn btn--icon btn--ghost" type="button" onClick={() => { runner.current?.stop(); onLogout(); }} aria-label="Đăng xuất">
            <Icon name="logout" size={16} />
          </button>
        </div>
      </header>

      <main id="main-content" className="lab-main" tabIndex={-1}>
        <Setup
          state={setup}
          onState={(patch) => setSetup((s) => ({ ...s, ...patch }))}
          sets={sets}
          onSet={(i, patch) => setSets((list) => list.map((s, k) => (k === i ? { ...s, ...patch } : s)))}
          procedure={proc}
          hint={beProcedures.get(proc.key)?.uploadHint}
          beLabel={(key) => beProcedures.get(key)?.label}
          running={running}
          ready={ready}
          onStart={start}
          onStop={() => runner.current?.stop()}
          onImport={onImport}
          importError={importError}
        />
        {batch ? <Results key={batch.id} batch={batch} running={running} /> : null}
      </main>
    </div>
  );
}
