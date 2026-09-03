import type { SVGProps } from "react";

export type IconName =
  | "arrow-left"
  | "check"
  | "chevron-left"
  | "chevron-right"
  | "copy"
  | "document"
  | "external"
  | "eye"
  | "eye-off"
  | "file"
  | "logout"
  | "refresh"
  | "search"
  | "shield"
  | "user";

interface Props extends SVGProps<SVGSVGElement> {
  name: IconName;
  size?: number;
}

// Bộ icon nét đồng nhất, dùng currentColor để mọi trạng thái được điều khiển bằng design token.
export default function Icon({ name, size = 18, ...props }: Props) {
  const common = {
    width: size,
    height: size,
    viewBox: "0 0 24 24",
    fill: "none",
    stroke: "currentColor",
    strokeWidth: 1.8,
    strokeLinecap: "round" as const,
    strokeLinejoin: "round" as const,
    "aria-hidden": true,
  };

  const paths: Record<IconName, React.ReactNode> = {
    "arrow-left": <><path d="m15 18-6-6 6-6" /><path d="M9 12h10" /></>,
    check: <path d="m5 12 4 4L19 6" />,
    "chevron-left": <path d="m15 18-6-6 6-6" />,
    "chevron-right": <path d="m9 18 6-6-6-6" />,
    copy: <><rect width="14" height="14" x="8" y="8" rx="2" /><path d="M4 16c-1.1 0-2-.9-2-2V4c0-1.1.9-2 2-2h10c1.1 0 2 .9 2 2" /></>,
    document: <><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8Z" /><path d="M14 2v6h6" /><path d="M8 13h8M8 17h6" /></>,
    external: <><path d="M15 3h6v6" /><path d="m10 14 11-11" /><path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6" /></>,
    eye: <><path d="M2.1 12a10.5 10.5 0 0 1 19.8 0 10.5 10.5 0 0 1-19.8 0Z" /><circle cx="12" cy="12" r="3" /></>,
    "eye-off": <><path d="m2 2 20 20" /><path d="M6.7 6.7A10.3 10.3 0 0 0 2.1 12a10.5 10.5 0 0 0 15.2 5.3" /><path d="M10.7 10.7a2 2 0 0 0 2.6 2.6" /><path d="M14.2 5.2A10.2 10.2 0 0 1 21.9 12a10.4 10.4 0 0 1-1.6 2.8" /></>,
    file: <><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8Z" /><path d="M14 2v6h6" /></>,
    logout: <><path d="M10 17l5-5-5-5" /><path d="M15 12H3" /><path d="M15 3h4a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2h-4" /></>,
    refresh: <><path d="M20 11a8.1 8.1 0 0 0-15.5-2M4 4v5h5" /><path d="M4 13a8.1 8.1 0 0 0 15.5 2M20 20v-5h-5" /></>,
    search: <><circle cx="11" cy="11" r="7" /><path d="m20 20-4-4" /></>,
    shield: <><path d="M20 13c0 5-3.5 7.5-8 9-4.5-1.5-8-4-8-9V5l8-3 8 3Z" /><path d="m9 12 2 2 4-4" /></>,
    user: <><circle cx="12" cy="8" r="4" /><path d="M4 22a8 8 0 0 1 16 0" /></>,
  };

  return <svg {...common} {...props}>{paths[name]}</svg>;
}
