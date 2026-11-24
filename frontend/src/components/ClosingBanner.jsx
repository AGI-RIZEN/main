import { appUrl } from "../config";
import TickerBorder from "./TickerBorder";

export default function ClosingBanner() {
  return (
    <section className="relative overflow-hidden bg-gradient-to-br from-peacock to-maroon text-ivory">
      <TickerBorder />
      <div className="mx-auto flex max-w-5xl flex-col items-center gap-6 px-4 py-14 text-center sm:px-6 md:flex-row md:text-left">
        <img
          src="/puppet-couple.svg"
          alt=""
          aria-hidden="true"
          className="hidden w-32 shrink-0 drop-shadow-lg md:block lg:w-40"
        />
        <div className="max-w-xl">
          <p className="text-sm font-bold uppercase tracking-widest text-gold-light">The journey continues</p>
          <h2 className="mt-1 font-display text-3xl leading-snug sm:text-4xl">
            <span className="block text-gold-light">An Old Tradition</span>
            <span className="block text-white">A Whole New Stage</span>
          </h2>
          <p className="mt-4 text-ivory/85">
            Street smarts kept people safe long before the internet existed &mdash; noticing a trick, trusting
            instinct, asking twice. CleanClick brings that same instinct online, one lesson at a time.
          </p>
          <a
            href={appUrl("/register")}
            className="mt-5 inline-block rounded-md bg-ivory px-6 py-3 font-bold text-peacock-dark shadow-lg transition hover:brightness-95"
          >
            Begin your journey
          </a>
        </div>
        <img
          src="/puppet-couple.svg"
          alt=""
          aria-hidden="true"
          className="hidden w-32 shrink-0 -scale-x-100 drop-shadow-lg md:block lg:w-40"
        />
      </div>
      <TickerBorder />
    </section>
  );
}
