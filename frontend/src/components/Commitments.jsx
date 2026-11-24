import { CheckCircle2, Globe2, Lock, Ticket } from "lucide-react";

const ITEMS = [
  {
    icon: Lock,
    title: "Privacy First",
    body: "We never ask for real passwords or OTPs. Every phishing exercise uses safe, simulated scenarios only.",
  },
  {
    icon: Ticket,
    title: "Free & Open Access",
    body: "Every lesson, quiz, poster, and certificate is free to use — no paywalls, no hidden fees.",
  },
  {
    icon: CheckCircle2,
    title: "Admin-Reviewed Content",
    body: "Every poster, infographic, film, and quiz is reviewed by an administrator before it goes live.",
  },
  {
    icon: Globe2,
    title: "Built for Everyday India",
    body: "Lessons and posters are written in plain language, in English and Hindi, for real everyday situations.",
  },
];

export default function Commitments() {
  return (
    <section id="about" className="bg-ivory py-16">
      <div className="mx-auto max-w-6xl px-4 text-center sm:px-6">
        <p className="text-sm font-bold uppercase tracking-widest text-maroon">Why trust CleanClick</p>
        <h2 className="font-display text-3xl text-peacock sm:text-4xl">Our Commitments</h2>
        <div className="mt-10 grid gap-6 sm:grid-cols-2 lg:grid-cols-4">
          {ITEMS.map(({ icon: Icon, title, body }) => (
            <article key={title} className="rounded-lg border border-gold/60 bg-white p-6 shadow-sm">
              <span className="mx-auto mb-3 flex h-14 w-14 items-center justify-center rounded-full border-2 border-gold bg-ivory">
                <Icon className="h-6 w-6 text-emerald" aria-hidden="true" />
              </span>
              <h3 className="mb-1 font-heading text-lg text-peacock">{title}</h3>
              <p className="text-sm text-ink/70">{body}</p>
            </article>
          ))}
        </div>
      </div>
    </section>
  );
}
