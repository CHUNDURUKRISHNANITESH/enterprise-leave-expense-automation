import { useState, type FormEvent, type ReactNode } from "react";
import { login, type TokenResponse } from "../../services/auth";
import "../../css/LoginPage.css";

type IconName = "clipboard" | "calendar" | "receipt" | "users" | "chart" | "mail" | "lock" | "eye" | "eye-off";

function Icon({ name, size = 24 }: { name: IconName; size?: number }) {
  const paths: Record<IconName, ReactNode> = {
    clipboard: <><rect x="6" y="4" width="12" height="17" rx="2"/><rect x="9" y="2" width="6" height="5" rx="1"/><path d="m9 14 2.5 2.5L16 12"/></>,
    calendar: <><rect x="3" y="5" width="18" height="16" rx="2"/><path d="M7 3v4M17 3v4M3 10h18M7 14h2M12 14h2M7 18h2"/></>,
    receipt: <><path d="M5 3h14v18l-3-2-3 2-3-2-3 2-2-2V3Z"/><path d="M9 8h6M9 12h6M9 16h3"/></>,
    users: <><circle cx="9" cy="8" r="3"/><path d="M3 20v-2a6 6 0 0 1 12 0v2H3ZM17 5a3 3 0 0 1 0 6M17 14a5 5 0 0 1 4 5v1h-4"/></>,
    chart: <><rect x="4" y="14" width="4" height="7" rx="1"/><rect x="10" y="9" width="4" height="12" rx="1"/><rect x="16" y="3" width="4" height="18" rx="1"/></>,
    mail: <><rect x="3" y="5" width="18" height="14" rx="2"/><path d="m4 7 8 6 8-6"/></>,
    lock: <><rect x="5" y="10" width="14" height="11" rx="2"/><path d="M8 10V7a4 4 0 0 1 8 0v3M12 14v3"/></>,
    eye: <><path d="M2 12s4-7 10-7 10 7 10 7-4 7-10 7S2 12 2 12Z"/><circle cx="12" cy="12" r="3"/></>,
    "eye-off": <><path d="m3 3 18 18M10.6 5.1A11 11 0 0 1 12 5c6 0 10 7 10 7a16 16 0 0 1-3.2 3.8M6.1 6.1C3.5 8.1 2 12 2 12s4 7 10 7c1.4 0 2.8-.4 4-1"/><path d="M10 10a3 3 0 0 0 4 4"/></>,
  };
  return <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">{paths[name]}</svg>;
}

const features: { icon: IconName; title: string; description: string }[] = [
  { icon: "calendar", title: "Leave Management", description: "Track balances, requests and approvals" },
  { icon: "receipt", title: "Expense Management", description: "Submit claims with policy validation" },
  { icon: "users", title: "Approval Workflows", description: "Route using rules and authority" },
  { icon: "chart", title: "AI Policy Assistant", description: "Get instant answers with evidence" },
];

export default function LoginPage({ onLoginSuccess }: { onLoginSuccess: (session: TokenResponse) => void }) {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (loading) return;
    setLoading(true);
    setError("");
    try {
      const session = await login({ email: email.trim(), password });
      setPassword("");
      onLoginSuccess(session);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unexpected error. Please try again.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <main className="auth-shell">
      <section className="brand-panel" aria-label="Platform features">
        <div className="brand-content">
          <div className="brand-identity"><span className="brand-mark"><Icon name="clipboard" size={34}/></span><div><strong>Leave &amp; Expense</strong><span>Management System</span></div></div>
          <h1>Simplify<br/>Workforce<br/>Workflows</h1>
          <p className="brand-tagline">Policy-aware approvals, transparent<br className="desktop-break"/> decisions, and auditable outcomes.</p>
          <div className="feature-list">{features.map(feature => <div className="feature" key={feature.title}><span className="feature-icon"><Icon name={feature.icon} size={29}/></span><div><strong>{feature.title}</strong><span>{feature.description}</span></div></div>)}</div>
        </div>
      </section>
      <section className="login-side" aria-label="Sign in">
        <div className="login-card">
          <div className="login-emblem"><Icon name="clipboard" size={54}/></div>
          <h2>Welcome back</h2>
          <p className="login-subtitle">Sign in to access your Leave &amp; Expense Management System</p>
          <form className="login-form" onSubmit={handleSubmit}>
            <label className="input-wrap" htmlFor="work-email"><Icon name="mail" size={24}/><span className="input-text"><span>Work email</span><input id="work-email" type="email" placeholder="employee@company.com" autoComplete="username" required value={email} onChange={event => setEmail(event.target.value)} disabled={loading}/></span></label>
            <label className="input-wrap" htmlFor="work-password"><Icon name="lock" size={24}/><span className="input-text"><span>Password</span><input id="work-password" type={showPassword ? "text" : "password"} placeholder="Enter your password" autoComplete="current-password" required value={password} onChange={event => setPassword(event.target.value)} disabled={loading}/></span><button className="password-toggle" type="button" aria-label={showPassword ? "Hide password" : "Show password"} aria-pressed={showPassword} onClick={() => setShowPassword(value => !value)}><Icon name={showPassword ? "eye" : "eye-off"} size={22}/></button></label>
            {error && <p className="login-error" role="alert">{error}</p>}
            <button className="login-button" type="submit" disabled={loading}>{loading ? "Signing in..." : "Login"}</button>
          </form>
          <div className="social-divider"><span>Or login with</span></div>
          <div className="social-buttons">
            <button type="button" disabled title="Google sign-in is not configured yet"><span className="google-g" aria-hidden="true">G</span> Google</button>
            <button type="button" disabled title="Microsoft sign-in is not configured yet"><span className="microsoft-logo" aria-hidden="true"><i/><i/><i/><i/></span> Microsoft</button>
          </div>
          <p className="social-note">Google and Microsoft sign-in coming soon</p>
        </div>
      </section>
    </main>
  );
}
