import { useApi } from "../hooks/useApi";
import RoyalDivider from "./RoyalDivider";

export default function Infographics() {
  const { data: items, loading, error } = useApi("/api/infographics");

  return (
    <section id="infographics" className="bg-plum py-16 text-ivory">
      <div className="mx-auto max-w-6xl px-4 text-center sm:px-6">
        <p className="text-sm font-bold uppercase tracking-widest text-gold-light">Cyber frauds, decoded</p>
        <h2 className="font-display text-3xl sm:text-4xl">Soch Samajh Chowk</h2>
        <RoyalDivider />
        <p className="mx-auto mb-10 max-w-xl text-ivory/80">
          Follow the thread of a scam &mdash; how it works, the red flags, and the smart move that breaks it.
        </p>

        {loading && <p className="text-ivory/70">Loading infographics&hellip;</p>}
        {error && <p className="text-gold-light">Couldn't load infographics right now.</p>}
        {!loading && !error && (!items || items.length === 0) && (
          <p className="text-ivory/70">No infographics have been published yet.</p>
        )}

        {items && items.length > 0 && (
          <div className="grid gap-6 pt-2 sm:grid-cols-2 lg:grid-cols-4">
            {items.map((item) => (
              <article key={item.id} className="rounded-lg border border-gold/50 bg-ivory p-5 text-left text-ink shadow-lg">
                <span className="mb-3 flex h-14 w-14 items-center justify-center rounded-full border-2 border-gold bg-sand text-2xl" aria-hidden="true">
                  {item.icon}
                </span>
                <h3 className="mb-1 font-heading text-lg text-peacock">{item.title}</h3>
                <p className="text-sm text-ink/75">{item.body}</p>
              </article>
            ))}
          </div>
        )}
      </div>
    </section>
  );
}
