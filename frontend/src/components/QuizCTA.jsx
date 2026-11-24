import { Play } from "lucide-react";
import { appUrl } from "../config";

export default function QuizCTA() {
  return (
    <section id="quiz" className="bg-gradient-to-b from-peacock to-peacock-dark py-16 text-ivory">
      <div className="mx-auto max-w-xl px-4 text-center sm:px-6">
        <div className="relative rounded-2xl border-2 border-gold bg-white/5 px-6 py-10 sm:px-10">
          <div className="pointer-events-none absolute inset-2 rounded-xl border border-emerald" aria-hidden="true" />
          <p className="text-sm font-bold uppercase tracking-widest text-gold-light">Put your instincts to the test</p>
          <h2 className="mt-1 font-display text-3xl sm:text-4xl">Cyber Security Awareness Quiz</h2>
          <p className="mx-auto mt-4 max-w-sm text-ivory/80">
            Short, sharp knowledge checks on phishing, passwords, OTP safety, and more &mdash; pass and earn a
            certificate worth keeping.
          </p>
          <a
            href={appUrl("/quizzes")}
            className="mt-6 inline-flex items-center gap-2 rounded-full border border-gold-dark bg-peacock px-7 py-3 text-base font-bold text-ivory shadow-lg transition hover:brightness-110"
          >
            <Play className="h-5 w-5 text-gold" fill="currentColor" /> Play Quiz
          </a>
        </div>
      </div>
    </section>
  );
}
