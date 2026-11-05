import { useCallback, useEffect, useState } from "react";
import {
  createVoice,
  deleteVoice,
  getProviderVoices,
  getVoiceSettings,
  listVoices,
  updateAsrSettings,
  updateTtsSettings,
  updateVoice,
} from "../api";
import type {
  AsrSettings,
  ProviderVoicesResp,
  TtsSettings,
  User,
  Voice as VoiceItem,
  VoiceGender,
  VoiceRegion,
} from "../types";
import TopBar, { type View } from "../components/TopBar";

interface Props {
  user: User;
  onLogout: () => void;
  view: View;
  onNavigate: (v: View) => void;
}

// Ô số giữ dạng chuỗi trong form để cán bộ xoá trắng rồi gõ lại được; đổi sang số lúc lưu.
interface TtsForm {
  wsUrl: string;
  wsUrlHmong: string;
  defaultTempo: string;
  tempoMin: string;
  tempoMax: string;
  pitch: string;
}

interface AsrForm {
  grpcUri: string;
  grpcUriHmong: string;
  rate: string;
  silenceTimeout: string;
  speechTimeout: string;
  speechMax: string;
}

interface VoiceForm {
  editing: boolean;
  voiceId: string;
  name: string;
  gender: VoiceGender;
  region: VoiceRegion;
  ethnicity: string;
  sampleRate: number;
  enabled: boolean;
}

const EMPTY_VOICE: VoiceForm = {
  editing: false,
  voiceId: "",
  name: "",
  gender: "",
  region: "",
  ethnicity: "",
  sampleRate: 16000,
  enabled: true,
};

const SAMPLE_RATES = [8000, 16000, 22050, 24000];
const VOICE_ID_RE = /^[A-Za-z0-9._-]{1,80}$/;
const GENDER_LABEL: Record<VoiceGender, string> = { nam: "Nam", nu: "Nữ", "": "—" };
const REGION_LABEL: Record<VoiceRegion, string> = {
  bac: "Miền Bắc",
  trung: "Miền Trung",
  nam: "Miền Nam",
  "": "—",
};

const ttsToForm = (t: TtsSettings): TtsForm => ({
  wsUrl: t.wsUrl ?? "",
  wsUrlHmong: t.wsUrlHmong ?? "",
  defaultTempo: String(t.defaultTempo ?? ""),
  tempoMin: String(t.tempoMin ?? ""),
  tempoMax: String(t.tempoMax ?? ""),
  pitch: String(t.pitch ?? ""),
});

const asrToForm = (a: AsrSettings): AsrForm => ({
  grpcUri: a.grpcUri ?? "",
  grpcUriHmong: a.grpcUriHmong ?? "",
  rate: String(a.rate ?? 16000),
  silenceTimeout: String(a.silenceTimeout ?? ""),
  speechTimeout: String(a.speechTimeout ?? ""),
  speechMax: String(a.speechMax ?? ""),
});

// Ô số để trống → không gửi khoá đó, BE giữ giá trị đang lưu.
function num(value: string): number | undefined {
  const v = value.trim();
  if (!v) return undefined;
  const n = Number(v);
  return Number.isFinite(n) ? n : undefined;
}

const errMsg = (e: unknown, fallback: string) => (e instanceof Error ? e.message : fallback);

