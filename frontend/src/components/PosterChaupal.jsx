import { useApi } from "../hooks/useApi";
import Carousel from "./Carousel";
import RoyalDivider from "./RoyalDivider";

const TONE_CLASSES = {
  p1: "bg-peacock",
  p2: "bg-maroon",
  p3: "bg-emerald",
  p4: "bg-plum",
  p5: "bg-vermillion",
  p6: "bg-emerald-dark",
};

function PosterCard({ poster, lang }) {
  const copy = poster[lang];
  return (
    <article
      className={`relative flex-none w-64 snap-start rounded-lg border-2 border-gold-light/80 p-5 text-ivory shadow-xl ${
        TONE_CLASSES[poster.tone] ?? "bg-peacock"
      }`}
    >
      <span className="mb-2 block text-2xl" aria-hidden="true">
        {poster.icon}
      </span>
      <h3 className="mb-3 font-heading text-lg uppercase leading-snug" lang={lang === "hi" ? "hi" : "en"}>
        {copy.title}
      </h3>
      <ul className="list-disc space-y-1.5 pl-4 text-sm text-ivory/90">
        {copy.tips.map((tip) => (
          <li key={tip}>{tip}</li>
        ))}
      </ul>
    </article>
  );
}

export default function PosterChaupal() {
  const { data: posters, loading, error } = useApi("/api/posters");

  return (
    <section id="posters" className="bg-sand py-16">
      <div className="mx-auto max-w-6xl px-4 sm:px-6">
        <div className="text-center">
          <p className="text-sm font-bold uppercase tracking-widest text-maroon">Wisdom for your walls</p>
          <h2 className="font-display text-3xl text-peacock sm:text-4xl">Poster Chaupal</h2>
          <RoyalDivider />
          <p className="mx-auto mb-10 max-w-xl text-ink/70">
            Each poster stages one cyber-safety lesson as a small, familiar scene &mdash; easy to recall, easy to pass on.
          </p>
        </div>

        {loading && <p className="text-center text-ink/60">Loading posters&hellip;</p>}
        {error && <p className="text-center text-vermillion">Couldn't load posters right now.</p>}
        {!loading && !error && (!posters || posters.length === 0) && (
          <p className="text-center text-ink/60">No posters have been published yet.</p>
        )}

        {posters && posters.length > 0 && (
          <div className="space-y-10">
            <div>
              <h3 className="mb-3 font-heading text-xl text-peacock">
                English Poster <span className="text-vermillion">&bull;</span>
              </h3>
              <Carousel ariaLabel="English posters, scrollable">
                {posters.map((p) => (
                  <PosterCard key={`en-${p.id}`} poster={p} lang="en" />
                ))}
              </Carousel>
            </div>
            <div>
              <h3 className="mb-3 font-heading text-xl text-peacock">
                हिन्दी पोस्टर <span className="text-vermillion">&bull;</span>
              </h3>
              <Carousel ariaLabel="Hindi posters, scrollable">
                {posters.map((p) => (
                  <PosterCard key={`hi-${p.id}`} poster={p} lang="hi" />
                ))}
              </Carousel>
            </div>
          </div>
        )}
      </div>
    </section>
  );
}
