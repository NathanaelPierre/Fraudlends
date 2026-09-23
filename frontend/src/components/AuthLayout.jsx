export default function AuthLayout({ eyebrow, title, children, footer }) {
  const mark = "/cipher-mark-blue.png";

  return (
    <div className="auth-shell">
      <div className="auth-card record-sheet">
        <div className="auth-mark">
          <img src={mark} alt="CipherLab" className="folder-nav-mark-glyph" />
          <div>
            <div className="folder-nav-title">CipherLab</div>
            <div className="folder-nav-sub">Mauritius registry check</div>
          </div>
        </div>
        {eyebrow && <div className="auth-eyebrow">{eyebrow}</div>}
        <h1 className="auth-title">{title}</h1>
        <div className="auth-body">{children}</div>
        {footer && <div className="auth-footer">{footer}</div>}
      </div>
    </div>
  );
}