export default function Voice({ user, onLogout, view, onNavigate }: Props) {
  const [loadError, setLoadError] = useState("");
  const [tts, setTts] = useState<TtsSettings | null>(null);
  const [asr, setAsr] = useState<AsrSettings | null>(null);
  const [ttsForm, setTtsForm] = useState<TtsForm | null>(null);
  const [asrForm, setAsrForm] = useState<AsrForm | null>(null);
  const [ttsSaving, setTtsSaving] = useState(false);
  const [asrSaving, setAsrSaving] = useState(false);
  const [ttsMsg, setTtsMsg] = useState<{ ok: boolean; text: string } | null>(null);
  const [asrMsg, setAsrMsg] = useState<{ ok: boolean; text: string } | null>(null);

  const [voices, setVoices] = useState<VoiceItem[]>([]);
  const [voicesLoading, setVoicesLoading] = useState(true);
  const [voicesError, setVoicesError] = useState("");
  const [busyRow, setBusyRow] = useState("");
  const [form, setForm] = useState<VoiceForm | null>(null);
  const [formError, setFormError] = useState("");
  const [saving, setSaving] = useState(false);
  const [provider, setProvider] = useState<ProviderVoicesResp | null>(null);
  const [providerLoading, setProviderLoading] = useState(false);

  useEffect(() => {
    const controller = new AbortController();
    getVoiceSettings(controller.signal)
      .then((res) => {
        setTts(res.tts);
        setAsr(res.asr);
        setTtsForm(ttsToForm(res.tts));
        setAsrForm(asrToForm(res.asr));
      })
      .catch((e) => {
        if (e instanceof DOMException && e.name === "AbortError") return;
        setLoadError(errMsg(e, "Không tải được cấu hình giọng nói"));
      });
    return () => controller.abort();
  }, []);

  const loadVoices = useCallback(async () => {
    setVoicesLoading(true);
    setVoicesError("");
    try {
      const res = await listVoices();
      setVoices(res.voices);
    } catch (e) {
      setVoicesError(errMsg(e, "Không tải được danh sách giọng"));
    } finally {
      setVoicesLoading(false);
    }
  }, []);

  useEffect(() => {
    void loadVoices();
  }, [loadVoices]);

  async function saveTts(e: React.FormEvent) {
    e.preventDefault();
    if (!ttsForm) return;
    setTtsMsg(null);
    setTtsSaving(true);
    try {
      const res = await updateTtsSettings({
        wsUrl: ttsForm.wsUrl.trim(),
        wsUrlHmong: ttsForm.wsUrlHmong.trim(),
        defaultTempo: num(ttsForm.defaultTempo),
        tempoMin: num(ttsForm.tempoMin),
        tempoMax: num(ttsForm.tempoMax),
        pitch: num(ttsForm.pitch),
      });
      setTts(res.tts);
      setTtsForm(ttsToForm(res.tts));
      setTtsMsg({ ok: true, text: "Đã lưu cấu hình đọc." });
    } catch (err) {
      setTtsMsg({ ok: false, text: errMsg(err, "Lưu thất bại") });
    } finally {
      setTtsSaving(false);
    }
  }

  async function saveAsr(e: React.FormEvent) {
    e.preventDefault();
    if (!asrForm) return;
    setAsrMsg(null);
    setAsrSaving(true);
    try {
      const res = await updateAsrSettings({
        grpcUri: asrForm.grpcUri.trim(),
        grpcUriHmong: asrForm.grpcUriHmong.trim(),
        rate: num(asrForm.rate),
        silenceTimeout: num(asrForm.silenceTimeout),
        speechTimeout: num(asrForm.speechTimeout),
        speechMax: num(asrForm.speechMax),
      });
      setAsr(res.asr);
      setAsrForm(asrToForm(res.asr));
      setAsrMsg({ ok: true, text: "Đã lưu cấu hình nghe." });
    } catch (err) {
      setAsrMsg({ ok: false, text: errMsg(err, "Lưu thất bại") });
    } finally {
      setAsrSaving(false);
    }
  }

  async function toggleEnabled(v: VoiceItem) {
    setVoicesError("");
    setBusyRow(v.voiceId);
    try {
      const updated = await updateVoice(v.voiceId, { enabled: !v.enabled });
      setVoices((list) => list.map((x) => (x.voiceId === updated.voiceId ? updated : x)));
    } catch (e) {
      setVoicesError(errMsg(e, "Đổi trạng thái thất bại"));
    } finally {
      setBusyRow("");
    }
  }

  async function removeVoice(v: VoiceItem) {
    if (!window.confirm(`Xoá giọng "${v.name || v.voiceId}" (${v.voiceId}) khỏi danh sách?`)) return;
    setVoicesError("");
    setBusyRow(v.voiceId);
    try {
      await deleteVoice(v.voiceId);
      await loadVoices();
    } catch (e) {
      setVoicesError(errMsg(e, "Xoá thất bại"));
    } finally {
      setBusyRow("");
    }
  }

  function openCreate(prefill: Partial<VoiceForm> = {}) {
    setFormError("");
    setForm({ ...EMPTY_VOICE, ...prefill });
  }

  function openEdit(v: VoiceItem) {
    setFormError("");
    setForm({
      editing: true,
      voiceId: v.voiceId,
      name: v.name,
      gender: v.gender,
      region: v.region,
      ethnicity: v.ethnicity,
      sampleRate: v.sampleRate,
      enabled: v.enabled,
    });
  }

  async function submitVoice(e: React.FormEvent) {
    e.preventDefault();
    if (!form) return;
    setFormError("");
    const voiceId = form.voiceId.trim();
    const name = form.name.trim();
    if (!form.editing && !VOICE_ID_RE.test(voiceId)) {
      setFormError("Mã giọng chỉ gồm chữ không dấu, số, dấu chấm, gạch nối, gạch dưới (tối đa 80 ký tự).");
      return;
    }
    if (!name) {
      setFormError("Chưa nhập tên giọng.");
      return;
    }
    const body = {
      name,
      gender: form.gender,
      region: form.region,
      ethnicity: form.ethnicity.trim(),
      sampleRate: form.sampleRate,
      enabled: form.enabled,
    };
    setSaving(true);
    try {
      if (form.editing) await updateVoice(voiceId, body);
      else await createVoice({ voiceId, ...body });
      setForm(null);
      await loadVoices();
    } catch (err) {
      setFormError(errMsg(err, "Lưu thất bại"));
    } finally {
      setSaving(false);
    }
  }

  async function fetchProvider() {
    setProviderLoading(true);
    try {
      setProvider(await getProviderVoices());
    } catch (e) {
      setProvider({ ok: false, error: errMsg(e, "Không lấy được danh sách từ máy chủ giọng."), voices: [] });
    } finally {
      setProviderLoading(false);
    }
  }

  // Lọc thêm theo bảng hiện tại: vừa thêm một mã từ gợi ý thì mã đó biến khỏi danh sách ngay.
  const suggestions = (provider?.voices ?? []).filter(
    (p) => !p.inTable && !voices.some((v) => v.voiceId === p.id),
  );

  return (
    <div className="app">
      <TopBar user={user} view={view} onNavigate={onNavigate} onLogout={onLogout} />

      <div className="stats-head">
        <div>
          <h1 className="page-title">Giọng nói</h1>
          <p className="muted page-sub">
            Cấu hình máy chủ đọc (TTS), máy chủ nghe (ASR) và danh sách giọng cán bộ được chọn
          </p>
        </div>
      </div>

      {loadError && <div className="error bar">{loadError}</div>}

      <div className="voice-sections">
        <form className="report-card" onSubmit={saveTts}>
          <div className="report-section-head">
            <div>
              <h2>Cấu hình đọc (TTS)</h2>
              <p>Máy chủ chuyển chữ thành giọng nói cho trợ lý.</p>
            </div>
          </div>
          {!ttsForm || !tts ? (
            <p className="muted">{loadError ? "—" : "Đang tải…"}</p>
          ) : (
            <>
              <div className="voice-grid">
                <label className="voice-wide">
                  Địa chỉ máy chủ đọc
                  <input
                    value={ttsForm.wsUrl}
                    onChange={(e) => setTtsForm({ ...ttsForm, wsUrl: e.target.value })}
                    placeholder="wss://…"
                  />
                </label>
                <label className="voice-wide">
                  Địa chỉ máy chủ đọc tiếng Mông
                  <input
                    value={ttsForm.wsUrlHmong}
                    onChange={(e) => setTtsForm({ ...ttsForm, wsUrlHmong: e.target.value })}
                    placeholder="wss://…"
                  />
                  <small>Để trống = dùng chung.</small>
                </label>
                <label>
                  Tốc độ mặc định
                  <input
                    type="number"
                    step="0.05"
                    min="0.5"
                    max="2"
                    value={ttsForm.defaultTempo}
                    onChange={(e) => setTtsForm({ ...ttsForm, defaultTempo: e.target.value })}
                  />
                  <small>Từ 0.5 đến 2.0, nằm trong khoảng nhỏ nhất – lớn nhất.</small>
                </label>
                <label>
                  Cao độ (pitch)
                  <input
                    type="number"
                    step="1"
                    min="-99"
                    max="100"
                    value={ttsForm.pitch}
                    onChange={(e) => setTtsForm({ ...ttsForm, pitch: e.target.value })}
                  />
                </label>
                <label>
                  Tốc độ nhỏ nhất cán bộ được chọn
                  <input
                    type="number"
                    step="0.05"
                    min="0.5"
                    max="2"
                    value={ttsForm.tempoMin}
                    onChange={(e) => setTtsForm({ ...ttsForm, tempoMin: e.target.value })}
                  />
                </label>
                <label>
                  Tốc độ lớn nhất cán bộ được chọn
                  <input
                    type="number"
                    step="0.05"
                    min="0.5"
                    max="2"
                    value={ttsForm.tempoMax}
                    onChange={(e) => setTtsForm({ ...ttsForm, tempoMax: e.target.value })}
                  />
                </label>
              </div>

              <dl className="voice-info">
                <div>
                  <dt>Giọng dự phòng tiếng Việt</dt>
                  <dd className="mono">{tts.fallbackVoiceVi || "—"}</dd>
                </div>
                <div>
                  <dt>Giọng dự phòng tiếng Mông</dt>
                  <dd className="mono">{tts.fallbackVoiceHmong || "—"}</dd>
                </div>
                <div>
                  <dt>Khoá dịch vụ</dt>
                  <dd>
                    <span className={`badge ${tts.apiKeyConfigured ? "ok" : "warn"}`}>
                      {tts.apiKeyConfigured ? "Đã cấu hình" : "Chưa cấu hình"}
                    </span>{" "}
                    <span className="muted">(env)</span>
                  </dd>
                </div>
              </dl>
              <p className="form-hint">
                Giọng dự phòng cấu hình ở env TTS_VOICE / TTS_VOICE_HMONG, dùng khi cán bộ chưa chọn
                hoặc giọng đã chọn lỗi.
              </p>

              <div className="voice-actions report-feedback" aria-live="polite">
                <button className="btn-primary" type="submit" disabled={ttsSaving}>
                  {ttsSaving ? "Đang lưu…" : "Lưu cấu hình đọc"}
                </button>
                {ttsMsg && <div className={ttsMsg.ok ? "success" : "error"}>{ttsMsg.text}</div>}
              </div>
            </>
          )}
        </form>

        <form className="report-card" onSubmit={saveAsr}>
          <div className="report-section-head">
            <div>
              <h2>Cấu hình nghe (ASR)</h2>
              <p>Máy chủ nhận dạng giọng nói của người dân.</p>
            </div>
          </div>
          {!asrForm || !asr ? (
            <p className="muted">{loadError ? "—" : "Đang tải…"}</p>
          ) : (
            <>
              <div className="voice-grid">
                <label className="voice-wide">
                  Địa chỉ máy chủ nghe
                  <input
                    value={asrForm.grpcUri}
                    onChange={(e) => setAsrForm({ ...asrForm, grpcUri: e.target.value })}
                  />
                </label>
                <label className="voice-wide">
                  Địa chỉ máy chủ nghe tiếng Mông
                  <input
                    value={asrForm.grpcUriHmong}
                    onChange={(e) => setAsrForm({ ...asrForm, grpcUriHmong: e.target.value })}
                  />
                  <small>Để trống = dùng chung.</small>
                </label>
                <label>
                  Tần số thu âm
                  <select
                    value={asrForm.rate}
                    onChange={(e) => setAsrForm({ ...asrForm, rate: e.target.value })}
                  >
                    <option value="16000">16000 Hz</option>
                    <option value="8000">8000 Hz</option>
                  </select>
                </label>
                <label>
                  silence_timeout (giây)
                  <input
                    type="number"
                    step="1"
                    min="1"
                    max="60"
                    value={asrForm.silenceTimeout}
                    onChange={(e) => setAsrForm({ ...asrForm, silenceTimeout: e.target.value })}
                  />
                  <small>Số giây im lặng tối đa trước khi bắt đầu nói (1–60).</small>
                </label>
                <label>
                  speech_timeout (giây)
                  <input
                    type="number"
                    step="0.1"
                    min="0.3"
                    max="10"
                    value={asrForm.speechTimeout}
                    onChange={(e) => setAsrForm({ ...asrForm, speechTimeout: e.target.value })}
                  />
                  <small>Số giây ngừng nói thì coi là nói xong (0.3–10).</small>
                </label>
                <label>
                  speech_max (giây)
                  <input
                    type="number"
                    step="1"
                    min="5"
                    max="120"
                    value={asrForm.speechMax}
                    onChange={(e) => setAsrForm({ ...asrForm, speechMax: e.target.value })}
                  />
                  <small>Thời lượng tối đa một lượt nói (5–120).</small>
                </label>
              </div>

              <dl className="voice-info">
                <div>
                  <dt>Token</dt>
                  <dd>
                    <span className={`badge ${asr.tokenConfigured ? "ok" : "warn"}`}>
                      {asr.tokenConfigured ? "Đã cấu hình" : "Chưa cấu hình"}
                    </span>{" "}
                    <span className="muted">(env)</span>
                  </dd>
                </div>
              </dl>

              <div className="voice-actions report-feedback" aria-live="polite">
                <button className="btn-primary" type="submit" disabled={asrSaving}>
                  {asrSaving ? "Đang lưu…" : "Lưu cấu hình nghe"}
                </button>
                {asrMsg && <div className={asrMsg.ok ? "success" : "error"}>{asrMsg.text}</div>}
              </div>
            </>
          )}
        </form>

        <section className="report-card">
          <div className="report-section-head voice-list-head">
            <div>
              <h2>Danh sách giọng</h2>
              <p>Giọng đang bật sẽ hiện cho cán bộ chọn. Giọng có dân tộc H'Mông dùng khi đọc tiếng Mông.</p>
            </div>
            <div className="row-actions">
              <button className="ghost" onClick={() => void fetchProvider()} disabled={providerLoading}>
                {providerLoading ? "Đang lấy…" : "Lấy danh sách từ máy chủ giọng"}
              </button>
              <button className="btn-primary" onClick={() => openCreate()}>
                + Thêm giọng
              </button>
            </div>
          </div>

          {provider && (
            <div className="voice-provider">
              {!provider.ok ? (
                <div className="error">{provider.error || "Không lấy được danh sách từ máy chủ giọng."}</div>
              ) : suggestions.length === 0 ? (
                <p className="muted">Mọi giọng trên máy chủ giọng đã có trong danh sách.</p>
              ) : (
                <>
                  <p className="muted">Giọng trên máy chủ chưa có trong danh sách:</p>
                  <ul>
                    {suggestions.map((p) => (
                      <li key={p.id}>
                        <span className="mono">{p.id}</span>
                        {p.samplingRate ? <span className="muted"> · {p.samplingRate} Hz</span> : null}
                        <button
                          className="ghost sm"
                          onClick={() =>
                            openCreate({
                              voiceId: p.id,
                              region: p.suggestedRegion,
                            })
                          }
                        >
                          Thêm
                        </button>
                      </li>
                    ))}
                  </ul>
                </>
              )}
            </div>
          )}

          {voicesError && <div className="error bar">{voicesError}</div>}

          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>Mã giọng</th>
                  <th>Tên giọng</th>
                  <th>Giới tính</th>
                  <th>Vùng miền</th>
                  <th>Dân tộc</th>
                  <th className="center">Tần số (Hz)</th>
                  <th className="center">Bật</th>
                  <th className="center">Thao tác</th>
                </tr>
              </thead>
              <tbody>
                {voicesLoading && (
                  <tr>
                    <td colSpan={8} className="center muted">Đang tải…</td>
                  </tr>
                )}
                {!voicesLoading && voices.length === 0 && (
                  <tr>
                    <td colSpan={8} className="center muted">Chưa có giọng nào</td>
                  </tr>
                )}
                {!voicesLoading &&
                  voices.map((v) => (
                    <tr key={v.voiceId}>
                      <td className="mono">{v.voiceId}</td>
                      <td>{v.name || <span className="muted">—</span>}</td>
                      <td>{GENDER_LABEL[v.gender] ?? "—"}</td>
                      <td>{REGION_LABEL[v.region] ?? "—"}</td>
                      <td>{v.ethnicity || <span className="muted">—</span>}</td>
                      <td className="center">{v.sampleRate}</td>
                      <td className="center">
                        <input
                          type="checkbox"
                          className="voice-toggle"
                          checked={v.enabled}
                          disabled={busyRow === v.voiceId}
                          aria-label={v.enabled ? "Tắt giọng" : "Bật giọng"}
                          onChange={() => void toggleEnabled(v)}
                        />
                      </td>
                      <td className="center">
                        <div className="row-actions">
                          <button className="ghost sm" onClick={() => openEdit(v)}>
                            Sửa
                          </button>
                          <button
                            className="ghost sm danger"
                            disabled={busyRow === v.voiceId}
                            onClick={() => void removeVoice(v)}
                          >
                            Xoá
                          </button>
                        </div>
                      </td>
                    </tr>
                  ))}
              </tbody>
            </table>
          </div>
        </section>
      </div>

      {form && (
        <div className="modal-backdrop" onClick={() => !saving && setForm(null)}>
          <form className="modal-card" onClick={(e) => e.stopPropagation()} onSubmit={submitVoice}>
            <h2>{form.editing ? `Sửa giọng: ${form.voiceId}` : "Thêm giọng"}</h2>

            <label>
              Mã giọng
              <input
                value={form.voiceId}
                disabled={form.editing}
                autoFocus={!form.editing && !form.voiceId}
                onChange={(e) => setForm({ ...form, voiceId: e.target.value })}
                placeholder="vd: phuongnhi-north"
              />
            </label>

            <label>
              Tên giọng *
              <input
                value={form.name}
                autoFocus={form.editing || Boolean(form.voiceId)}
                onChange={(e) => setForm({ ...form, name: e.target.value })}
              />
            </label>

            <div className="form-row">
              <label>
                Giới tính
                <select
                  value={form.gender}
                  onChange={(e) => setForm({ ...form, gender: e.target.value as VoiceGender })}
                >
                  <option value="">—</option>
                  <option value="nam">Nam</option>
                  <option value="nu">Nữ</option>
                </select>
              </label>
              <label>
                Vùng miền
                <select
                  value={form.region}
                  onChange={(e) => setForm({ ...form, region: e.target.value as VoiceRegion })}
                >
                  <option value="">—</option>
                  <option value="bac">Miền Bắc</option>
                  <option value="trung">Miền Trung</option>
                  <option value="nam">Miền Nam</option>
                </select>
              </label>
            </div>

            <label>
              Dân tộc
              <input
                value={form.ethnicity}
                onChange={(e) => setForm({ ...form, ethnicity: e.target.value })}
                placeholder="để trống nếu không có; H'Mông = giọng tiếng Mông"
              />
            </label>

            <label>
              Tần số
              <select
                value={form.sampleRate}
                onChange={(e) => setForm({ ...form, sampleRate: Number(e.target.value) })}
              >
                {SAMPLE_RATES.map((r) => (
                  <option key={r} value={r}>{r} Hz</option>
                ))}
              </select>
            </label>

            {formError && <div className="error">{formError}</div>}

            <div className="modal-actions">
              <button type="button" className="ghost" onClick={() => setForm(null)} disabled={saving}>
                Hủy
              </button>
              <button type="submit" className="btn-primary" disabled={saving}>
                {saving ? "Đang lưu…" : form.editing ? "Lưu thay đổi" : "Thêm giọng"}
              </button>
            </div>
          </form>
        </div>
      )}
    </div>
  );
}
