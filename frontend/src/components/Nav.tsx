"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

const links = [
  { href: "/", label: "ダッシュボード" },
  { href: "/forecast/generation", label: "発電量" },
  { href: "/forecast/demand", label: "需要" },
  { href: "/forecast/market-price", label: "市場価格" },
  { href: "/forecast/fuel-price", label: "燃料価格" },
  { href: "/risk", label: "リスク" },
  { href: "/simulate", label: "収益シミュ" },
  { href: "/optimize", label: "蓄電池最適化" },
  { href: "/trading", label: "市場最適化" },
  { href: "/vpp", label: "VPP" },
  { href: "/dr", label: "DR" },
];

export function Nav() {
  const pathname = usePathname();
  return (
    <header className="nav">
      <div className="brand">
        Grid<span>Leaf</span>
      </div>
      <nav className="nav-links">
        {links.map((l) => (
          <Link
            key={l.href}
            href={l.href}
            className={pathname === l.href ? "active" : undefined}
          >
            {l.label}
          </Link>
        ))}
      </nav>
    </header>
  );
}
