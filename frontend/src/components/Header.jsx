import { useState } from "react";
import { Menu, Shield, X } from "lucide-react";
import { appUrl } from "../config";

const NAV_LINKS = [
  { label: "Home", href: "#top" },
  { label: "About", href: "#about" },
  { label: "Posters", href: "#posters" },
  { label: "Infographics", href: "#infographics" },
  { label: "Play Quiz", href: "#quiz" },
  { label: "Event Gallery", href: "#events" },
];

export default function Header() {
  const [open, setOpen] = useState(false);

  return (
    <header className="sticky top-0 z-50 border-b-4 border-gold bg-peacock shadow-lg shadow-black/10">
      <div className="mx-auto flex max-w-6xl items-center justify-between px-4 py-3 sm:px-6">
        <a href="#top" className="flex items-center gap-2 font-heading text-xl font-extrabold text-ivory">
          <Shield className="h-6 w-6 text-gold" aria-hidden="true" />
          CleanClick
        </a>

        <nav className="hidden items-center gap-1 md:flex" aria-label="Main navigation">
          {NAV_LINKS.map((link) => (
            <a
              key={link.label}
              href={link.href}
              className="rounded px-3 py-2 text-sm font-semibold text-ivory/90 transition hover:bg-white/10 hover:text-white"
            >
              {link.label}
            </a>
          ))}
          <a
            href={appUrl("/login")}
            className="ml-2 rounded-full border border-gold px-4 py-2 text-sm font-bold text-gold transition hover:bg-gold hover:text-peacock-dark"
          >
            Sign in
          </a>
        </nav>

        <button
          type="button"
          className="rounded p-2 text-ivory md:hidden"
          aria-label={open ? "Close menu" : "Open menu"}
          aria-expanded={open}
          onClick={() => setOpen((v) => !v)}
        >
          {open ? <X className="h-6 w-6" /> : <Menu className="h-6 w-6" />}
        </button>
      </div>

      {open && (
        <nav className="flex flex-col gap-1 border-t border-white/10 bg-peacock-dark px-4 py-3 md:hidden" aria-label="Mobile navigation">
          {NAV_LINKS.map((link) => (
            <a
              key={link.label}
              href={link.href}
              onClick={() => setOpen(false)}
              className="rounded px-3 py-2 text-sm font-semibold text-ivory/90 hover:bg-white/10"
            >
              {link.label}
            </a>
          ))}
          <a
            href={appUrl("/login")}
            className="mt-1 rounded-full border border-gold px-4 py-2 text-center text-sm font-bold text-gold"
          >
            Sign in
          </a>
        </nav>
      )}
    </header>
  );
}
