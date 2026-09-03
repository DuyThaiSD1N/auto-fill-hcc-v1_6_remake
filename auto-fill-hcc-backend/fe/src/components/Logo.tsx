export default function Logo({ size = 40 }: { size?: number }) {
  return (
    <img
      src="/assets/icons/hcc-128.png"
      width={size}
      height={size}
      alt="Biểu tượng HCC"
      className="hcc-logo"
    />
  );
}
