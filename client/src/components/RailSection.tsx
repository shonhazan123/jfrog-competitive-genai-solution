import { useCallback, useEffect, useRef, useState } from "react";
import type { CSSProperties } from "react";
import { Link } from "react-router-dom";
import type { RailGroup } from "../config/railCopy";
import { RailCard } from "./RailCard";
import "./RailSection.css";

interface RailSectionProps {
  eyebrow: string;
  roomName: string;
  /** where "See all" and the trailing card lead (the room this rail previews). */
  roomPath: string;
  /** where an individual card leads; defaults to roomPath. Lets a rail preview
   *  one room (e.g. Competitors) while its cards open another (e.g. Signals). */
  cardPath?: string;
  groups: RailGroup[];
  testId?: string;
}

const CROSSFADE_MS = 140;

function prefersReducedMotion(): boolean {
  return (
    typeof window !== "undefined" &&
    typeof window.matchMedia === "function" &&
    window.matchMedia("(prefers-reduced-motion:reduce)").matches
  );
}

export function RailSection({
  eyebrow,
  roomName,
  roomPath,
  cardPath,
  groups,
  testId,
}: RailSectionProps) {
  const cardDestination = cardPath ?? roomPath;
  const railRef = useRef<HTMLDivElement>(null);
  const rafRef = useRef<number | null>(null);
  // After a segment click we optimistically set the active group; suppress
  // scroll-driven detection briefly so the clicked title isn't overridden by
  // the settling smooth-scroll (which may clamp short of the target near the end).
  const lockUntilRef = useRef(0);

  const [activeIndex, setActiveIndex] = useState(0);
  const [displayIndex, setDisplayIndex] = useState(0);
  const [titleVisible, setTitleVisible] = useState(true);
  const [centered, setCentered] = useState(false);

  // Crossfade the heading when the scrolled-to group changes.
  useEffect(() => {
    if (activeIndex === displayIndex) return;
    if (prefersReducedMotion()) {
      setDisplayIndex(activeIndex);
      return;
    }
    setTitleVisible(false);
    const t = setTimeout(() => {
      setDisplayIndex(activeIndex);
      setTitleVisible(true);
    }, CROSSFADE_MS);
    return () => clearTimeout(t);
  }, [activeIndex, displayIndex]);

  const currentGroup = useCallback(() => {
    const rail = railRef.current;
    if (!rail) return 0;
    const firsts = rail.querySelectorAll<HTMLElement>('[data-first="true"]');
    // At (or all but) the end, the trailing groups can never reach the left
    // edge, so snap to the last group once we've hit max scroll.
    const maxScroll = rail.scrollWidth - rail.clientWidth;
    if (maxScroll > 0 && rail.scrollLeft >= maxScroll - 4) {
      let last = 0;
      firsts.forEach((fc) => {
        last = Math.max(last, Number(fc.dataset.gi ?? 0));
      });
      return last;
    }
    // Otherwise the active group is the one occupying the viewport centre —
    // this lets every group (not just those reachable at the left edge) become
    // active as the rail scrolls.
    const probe = rail.scrollLeft + rail.clientWidth * 0.5;
    let gi = 0;
    firsts.forEach((fc) => {
      if (fc.offsetLeft <= probe) gi = Number(fc.dataset.gi ?? 0);
    });
    return gi;
  }, []);

  const syncCenter = useCallback(() => {
    const rail = railRef.current;
    if (!rail) return;
    setCentered(rail.scrollWidth <= rail.clientWidth + 2);
  }, []);

  // Scroll, wheel, and resize listeners on the rail.
  useEffect(() => {
    const rail = railRef.current;
    if (!rail) return;

    const handleScroll = () => {
      if (Date.now() < lockUntilRef.current) return;
      if (rafRef.current != null) return;
      rafRef.current = requestAnimationFrame(() => {
        rafRef.current = null;
        setActiveIndex(currentGroup());
      });
    };

    const handleWheel = (e: WheelEvent) => {
      if (Math.abs(e.deltaY) <= Math.abs(e.deltaX)) return;
      const max = rail.scrollWidth - rail.clientWidth;
      if (max <= 0) return;
      if (
        (e.deltaY < 0 && rail.scrollLeft > 0) ||
        (e.deltaY > 0 && rail.scrollLeft < max)
      ) {
        e.preventDefault();
        rail.scrollLeft += e.deltaY;
      }
    };

    rail.addEventListener("scroll", handleScroll, { passive: true });
    rail.addEventListener("wheel", handleWheel, { passive: false });
    window.addEventListener("resize", syncCenter);

    syncCenter();
    setActiveIndex(currentGroup());

    return () => {
      rail.removeEventListener("scroll", handleScroll);
      rail.removeEventListener("wheel", handleWheel);
      window.removeEventListener("resize", syncCenter);
      if (rafRef.current != null) cancelAnimationFrame(rafRef.current);
    };
  }, [currentGroup, syncCenter, groups]);

  const scrollToGroup = useCallback((gi: number) => {
    const rail = railRef.current;
    if (!rail) return;
    // Show the clicked group's title immediately, and hold it while the
    // smooth-scroll settles (it may clamp short of a trailing group).
    lockUntilRef.current = Date.now() + 700;
    setActiveIndex(gi);
    const target = rail.querySelector<HTMLElement>(
      `[data-first="true"][data-gi="${gi}"]`,
    );
    if (target) {
      rail.scrollTo({ left: Math.max(0, target.offsetLeft - 6), behavior: "smooth" });
    }
  }, []);

  if (groups.length === 0) return null;

  const active = groups[Math.min(activeIndex, groups.length - 1)];
  const shown = groups[Math.min(displayIndex, groups.length - 1)];

  const swatchStyle = { background: shown.accent } as CSSProperties;
  const titleWrapStyle = {
    "--grp-accent": shown.accent,
    opacity: titleVisible ? 1 : 0,
    transform: titleVisible ? "translateY(0)" : "translateY(8px)",
  } as CSSProperties;

  let flatIndex = 0;

  return (
    <section className="rail-section" data-testid={testId}>
      <div className="rail-section__eyebrow">
        <span className="rail-section__swatch" style={swatchStyle} aria-hidden="true" />
        <span>{eyebrow}</span>
      </div>

      <div className="rail-section__title-wrap" style={titleWrapStyle}>
        <div className="rail-section__title">{shown.title}</div>
        <div className="rail-section__explain">{shown.explain}</div>
      </div>

      <div className="rail-section__segs" role="tablist">
        {groups.map((g, gi) => {
          const segStyle = {
            "--seg-accent": g.accent,
            "--seg-wash": g.accent.replace(/^var\((--[a-z-]+)\)$/, "var($1-wash)"),
          } as CSSProperties;
          return (
            <button
              key={g.key}
              type="button"
              className="rail-seg"
              role="tab"
              aria-selected={gi === activeIndex}
              style={segStyle}
              onClick={() => scrollToGroup(gi)}
            >
              <span className="rail-seg__dot" aria-hidden="true" />
              {g.shortLabel}
            </button>
          );
        })}
      </div>

      <div className="rail-section__rail-wrap">
        <div className="rail-section__fade rail-section__fade--l" aria-hidden="true" />
        <div className="rail-section__fade rail-section__fade--r" aria-hidden="true" />
        <div
          ref={railRef}
          className={`rail-section__rail${centered ? " is-centered" : ""}`}
        >
          {groups.map((g, gi) =>
            g.cards.map((card, ci) => {
              flatIndex += 1;
              return (
                <RailCard
                  key={`${g.key}-${card.id}-${flatIndex}`}
                  card={card}
                  accent={g.accent}
                  cardPath={cardDestination}
                  groupIndex={gi}
                  isFirst={ci === 0}
                />
              );
            }),
          )}
          <Link to={roomPath} className="rail-card rail-card--more">
            <span className="rail-card--more__label">
              {groups.length} kinds of signal
            </span>
            <span className="rail-card--more__title">
              See everything in {roomName}
            </span>
            <span className="rail-card--more__go">Open {roomName} →</span>
          </Link>
        </div>
      </div>

      <div className="rail-section__seeall-row">
        <Link to={roomPath} className="rail-section__seeall">
          See all in {roomName} →
        </Link>
      </div>
    </section>
  );
}
