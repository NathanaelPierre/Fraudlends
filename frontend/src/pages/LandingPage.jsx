import { useRef, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import CubeField from "../components/CubeField";

export const PENDING_MESSAGE_KEY = "cipherlab_pending_message";

const STEPS = [
  {
    n: "01",
    title: "Paste the message",
    body: "The SMS, email or WhatsApp text, plus whoever it says it's from — a bank, a wallet, a regulator.",
  },
  {
    n: "02",
    title: "We check the registry",
    body: "The claimed sender is matched against a snapshot of Mauritius' official financial institution registry.",
  },
  {
    n: "03",
    title: "You get a verdict, not a guess",
    body: "Verified, unverified, or high risk — with the registry evidence behind it, so you can see the reasoning.",
  },
];

const ABOUT_ITEMS = [
  {
    label: "Vision",
    body: "A straight, checkable answer in the seconds before you tap a link — not one more AI opinion to weigh.",
  },
  {
    label: "Tech stack",
    body: "A FastAPI backend, a fine-tuned local LLM for reading the message, checked against a Bank of Mauritius registry snapshot.",
  },
  {
    label: "Privacy",
    body: "Every check is disposable by default. Nothing reaches a database unless you choose to keep it.",
  },
];

const TECH_STACK = [
  {
    name: "FastAPI",
    body: "The backend that receives each message, runs it through the pipeline, and returns a verdict.",
  },
  {
    name: "Local QLoRA LLM",
    body: "A fine-tuned, locally-hosted model that reads the message and pulls out the claimed sender — nothing is sent to a third-party AI API.",
  },
  {
    name: "Fuzzy-matching algorithms",
    body: "The claimed sender is matched against registry entries even through misspellings, abbreviations, or unusual formatting.",
  },
  {
    name: "SQLite",
    body: "Lightweight, local storage — used only for checks you explicitly choose to save to your case log.",
  },
];

const COMPARISON = {
  before: {
    label: "Traditional AI guardrails",
    quote: "Looks like a 78% risk based on phrasing.",
    tags: ["Vague", "Unverified"],
  },
  after: {
    label: "CipherLab's approach",
    quote: "FACT: the sender \"Tranz Digital\" is not in the Bank of Mauritius official registry.",
    tags: ["Deterministic", "Explainable", "Zero-hallucination"],
  },
};

const PRIVACY_ITEMS = [
  {
    title: "Unauthenticated checks vanish",
    body: "If you check a message before creating an account, it's processed entirely in-memory and discarded once you have your verdict. Nothing is logged, tracked, or written to a database.",
  },
  {
    title: "Saving is always your choice",
    body: 'Create an account and CipherLab can keep a case log of your checks — but only the ones you choose to save. Leave "save this check" off for anything with an OTP, account number, or other sensitive detail.',
  },
  {
    title: "The registry, not your data, does the work",
    body: "A verdict comes from matching a claimed sender against a registry snapshot — not from profiling you or the device you're checking from.",
  },
];

const FAQ_ITEMS = [
  {
    q: "Does a registry match mean the message is genuine?",
    a: "No — it confirms the claimed sender's name is in the registry snapshot, not that this particular message came from them. Always verify through the institution's own official channels before acting.",
  },
  {
    q: 'Does a "not found" mean it\'s a scam?',
    a: "Not on its own. Many legitimate senders sit outside this registry. Treat it as one more data point, alongside common sense.",
  },
  {
    q: "Is my message stored?",
    a: 'Only if you leave "save this check" on. Turn it off for anything with an OTP, account number, or other sensitive detail — that result is never written to the database.',
  },
];

const QUICK_LINKS = [
  { id: "about", label: "About CipherLab", subs: ABOUT_ITEMS.map((a) => a.label) },
  { id: "comparison", label: "The difference", subs: [COMPARISON.before.label, COMPARISON.after.label] },
  {
    id: "threat-landscape",
    label: "The threat landscape",
    subs: ["Cyber-enabled impersonation scams", "Bank of Mauritius public notice — 23 Jan 2026"],
  },
  {
    id: "registry",
    label: "The registry",
    subs: ["Checked against the Bank of Mauritius registry", "Snapshot-based, not sentiment-based"],
  },
  { id: "privacy", label: "Privacy & security", subs: PRIVACY_ITEMS.map((p) => p.title) },
  { id: "team", label: "Team & tech stack", subs: TECH_STACK.map((t) => t.name) },
  { id: "faq", label: "FAQ", subs: FAQ_ITEMS.map((f) => f.q) },
];

function QuickLink({ id, label, subs, variant }) {
  return (
    <div className={`landing-quicklink${variant ? ` landing-quicklink-${variant}` : ""}`}>
      <a
        href={`#${id}`}
        className={
          variant === "hero"
            ? "btn btn-landing-ghost btn-landing-lg landing-quicklink-trigger"
            : "landing-quicklink-trigger"
        }
      >
        <span>{label}</span>
        <svg className="landing-quicklink-chevron" viewBox="0 0 24 24" fill="none" aria-hidden="true">
          <path
            d="M6 9l6 6 6-6"
            stroke="currentColor"
            strokeWidth="2"
            strokeLinecap="round"
            strokeLinejoin="round"
          />
        </svg>
      </a>
      <div className="landing-quicklink-panel">
        <ul>
          {subs.map((s) => (
            <li key={s}>
              <a href={`#${id}`}>{s}</a>
            </li>
          ))}
        </ul>
      </div>
    </div>
  );
}

export default function LandingPage() {
  const mark = "/cipher-mark-blue.png";
  const markFull = "/cipher-logo-full.png";

  const navigate = useNavigate();
  const [chatMessage, setChatMessage] = useState("");
  const [activeStep, setActiveStep] = useState(0);
  const chatInputRef = useRef(null);

  function handleChatSubmit(e) {
    e.preventDefault();
    const trimmed = chatMessage.trim();
    if (!trimmed) return;
    sessionStorage.setItem(PENDING_MESSAGE_KEY, trimmed);
    navigate("/signup");
  }

  function handleChatKeyDown(e) {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleChatSubmit(e);
    }
  }

  function autoGrow(e) {
    const el = e.target;
    el.style.height = "auto";
    el.style.height = `${Math.min(el.scrollHeight, 220)}px`;
  }

  return (
    <div className="landing-page">
      <div className="landing-hero">
        <img src={markFull} alt="" aria-hidden="true" className="landing-hero-mark" />
        <CubeField />
        <div className="landing-hero-fade" />

        <header className="landing-nav">
          <div className="landing-mark">
            <img src={mark} alt="CipherLab" className="landing-mark-glyph" />
            <span className="landing-mark-word">CipherLab</span>
          </div>
          <div className="landing-nav-actions">
            <Link to="/login" className="btn btn-landing-ghost">
              Log in
            </Link>
            <Link to="/signup" className="btn btn-landing-solid">
              Get started
            </Link>
          </div>
        </header>

        <div className="landing-hero-content">
          <h1>
            Spot the Warning
            <br />
            Signs Before You Pay
          </h1>
          <p className="landing-hero-sub">
            Before you tap a link or share an OTP, check the sender it claims to be against
            Mauritius' official financial institution registry — a straight answer, not an
            AI guess.
          </p>
          <div className="landing-hero-actions">
            <a href="#message-check" className="btn btn-landing-solid btn-landing-lg">
              Talk to Klaro
            </a>
            <QuickLink
              id="how-it-works"
              label="How it works"
              subs={STEPS.map((s) => `${s.n}. ${s.title}`)}
              variant="hero"
            />
          </div>

          <div className="landing-quicklinks">
            {QUICK_LINKS.map((q) => (
              <QuickLink key={q.id} {...q} />
            ))}
          </div>
        </div>
      </div>

      <section id="message-check" className="landing-section landing-chat-section">
        <div className="landing-section-head landing-section-head-center">
          <span className="landing-eyebrow">Try it now</span>
          <h2>Paste a message. We'll tell you what we find.</h2>
          <p className="landing-chat-sub">
            Drop in the SMS, email, or WhatsApp text below — we'll take it from there.
          </p>
        </div>

        <form className="landing-chatbox" onSubmit={handleChatSubmit}>
          <textarea
            ref={chatInputRef}
            className="landing-chatbox-input"
            placeholder="Paste the message you want checked…"
            rows={1}
            value={chatMessage}
            onChange={(e) => {
              setChatMessage(e.target.value);
              autoGrow(e);
            }}
            onKeyDown={handleChatKeyDown}
          />
          <button
            type="submit"
            className="landing-chatbox-send"
            aria-label="Check this message"
            disabled={!chatMessage.trim()}
          >
            <svg viewBox="0 0 24 24" fill="none" aria-hidden="true">
              <path
                d="M12 19V5M12 5L5 12M12 5l7 7"
                stroke="currentColor"
                strokeWidth="2"
                strokeLinecap="round"
                strokeLinejoin="round"
              />
            </svg>
          </button>
        </form>
        <p className="landing-chatbox-hint">
          Free to try — create an account to see the verdict and evidence behind it.
        </p>
      </section>

      <section id="about" className="landing-section landing-section-alt">
        <div className="landing-section-head">
          <span className="landing-eyebrow">About CipherLab</span>
          <h2>Why we built it this way</h2>
        </div>
        <div className="landing-about-grid">
          {ABOUT_ITEMS.map((item) => (
            <div className="landing-about-item" key={item.label}>
              <h3>{item.label}</h3>
              <p>{item.body}</p>
            </div>
          ))}
        </div>
      </section>

      <section id="comparison" className="landing-section">
        <div className="landing-section-head">
          <span className="landing-eyebrow">The difference</span>
          <h2>A verdict you can check, not a score you have to trust</h2>
        </div>
        <div className="landing-compare">
          <div className="landing-compare-card is-before">
            <span className="landing-compare-label">{COMPARISON.before.label}</span>
            <p className="landing-compare-quote">"{COMPARISON.before.quote}"</p>
            <div className="landing-compare-tags">
              {COMPARISON.before.tags.map((t) => (
                <span key={t}>{t}</span>
              ))}
            </div>
          </div>
          <div className="landing-compare-card is-after">
            <span className="landing-compare-label">{COMPARISON.after.label}</span>
            <p className="landing-compare-quote">"{COMPARISON.after.quote}"</p>
            <div className="landing-compare-tags">
              {COMPARISON.after.tags.map((t) => (
                <span key={t}>{t}</span>
              ))}
            </div>
          </div>
        </div>
      </section>

      <section id="how-it-works" className="landing-section">
        <div className="landing-section-head">
          <span className="landing-eyebrow">How it works</span>
          <h2>Three steps, no black box</h2>
          <span className="landing-section-badge">Works on SMS, email, or WhatsApp text</span>
        </div>
        <div className="landing-steps-hover">
          <ul className="landing-steps-list">
            {STEPS.map((s, i) => (
              <li
                key={s.n}
                className={`landing-steps-list-item${i === activeStep ? " is-active" : ""}`}
                onMouseEnter={() => setActiveStep(i)}
                onFocus={() => setActiveStep(i)}
                onClick={() => setActiveStep(i)}
                tabIndex={0}
              >
                <span className="landing-step-n">{s.n}</span>
                <h3>{s.title}</h3>
                <svg className="landing-steps-list-arrow" viewBox="0 0 24 24" fill="none" aria-hidden="true">
                  <path
                    d="M5 12h14M13 6l6 6-6 6"
                    stroke="currentColor"
                    strokeWidth="2"
                    strokeLinecap="round"
                    strokeLinejoin="round"
                  />
                </svg>
              </li>
            ))}
          </ul>
          <div className="landing-steps-panel">
            {STEPS.map((s, i) => (
              <div
                key={s.n}
                className={`landing-steps-panel-card${i === activeStep ? " is-active" : ""}`}
              >
                <span className="landing-step-n">{s.n}</span>
                <h3>{s.title}</h3>
                <p>{s.body}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      <section id="threat-landscape" className="landing-section landing-section-alt">
        <div className="landing-threat-grid">
          <div>
            <span className="landing-eyebrow">The threat landscape</span>
            <h2>This isn't a hypothetical problem</h2>
            <p className="landing-registry-copy">
              Cyber-enabled impersonation scams sent over WhatsApp and SMS are now among the
              most commonly reported forms of financial crime in Mauritius — messages that
              borrow a bank's name, logo, and urgency to get someone to click a link or read
              out an OTP.
            </p>
            <p className="landing-registry-copy">
              Regulators are responding directly. On 23 January 2026, the Bank of Mauritius
              issued a public notice warning that an entity calling itself "Tranz Digital
              Bank" was presenting itself online as a licensed digital bank, despite not
              being licensed or regulated by the Bank at all — precisely the kind of claim
              CipherLab is built to check in seconds.
            </p>
          </div>
          <div className="landing-notice-card">
            <span className="landing-notice-tag">Public notice</span>
            <span className="landing-notice-date">Bank of Mauritius — 23 January 2026</span>
            <p>
              "Tranz Digital Bank" is neither licensed nor regulated by the Bank of Mauritius
              as a digital bank. The public was advised to verify licensing status before
              engaging with any entity claiming to be a regulated bank.
            </p>
          </div>
        </div>
      </section>

      <section id="registry" className="landing-section">
        <div className="landing-section-head">
          <span className="landing-eyebrow">The registry</span>
          <h2>Verification, not vibes</h2>
          <span className="landing-section-badge">Checked against the Bank of Mauritius registry</span>
        </div>
        <p className="landing-registry-copy">
          Most scam checkers score a message by how it "feels." CipherLab starts from a
          dated snapshot of Mauritius' official financial institution registry and checks
          whether the sender a message claims to be from is actually in it. A match is
          evidence. A miss is evidence too — either way, you get the record behind the
          verdict, not just a color.
        </p>
      </section>

      <section id="privacy" className="landing-section landing-section-alt">
        <div className="landing-section-head">
          <span className="landing-eyebrow">Privacy &amp; security</span>
          <h2>No storage by default</h2>
          <span className="landing-section-badge">Nothing stored unless you choose to save it</span>
        </div>
        <div className="landing-privacy-grid">
          {PRIVACY_ITEMS.map((item) => (
            <div className="landing-privacy-item" key={item.title}>
              <h3>{item.title}</h3>
              <p>{item.body}</p>
            </div>
          ))}
        </div>
      </section>

      <section id="team" className="landing-section">
        <div className="landing-section-head">
          <span className="landing-eyebrow">Team &amp; tech stack</span>
          <h2>What's actually running under the hood</h2>
        </div>
        <p className="landing-registry-copy">
          CipherLab is built by a small team focused on financial-crime prevention in
          Mauritius, working from the Bank of Mauritius' public list of licensed
          institutions rather than any proprietary or closed data source.
        </p>
        <div className="landing-tech-grid">
          {TECH_STACK.map((t) => (
            <div className="landing-tech-item" key={t.name}>
              <h3>{t.name}</h3>
              <p>{t.body}</p>
            </div>
          ))}
        </div>
      </section>

      <section id="faq" className="landing-section">
        <div className="landing-section-head">
          <span className="landing-eyebrow">FAQ</span>
          <h2>Before you start</h2>
        </div>
        <div className="landing-faq">
          {FAQ_ITEMS.map((item) => (
            <div key={item.q}>
              <h3>{item.q}</h3>
              <p>{item.a}</p>
            </div>
          ))}
        </div>
      </section>

      <section className="landing-cta">
        <h2>Ready to check your first message?</h2>
        <Link to="/signup" className="btn btn-landing-solid btn-landing-lg">
          Get started
        </Link>
      </section>

      <footer className="landing-footer">
        <span>CipherLab</span>
        <span>Built on the Bank of Mauritius registry snapshot.</span>
      </footer>
    </div>
  );
}
