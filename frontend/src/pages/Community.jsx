import { useState } from "react";
import { useTranslation } from "react-i18next";
import StatusTag from "../components/StatusTag";

// Sample-only data. There is no community backend yet (see README) — this
// gives the page a real shape to design and demo against. Swap for a
// GET /community/posts call once that endpoint exists; keep the same
// {id, verdict, pattern, quote, initials, handle, timeAgo, likes} shape.
const SAMPLE_POSTS = [
  {
    id: 1,
    verdict: "high_risk",
    pattern: "OTP request",
    quote:
      "\u201cUrgent: your MCB account will be suspended today. Verify now and reply with the OTP we just sent you.\u201d",
    initials: "R.B.",
    handle: "R.B. \u00b7 Rose Hill",
    timeAgo: "2 hours ago",
    likes: 14,
  },
  {
    id: 2,
    verdict: "high_risk",
    pattern: "Fake investment",
    quote:
      "\u201cDouble your money in 7 days \u2014 join our forex pool. Send Rs 5,000 to this MCB Juice number to start.\u201d",
    initials: "S.K.",
    handle: "S.K. \u00b7 Quatre Bornes",
    timeAgo: "5 hours ago",
    likes: 27,
  },
  {
    id: 3,
    verdict: "suspicious",
    pattern: "Revoked license",
    quote:
      "\u201cWhatsApp message from a \u2018licensed forex broker\u2019 \u2014 Klaro's registry check showed the license was surrendered in 2025.\u201d",
    initials: "M.A.",
    handle: "M.A. \u00b7 Vacoas",
    timeAgo: "1 day ago",
    likes: 9,
  },
  {
    id: 4,
    verdict: "high_risk",
    pattern: "Lookalike sender",
    quote:
      "\u201cName was one letter off from a real bank \u2014 easy to miss on a phone screen. Klaro flagged it as a near match, not a real one.\u201d",
    initials: "D.P.",
    handle: "D.P. \u00b7 Curepipe",
    timeAgo: "1 day ago",
    likes: 21,
  },
  {
    id: 5,
    verdict: "suspicious",
    pattern: "Job offer fee",
    quote:
      "\u201cCongratulations, you're hired! Pay a Rs 2,500 \u2018processing fee\u2019 to activate your remote job account.\u201d",
    initials: "K.N.",
    handle: "K.N. \u00b7 Flic en Flac",
    timeAgo: "2 days ago",
    likes: 6,
  },
  {
    id: 6,
    verdict: "high_risk",
    pattern: "Verified sender, risky ask",
    quote:
      "\u201cCame from a genuinely verified bank number, but it still asked for a card PIN by text \u2014 verified isn't the same as safe.\u201d",
    initials: "A.T.",
    handle: "A.T. \u00b7 Port Louis",
    timeAgo: "3 days ago",
    likes: 18,
  },
  {
    id: 7,
    verdict: "safe",
    pattern: "Genuine promo",
    quote:
      "\u201cAlmost reported this one \u2014 turned out to be a real, verified promo message from my own bank. Good to have it confirmed either way.\u201d",
    initials: "L.C.",
    handle: "L.C. \u00b7 Grand Baie",
    timeAgo: "4 days ago",
    likes: 11,
  },
];

function QuoteIcon() {
  return (
    <svg width="26" height="26" viewBox="0 0 22 22" aria-hidden="true" className="feed-card-quote-icon">
      <path
        fill="currentColor"
        d="M9 6.5C6.5 6.5 4.5 8.5 4.5 11v5H9v-5H6.7C6.7 9.6 7.7 8.6 9 8.6V6.5Zm8.5 0c-2.5 0-4.5 2-4.5 4.5v5h4.5v-5h-2.3c0-1.4 1-2.4 2.3-2.4V6.5Z"
      />
    </svg>
  );
}

const ACCENT_TONE = {
  safe: "safe",
  suspicious: "caution",
  high_risk: "risk",
};

function HeartIcon({ filled }) {
  return (
    <svg width="14" height="14" viewBox="0 0 22 22" aria-hidden="true">
      <path
        d="M11 18.4c-.3 0-.5-.1-.7-.3C7 15.2 3 12 3 8.3 3 5.9 4.9 4 7.3 4c1.4 0 2.7.6 3.7 1.7C12 4.6 13.3 4 14.7 4 17.1 4 19 5.9 19 8.3c0 3.7-4 6.9-7.3 9.8-.2.2-.5.3-.7.3Z"
        fill={filled ? "currentColor" : "none"}
        stroke="currentColor"
        strokeWidth={filled ? 0 : 1.6}
      />
    </svg>
  );
}

export default function Community() {
  const { t } = useTranslation();
  const [likes, setLikes] = useState(() =>
    Object.fromEntries(SAMPLE_POSTS.map((p) => [p.id, { liked: false, count: p.likes }]))
  );

  function toggleLike(id) {
    setLikes((prev) => {
      const current = prev[id];
      const liked = !current.liked;
      return { ...prev, [id]: { liked, count: current.count + (liked ? 1 : -1) } };
    });
  }

  return (
    <>
      <div className="page-head">
        <h1>{t("community.title")}</h1>
        <p>{t("community.intro")}</p>
      </div>

      <div className="community-feed-head">
        <h2>{t("community.feedTitle")}</h2>
        <p>{t("community.feedSubtitle")}</p>
      </div>

      <div className="community-sample-note">{t("community.sampleNote")}</div>

      <div className="feed-masonry">
        {SAMPLE_POSTS.map((post) => {
          const like = likes[post.id];
          return (
            <article key={post.id} className="record-sheet feed-card">
              <div className={"feed-card-accent " + (ACCENT_TONE[post.verdict] || "caution")}>
                <QuoteIcon />
                <span className="feed-card-pattern-label">{post.pattern}</span>
              </div>

              <div className="feed-card-body">
                <p className="feed-card-text">{post.quote}</p>
              </div>

              <div className="feed-card-meta">
                <div className="feed-avatar" aria-hidden="true">{post.initials}</div>
                <div className="feed-card-who">
                  <div className="feed-card-handle">{post.handle}</div>
                  <div className="feed-card-time">{post.timeAgo}</div>
                </div>
                <StatusTag verdict={post.verdict} />
              </div>

              <div className="feed-card-actions">
                <button
                  type="button"
                  className={"feed-like-btn" + (like.liked ? " liked" : "")}
                  onClick={() => toggleLike(post.id)}
                  aria-label={t("community.likeAria")}
                  aria-pressed={like.liked}
                >
                  <HeartIcon filled={like.liked} />
                  <span>{like.count}</span>
                </button>
              </div>
            </article>
          );
        })}
      </div>
    </>
  );
}
