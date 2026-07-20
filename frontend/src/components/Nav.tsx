"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useEffect, useState } from "react";
import { UsageGuideFab, UsageGuidePanel } from "@/components/UsageGuidePanel";

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
  { href: "/autotrade", label: "自動取引" },
  { href: "/vpp", label: "VPP" },
  { href: "/dr", label: "DR" },
];

const OPEN_KEY = "gridleaf-usage-guide-open-v1";

export function Nav() {
  const pathname = usePathname();
  const [guideOpen, setGuideOpen] = useState(false);

  useEffect(() => {
    try {
      const v = localStorage.getItem(OPEN_KEY);
      if (v === null) {
        setGuideOpen(true);
        return;
      }
      setGuideOpen(v === "1");
    } catch {
      setGuideOpen(true);
    }
  }, []);

  const setOpen = (open: boolean) => {
    setGuideOpen(open);
    try {
      localStorage.setItem(OPEN_KEY, open ? "1" : "0");
    } catch {
      /* ignore */
    }
  };

  return (
    <>
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
          <button
            type="button"
            onClick={() => setOpen(true)}
            style={{
              border: "1px solid rgba(62,207,142,0.35)",
              background: "rgba(62,207,142,0.12)",
              color: "var(--ink)",
              borderRadius: 999,
              padding: "0.35rem 0.75rem",
              cursor: "pointer",
              font: "inherit",
              fontWeight: 600,
            }}
          >
            利用手順
          </button>
        </nav>
      </header>
      <UsageGuidePanel open={guideOpen} onClose={() => setOpen(false)} />
      {!guideOpen && <UsageGuideFab onClick={() => setOpen(true)} />}
    </>
  );
}
