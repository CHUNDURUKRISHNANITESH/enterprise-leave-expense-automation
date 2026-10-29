
import { useCallback, useEffect, useState } from "react";
import LoginPage from "../features/auth/LoginPage";
import DashboardPage from "../features/dashboard/DashboardPage";
import type { TokenResponse } from "../services/auth";

export default function App() {
  const [session, setSession] = useState<TokenResponse | null>(null);

  const handleLogout = useCallback(() => {
    setSession(null);
  }, []);

  useEffect(() => {
    if (!session) return;

    const timeout = window.setTimeout(
      handleLogout,
      session.expires_in * 1000
    );

    return () => window.clearTimeout(timeout);
  }, [session, handleLogout]);

  if (!session) {
    return <LoginPage onLoginSuccess={setSession} />;
  }

  return (
    <DashboardPage
      accessToken={session.access_token}
      onLogout={handleLogout}
    />
  );
}
