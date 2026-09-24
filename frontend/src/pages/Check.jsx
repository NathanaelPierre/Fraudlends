import { useEffect, useRef, useState } from "react";
import { Link } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { api } from "../api/client";
import VerdictStamp from "../components/VerdictStamp";
import RegistryRecord from "../components/RegistryRecord";
import EvidenceList from "../components/EvidenceList";
import { PENDING_MESSAGE_KEY } from "./LandingPage";

const EXAMPLE_MESSAGE =
  "Dear customer, your MCB internet banking access will be suspended today. Verify your account now and share the OTP sent to your phone to avoid suspension.";

const URL_PATTERN = /^https?:\/\/\S+$/i;

function PlusIcon() {
  return (
    <svg width="16" height="16" viewBox="0 0 22 22" aria-hidden="true">
      <path fill="currentColor" d="M10 4h2v6h6v2h-6v6h-2v-6H4v-2h6V4Z" />
    </svg>
  );
}

function SendIcon() {
  return (
    <svg width="16" height="16" viewBox="0 0 22 22" aria-hidden="true">
      <path fill="currentColor" d="M3.4 20.6 21 11 3.4 1.4 3 8l12 3-12 3 .4 6.6Z" />
    </svg>
  );
}

function ImageIcon() {
  return (
    <svg width="16" height="16" viewBox="0 0 22 22" aria-hidden="true">
      <path
        fill="currentColor"
        d="M4.5 3.5h13a1 1 0 0 1 1 1v13a1 1 0 0 1-1 1h-13a1 1 0 0 1-1-1v-13a1 1 0 0 1 1-1Zm1 2v9.4l3-3.6 2.4 2.9 2.9-3.8 3.7 4.6V5.5h-12Zm2.3 2.7a1.4 1.4 0 1 0 0-2.8 1.4 1.4 0 0 0 0 2.8Z"
      />
    </svg>
  );
}

function MicIcon() {
  return (
    <svg width="16" height="16" viewBox="0 0 22 22" aria-hidden="true">
      <path
        fill="currentColor"
        d="M11 14a3 3 0 0 0 3-3V6a3 3 0 0 0-6 0v5a3 3 0 0 0 3 3Zm5-3a5 5 0 0 1-10 0H4a7 7 0 0 0 6 6.9V20h2v-2.1A7 7 0 0 0 18 11h-2Z"
      />
    </svg>
  );
}

function CloseIcon() {
  return (
    <svg width="12" height="12" viewBox="0 0 22 22" aria-hidden="true">
      <path
        fill="none"
        stroke="currentColor"
        strokeWidth="2.2"
        strokeLinecap="round"
        d="m5 5 12 12M17 5 5 17"
      />
    </svg>
  );
}

