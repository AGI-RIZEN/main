import { useEffect, useRef, useState } from "react";
import { ChevronLeft, ChevronRight } from "lucide-react";

export default function Carousel({ children, ariaLabel, autoAdvanceMs = 5000 }) {
  const trackRef = useRef(null);
  const [paused, setPaused] = useState(false);

  const step = () => {
    const track = trackRef.current;
    if (!track) return 260;
    const card = track.querySelector(":scope > *");
    return (card ? card.getBoundingClientRect().width : 260) + 16;
  };

  const scrollBy = (dir) => {
    trackRef.current?.scrollBy({ left: dir * step(), behavior: "smooth" });
  };

  useEffect(() => {
    const id = window.setInterval(() => {
      const track = trackRef.current;
      if (!track || paused) return;
      const atEnd = track.scrollLeft + track.clientWidth >= track.scrollWidth - 4;
      if (atEnd) track.scrollTo({ left: 0, behavior: "smooth" });
      else track.scrollBy({ left: step(), behavior: "smooth" });
    }, autoAdvanceMs);
    return () => window.clearInterval(id);
  }, [autoAdvanceMs, paused]);

  return (
    <div className="relative">
      <div className="mb-3 flex justify-end gap-2">
        <button
          type="button"
          onClick={() => scrollBy(-1)}
          aria-label="Scroll left"
          className="flex h-9 w-9 items-center justify-center rounded-full border border-gold bg-peacock text-ivory shadow transition hover:brightness-110"
        >
          <ChevronLeft className="h-5 w-5" />
        </button>
        <button
          type="button"
          onClick={() => scrollBy(1)}
          aria-label="Scroll right"
          className="flex h-9 w-9 items-center justify-center rounded-full border border-gold bg-peacock text-ivory shadow transition hover:brightness-110"
        >
          <ChevronRight className="h-5 w-5" />
        </button>
      </div>
      <div
        ref={trackRef}
        tabIndex={0}
        aria-label={ariaLabel}
        onMouseEnter={() => setPaused(true)}
        onMouseLeave={() => setPaused(false)}
        onFocus={() => setPaused(true)}
        onBlur={() => setPaused(false)}
        onTouchStart={() => setPaused(true)}
        onTouchEnd={() => setPaused(false)}
        className="flex snap-x snap-mandatory gap-4 overflow-x-auto pb-2 [scrollbar-width:thin]"
      >
        {children}
      </div>
    </div>
  );
}
