import { createContext, useCallback, useContext, useEffect, useRef, useState } from "react";
import type { Facets } from "./types";

/** Tải dữ liệu theo `key`; đổi key thì bỏ kết quả cũ đang bay về (tránh ghi đè sai thứ tự). */
export function useAsync<T>(load: () => Promise<T>, key: string) {
  const [data, setData] = useState<T | null>(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);
  const seq = useRef(0);
  const loader = useRef(load);
  loader.current = load;

  const run = useCallback(() => {
    const id = ++seq.current;
    setLoading(true);
    setError("");
    loader.current()
      .then((value) => { if (id === seq.current) setData(value); })
      .catch((reason) => { if (id === seq.current) setError(reason instanceof Error ? reason.message : String(reason)); })
      .finally(() => { if (id === seq.current) setLoading(false); });
  }, []);

  useEffect(() => { run(); }, [key, run]);
  return { data, error, loading, reload: run };
}

export const FacetsContext = createContext<Facets | null>(null);

export function useFacets() {
  const facets = useContext(FacetsContext);
  const unitName = (userId?: string | null, fallback?: string | null) => {
    if (fallback) return fallback;
    const u = facets?.users.find((x) => x.userId === userId);
    return u?.name || u?.username || userId || "—";
  };
  const procLabel = (key?: string | null, fallback?: string | null) => {
    if (fallback) return fallback;
    return facets?.procedures.find((p) => p.key === key)?.label || key || "—";
  };
  return { facets, unitName, procLabel };
}
