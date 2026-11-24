import { useState } from "react";
import { Sparkles } from "lucide-react";
import { appUrl } from "../config";
import RoyalDivider from "./RoyalDivider";
import TickerBorder from "./TickerBorder";

const TIPS = [
  "Your OTP is the final key to your money — never share it with anyone.",
  "A phishing mail is a staged trick. Pause, verify, then act.",
  "A reused password opens many doors to one thief. Keep every password unique.",
  "A cloned voice can wear a familiar face. Call back to verify first.",
  "An app that asks for more than it needs deserves a second look.",
];

function CounselBubble({ side, tip }) {
  if (!tip) return null;
  return (
    <div
      className={`absolute bottom-40 z-20 max-w-[210px] rounded-xl border-2 border-vermillion bg-ivory p-3 text-sm font-semibold leading-snug text-peacock shadow-xl sm:bottom-48 ${
        side === "left" ? "left-28 sm:left-40" : "right-28 sm:right-40"
      }`}
    >
      {tip}
    </div>
  );
}

function CourtFigure({ side, onSeekCounsel }) {
  const isRight = side === "right";
  return (
    <div
      className={`absolute bottom-10 z-20 hidden flex-col items-center gap-2 sm:flex ${
        isRight ? "right-1 md:right-3" : "left-1 md:left-3"
      }`}
    >
      <img
        src="/puppet-couple.svg"
        alt={isRight ? "" : "Illustrated royal Indian couple in traditional dress"}
        aria-hidden={isRight || undefined}
        className={`pointer-events-none w-32 drop-shadow-xl md:w-44 lg:w-52 ${isRight ? "-scale-x-100" : ""}`}
      />
      <button
        type="button"
        onClick={() => onSeekCounsel(side)}
        className="flex items-center gap-1 rounded-full border border-gold-dark bg-peacock px-4 py-2 text-xs font-bold text-ivory shadow-lg transition hover:brightness-110"
      >
        <Sparkles className="h-3.5 w-3.5 text-gold" /> Seek Counsel
      </button>
    </div>
  );
}

export default function Hero() {
  const [tip, setTip] = useState({ side: null, text: "" });

  const seekCounsel = (side) => {
    setTip({ side, text: TIPS[Math.floor(Math.random() * TIPS.length)] });
  };

  return (
    <section
      id="top"
      className="relative flex min-h-[620px] flex-col justify-center overflow-hidden bg-[radial-gradient(ellipse_at_50%_0%,theme(colors.ivory),theme(colors.sand)_85%)] pb-20 pt-16 sm:pt-20"
    >
      <div className="pointer-events-none absolute inset-3 rounded-2xl border border-gold sm:inset-4" aria-hidden="true" />

      <CourtFigure side="left" onSeekCounsel={seekCounsel} />
      <CourtFigure side="right" onSeekCounsel={seekCounsel} />
      <CounselBubble side={tip.side} tip={tip.side ? tip.text : null} />

      <div className="relative z-10 mx-auto max-w-2xl px-6 text-center">
        <h1 className="font-display text-4xl leading-tight text-maroon sm:text-5xl md:text-6xl">
          Rule Your
          <br />
          <span className="royal-text-gradient">Digital Kingdom</span>
        </h1>
        <p className="mt-4 text-lg font-bold text-maroon">Royal wisdom for everyday digital safety.</p>
        <p className="mx-auto mt-3 max-w-md text-muted-foreground text-ink/80">
          Learn through short lessons, quizzes, phishing simulations, and real cybercrime stories &mdash;
          practical protection, delivered with a touch of heritage.
        </p>
        <RoyalDivider />
        <div className="flex flex-wrap items-center justify-center gap-3">
          <a
            href={appUrl("/register")}
            className="rounded-md border border-maroon-dark bg-maroon px-6 py-3 font-bold text-ivory shadow-lg shadow-maroon/30 transition hover:brightness-110"
          >
            Get started
          </a>
          <a
            href={appUrl("/login")}
            className="rounded-md border border-peacock px-6 py-3 font-bold text-peacock transition hover:bg-peacock hover:text-ivory"
          >
            Sign in
          </a>
        </div>
      </div>

      <div className="absolute inset-x-0 bottom-0 z-10">
        <div className="h-3.5 bg-gradient-to-b from-gold-light to-gold-dark" />
        <TickerBorder />
      </div>
    </section>
  );
}
