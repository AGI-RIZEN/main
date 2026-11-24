import { Play } from "lucide-react";
import { useApi } from "../hooks/useApi";
import Carousel from "./Carousel";
import RoyalDivider from "./RoyalDivider";

export default function EventGallery() {
  const { data: items, loading, error } = useApi("/api/events");

  return (
    <section id="events" className="bg-gradient-to-b from-emerald to-emerald-dark py-16 text-ivory">
      <div className="mx-auto max-w-6xl px-4 text-center sm:px-6">
        <p className="text-sm font-bold uppercase tracking-widest text-gold-light">From our events</p>
        <h2 className="font-display text-3xl sm:text-4xl">Event Gallery</h2>
        <RoyalDivider />

        {loading && <p className="text-ivory/70">Loading gallery&hellip;</p>}
        {error && <p className="text-gold-light">Couldn't load the gallery right now.</p>}
        {!loading && !error && (!items || items.length === 0) && (
          <p className="text-ivory/70">Event photos and videos will appear here once the team publishes them.</p>
        )}

        {items && items.length > 0 && (
          <Carousel ariaLabel="Event photos and videos, scrollable">
            {items.map((item) => (
              <article
                key={item.id}
                className="flex-none w-64 snap-start overflow-hidden rounded-lg bg-ivory text-left text-ink shadow-xl"
              >
                {item.type === "video" ? (
                  <a
                    href={item.video_url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="relative flex h-40 items-center justify-center bg-sand"
                  >
                    {item.image_url && (
                      <img src={item.image_url} alt="" className="absolute inset-0 h-full w-full object-cover" />
                    )}
                    <span className="relative z-10 flex h-12 w-12 items-center justify-center rounded-full bg-black/50 text-white">
                      <Play className="h-6 w-6" fill="currentColor" />
                    </span>
                  </a>
                ) : (
                  <img src={item.image_url} alt={item.title} className="h-40 w-full object-cover" />
                )}
                <div className="p-4">
                  <h3 className="mb-1 font-heading text-base text-peacock">{item.title}</h3>
                  {item.caption && <p className="line-clamp-2 text-sm text-ink/70">{item.caption}</p>}
                </div>
              </article>
            ))}
          </Carousel>
        )}
      </div>
    </section>
  );
}
