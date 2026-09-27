import { useState } from "react";
import Icon from "./Icon";

export default function CopyButton({ text, label = "Sao chép" }: { text: string; label?: string }) {
  const [done, setDone] = useState(false);
  async function copy(event: React.MouseEvent) {
    event.stopPropagation();
    try {
      await navigator.clipboard.writeText(text);
      setDone(true);
      window.setTimeout(() => setDone(false), 1500);
    } catch {
      // Clipboard có thể bị chặn khi chưa HTTPS — mã vẫn hiện trên màn để chép tay.
    }
  }
  return (
    <button className="btn btn--sm" type="button" onClick={copy} aria-live="polite">
      <Icon name={done ? "check" : "copy"} size={14} /> {done ? "Đã chép" : label}
    </button>
  );
}
