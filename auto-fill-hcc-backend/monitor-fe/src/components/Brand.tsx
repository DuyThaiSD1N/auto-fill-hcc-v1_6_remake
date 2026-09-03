import Icon from "./Icon";

export default function Brand({ compact = false }: { compact?: boolean }) {
  return (
    <div className={`brand${compact ? " brand--compact" : ""}`}>
      <span className="brand__mark" aria-hidden="true">
        <Icon name="document" size={22} />
        <span className="brand__pulse" />
      </span>
      <span className="brand__words">
        <strong>Trợ lý hồ sơ</strong>
        <span>Monitor</span>
      </span>
    </div>
  );
}