export default function Check() {
  const { t } = useTranslation();
  const [messageText, setMessageText] = useState("");
  const [attachment, setAttachment] = useState(null); // { type: "image" | "audio", file }
  const [attachMenuOpen, setAttachMenuOpen] = useState(false);
  const [saveCheck, setSaveCheck] = useState(true);
  const [result, setResult] = useState(null);
  const [error, setError] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [stampKey, setStampKey] = useState(0);
  const imageInputRef = useRef(null);
  const audioInputRef = useRef(null);
  const composerRef = useRef(null);

  useEffect(() => {
    const pending = sessionStorage.getItem(PENDING_MESSAGE_KEY);
    if (pending) {
      setMessageText(pending);
      setAttachment(null);
      sessionStorage.removeItem(PENDING_MESSAGE_KEY);
    }
  }, []);

  useEffect(() => {
    if (!attachMenuOpen) return;
    function onOutside(e) {
      if (composerRef.current && !composerRef.current.contains(e.target)) {
        setAttachMenuOpen(false);
      }
    }
    document.addEventListener("mousedown", onOutside);
    return () => document.removeEventListener("mousedown", onOutside);
  }, [attachMenuOpen]);

  const trimmedText = messageText.trim();
  const isUrl = !attachment && URL_PATTERN.test(trimmedText);

  function canSubmit() {
    if (submitting) return false;
    if (attachment) return true;
    return !!trimmedText;
  }

  function clearAttachment() {
    setAttachment(null);
  }

  function onPickImage(e) {
    const file = e.target.files?.[0] || null;
    if (file) {
      setAttachment({ type: "image", file });
      setMessageText("");
    }
    setAttachMenuOpen(false);
    e.target.value = "";
  }

  function onPickAudio(e) {
    const file = e.target.files?.[0] || null;
    if (file) {
      setAttachment({ type: "audio", file });
      setMessageText("");
    }
    setAttachMenuOpen(false);
    e.target.value = "";
  }

  async function handleSubmit(e) {
    e.preventDefault();
    setError("");
    setSubmitting(true);
    try {
      let check;
      // Note: /checks/ does not take a language parameter at all — the
      // backend detects the MESSAGE's own language (see
      // app/language_detector.py) and explains the result in that
      // language, independent of whatever language this page's UI
      // happens to be displayed in right now. A French-speaking user
      // checking an English scam text correctly gets an English
      // explanation back, not a mismatched translation.
      if (attachment?.type === "image") {
        check = await api.createCheckFromImage(attachment.file, { saveCheck });
      } else if (attachment?.type === "audio") {
        check = await api.createCheckFromAudio(attachment.file, { saveCheck });
      } else if (isUrl) {
        check = await api.createCheck({ source_url: trimmedText, save_check: saveCheck });
      } else {
        check = await api.createCheck({ message_text: trimmedText, save_check: saveCheck });
      }

      setResult(check);
      setStampKey((k) => k + 1);
    } catch (err) {
      setResult(null);
      setError(err.message);
    } finally {
      setSubmitting(false);
    }
  }

  function fillExample() {
    setAttachment(null);
    setMessageText(EXAMPLE_MESSAGE);
  }

  const hint = attachment?.type === "image"
    ? t("check.imageHint")
    : attachment?.type === "audio"
      ? t("check.audioHint")
      : isUrl
        ? t("check.urlHint")
        : t("check.composerHint");

  return (
    <div className="check-page-center">
      <div className="page-head page-head-center">
        <h1>{t("check.title")}</h1>
        <p>{t("check.intro")}</p>
      </div>

      <div className="check-grid">
        <form className="record-sheet check-form" onSubmit={handleSubmit} noValidate>
          <div className="chat-composer" ref={composerRef}>
            {attachment && (
              <div className="chat-attachment-chip">
                {attachment.type === "image" ? <ImageIcon /> : <MicIcon />}
                <span className="chat-attachment-name">{attachment.file.name}</span>
                <button
                  type="button"
                  className="chat-attachment-remove"
                  onClick={clearAttachment}
                  aria-label={t("check.removeAttachment")}
                >
                  <CloseIcon />
                </button>
              </div>
            )}

            <div className="chat-composer-row">
              <div className="chat-plus-wrap">
                <button
                  type="button"
                  className={"chat-plus-btn" + (attachMenuOpen ? " active" : "")}
                  onClick={() => setAttachMenuOpen((o) => !o)}
                  aria-haspopup="true"
                  aria-expanded={attachMenuOpen}
                  aria-label={t("check.attachLabel")}
                >
                  <PlusIcon />
                </button>

                {attachMenuOpen && (
                  <div className="chat-attach-menu" role="menu">
                    <button
                      type="button"
                      role="menuitem"
                      className="chat-attach-option"
                      onClick={() => imageInputRef.current?.click()}
                    >
                      <ImageIcon />
                      <span>{t("check.modeImage")}</span>
                    </button>
                    <button
                      type="button"
                      role="menuitem"
                      className="chat-attach-option"
                      onClick={() => audioInputRef.current?.click()}
                    >
                      <MicIcon />
                      <span>{t("check.modeAudio")}</span>
                    </button>
                  </div>
                )}
              </div>

              <input
                type="text"
                className="chat-input"
                placeholder={t("check.askKlaro")}
                maxLength={5000}
                value={attachment ? "" : messageText}
                disabled={!!attachment}
                onChange={(e) => setMessageText(e.target.value)}
              />

              <button
                className={"chat-send-btn" + (submitting ? " is-loading" : "")}
                type="submit"
                disabled={!canSubmit()}
                title={submitting ? t("check.submitting") : t("check.submit")}
                aria-label={t("check.submit")}
              >
                <SendIcon />
              </button>
            </div>

            <input
              ref={imageInputRef}
              type="file"
              accept="image/*"
              hidden
              onChange={onPickImage}
            />
            <input
              ref={audioInputRef}
              type="file"
              accept="audio/*"
              hidden
              onChange={onPickAudio}
            />
          </div>

          <p className="chat-composer-hint">{hint}</p>

          <label className="checkbox-row">
            <input
              type="checkbox"
              checked={saveCheck}
              onChange={(e) => setSaveCheck(e.target.checked)}
            />
            <span>{t("check.saveCheckbox")}</span>
          </label>

          {error && <div className="banner banner-risk">{error}</div>}

          <div className="check-form-actions">
            <button className="btn btn-ghost" type="button" onClick={fillExample}>
              {t("check.tryExample")}
            </button>
          </div>
        </form>

        <div className="check-result">
          {!result && !submitting && (
            <div className="result-empty">
              <p>{t("check.resultEmpty")}</p>
            </div>
          )}

          {submitting && <div className="result-empty">{t("check.checkingAgainstRegistry")}</div>}

          {result && !submitting && (
            <div className="record-sheet result-card">
              <VerdictStamp verdict={result.overall_verdict} stampKey={stampKey} />
              <p className="result-explanation">{result.ai_explanation}</p>
              {result.repeat_sender_summary && (
                <p className="hint repeat-sender-note">{result.repeat_sender_summary}</p>
              )}
              <RegistryRecord check={result} />
              <EvidenceList evidence={result.evidence} />
              {result.id === 0 && (
                <p className="hint result-unsaved">{t("check.notSaved")}</p>
              )}
              {result.id !== 0 && (
                <Link className="btn btn-ghost" to={`/history/${result.id}`}>
                  {t("check.viewInHistory")}
                </Link>
              )}
            </div>
          )}
        </div>
      </div>

      <p className="responsible-use-note">{t("check.responsibleUse")}</p>
    </div>
  );
}
