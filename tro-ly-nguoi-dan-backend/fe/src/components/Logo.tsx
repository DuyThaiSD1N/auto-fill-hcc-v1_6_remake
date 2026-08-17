// Emblem "hành chính công": công sở cổ điển (mái + hàng cột + bậc thềm) trên nền huy hiệu
// xanh. SVG inline — không phụ thuộc asset ngoài, hiển thị offline, scale theo `size`.
// CỐ Ý không dùng Quốc huy để tránh giả mạo dấu hiệu cơ quan nhà nước.
export default function Logo({ size = 40 }: { size?: number }) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 48 48"
      fill="none"
      role="img"
      aria-label="Hành chính công"
    >
      <defs>
        <linearGradient id="hccLogoGradient" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0" stopColor="#2b7cf0" />
          <stop offset="1" stopColor="#1858c0" />
        </linearGradient>
      </defs>
      <rect x="2" y="2" width="44" height="44" rx="12" fill="url(#hccLogoGradient)" />
      {/* mái (fronton) */}
      <path d="M24 11 L38 19 L10 19 Z" fill="#fff" />
      {/* thanh đỡ dưới mái */}
      <rect x="10" y="20.5" width="28" height="2.4" rx="1.2" fill="#fff" />
      {/* 4 cột trụ, đối xứng quanh tâm x=24 */}
      <g fill="#fff">
        <rect x="15.2" y="24" width="2.6" height="8" />
        <rect x="20.2" y="24" width="2.6" height="8" />
        <rect x="25.2" y="24" width="2.6" height="8" />
        <rect x="30.2" y="24" width="2.6" height="8" />
      </g>
      {/* bậc thềm */}
      <rect x="10" y="33" width="28" height="2.8" rx="1.4" fill="#fff" />
    </svg>
  );
}
