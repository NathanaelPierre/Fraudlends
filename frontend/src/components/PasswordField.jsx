import { useState } from "react";

export default function PasswordField({
  id,
  label,
  value,
  onChange,
  autoComplete = "new-password",
  required = true,
  minLength,
  hint,
  error,
}) {
  const [visible, setVisible] = useState(false);

  return (
    <div className="field">
      <label htmlFor={id}>{label}</label>
      <div className="password-input">
        <input
          id={id}
          type={visible ? "text" : "password"}
          autoComplete={autoComplete}
          required={required}
          minLength={minLength}
          value={value}
          onChange={onChange}
          className={error ? "field-error" : ""}
        />
        <button
          type="button"
          className="password-toggle"
          onClick={() => setVisible((v) => !v)}
          aria-label={visible ? "Hide password" : "Show password"}
          aria-pressed={visible}
          title={visible ? "Hide password" : "Show password"}
        >
          {visible ? (
            <svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
              <path d="M3 3l18 18" />
              <path d="M10.58 10.58a2 2 0 0 0 2.83 2.83" />
              <path d="M9.36 5.11A9.9 9.9 0 0 1 12 4.8c5.5 0 9.5 4.2 10.5 7.2a11.6 11.6 0 0 1-2.1 3.5M6.6 6.6C4.4 8.1 2.9 10.2 1.5 12c1 3 5 7.2 10.5 7.2 1.5 0 2.86-.3 4.06-.83" />
            </svg>
          ) : (
            <svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
              <path d="M1.5 12S5.5 4.8 12 4.8 22.5 12 22.5 12 18.5 19.2 12 19.2 1.5 12 1.5 12Z" />
              <circle cx="12" cy="12" r="3.2" />
            </svg>
          )}
        </button>
      </div>
      {hint && !error && <span className="hint">{hint}</span>}
      {error && <span className="error-text">{error}</span>}
    </div>
  );
}
