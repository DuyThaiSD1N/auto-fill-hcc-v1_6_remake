// Con dấu tròn — logomark của app (KHÔNG phải bản sao con dấu hành chính thật). Chữ chạy
// cong quanh vành trên/dưới, ngôi sao vàng ở giữa. Dùng ở masthead và trang đăng nhập.
interface Props {
  size?: number;
  top?: string;
  bottom?: string;
  /** "gold": vàng trên nền tối (masthead/login). "ink": mực trên nền sáng (watermark). */
  tone?: "gold" | "ink";
  className?: string;
}

export default function Seal({
  size = 64,
  top = "TRỢ LÝ NHÂN DÂN",
  bottom = "HÀNH CHÍNH CÔNG",
  tone = "gold",
  className,
}: Props) {
  const stroke = tone === "gold" ? "var(--gilt)" : "var(--ink)";
  // id duy nhất để nhiều con dấu trên cùng trang không tranh textPath.
  const uid = `${top}${bottom}${size}`.replace(/[^a-zA-Z0-9]/g, "").slice(0, 24) || "seal";
  const rText = 41; // bán kính đường chạy chữ

  return (
    <svg
      className={className}
      width={size}
      height={size}
      viewBox="0 0 100 100"
      role="img"
      aria-label="Trợ lý nhân dân"
      style={{ color: stroke }}
    >
      <defs>
        {/* Cung trên: trái→phải qua đỉnh (chữ đọc xuôi). */}
        <path id={`arc-top-${uid}`} d={`M ${50 - rText},50 A ${rText},${rText} 0 0 1 ${50 + rText},50`} fill="none" />
        {/* Cung dưới: trái→phải qua đáy. */}
        <path id={`arc-bot-${uid}`} d={`M ${50 - rText},50 A ${rText},${rText} 0 0 0 ${50 + rText},50`} fill="none" />
      </defs>

      <circle cx="50" cy="50" r="47" fill="none" stroke="currentColor" strokeWidth="1.6" />
      <circle cx="50" cy="50" r="34" fill="none" stroke="currentColor" strokeWidth="1" opacity="0.5" />

      <text fontSize="8.5" fontWeight={700} letterSpacing="1.2" fill="currentColor">
        <textPath href={`#arc-top-${uid}`} startOffset="50%" textAnchor="middle">
          {top}
        </textPath>
      </text>
      <text fontSize="7" fontWeight={600} letterSpacing="1.4" fill="currentColor">
        <textPath href={`#arc-bot-${uid}`} startOffset="50%" textAnchor="middle">
          {bottom}
        </textPath>
      </text>

      {/* Ngôi sao 5 cánh ở tâm. */}
      <path
        transform="translate(50 51) scale(0.95)"
        d="M0,-15 L4.4,-4.6 L15.6,-4.6 L6.6,2.6 L9.9,13.4 L0,6.8 L-9.9,13.4 L-6.6,2.6 L-15.6,-4.6 L-4.4,-4.6 Z"
        fill="currentColor"
      />
      {/* Hai chấm ngăn cách trái/phải giữa cung trên và dưới. */}
      <circle cx={50 - rText} cy="50" r="1.5" fill="currentColor" />
      <circle cx={50 + rText} cy="50" r="1.5" fill="currentColor" />
    </svg>
  );
}
