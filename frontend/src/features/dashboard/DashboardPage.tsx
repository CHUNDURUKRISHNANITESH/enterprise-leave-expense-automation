
import { useEffect, useState } from "react";
import {
  getDashboardSummary,
  DashboardApiError,
  type DashboardSummary,
} from "../../services/dashboard";
import EmployeesPage from "../employees/EmployeesPage";
import "../../css/DashboardPage.css";
import LeaveManagementPage from "../leaves/LeaveManagementPage";
import ExpensesPage from "../expenses/ExpensesPage";
import ApprovalsPage from "../approvals/ApprovalsPage";
import ReimbursementsPage from "../reimbursements/ReimbursementsPage";
import AIPolicyAssistantPage from "../ai/AIPolicyAssistantPage";
import AnalyticsPage from "../analytics/AnalyticsPage";

interface DashboardPageProps {
  accessToken: string;
  onLogout: () => void;
}

type ActivePage =
  | "dashboard"
  | "employees"
  | "leaves"
  | "expenses"
  | "approvals"
  | "reimbursements"
  | "ai"
  | "analytics";
export default function DashboardPage({
  accessToken,
  onLogout,
}: DashboardPageProps) {
  const [activePage, setActivePage] =
    useState<ActivePage>("dashboard");

  const [summary, setSummary] =
    useState<DashboardSummary | null>(null);

  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [refreshKey, setRefreshKey] = useState(0);

  useEffect(() => {
    if (activePage !== "dashboard") return;

    const controller = new AbortController();

    async function loadDashboard() {
      setLoading(true);
      setError("");

      try {
        const data = await getDashboardSummary(
          accessToken,
          controller.signal
        );

        if (!controller.signal.aborted) {
          setSummary(data);
        }
      } catch (err) {
        if (controller.signal.aborted) return;

        if (err instanceof DashboardApiError) {
          if (err.status === 401) {
            onLogout();
            return;
          }

          setError(err.message);
        } else {
          setError("Unable to load dashboard statistics.");
        }
      } finally {
        if (!controller.signal.aborted) {
          setLoading(false);
        }
      }
    }

    loadDashboard();

    return () => controller.abort();
  }, [accessToken, onLogout, refreshKey, activePage]);

  const cards = summary
    ? [
        {
          label: "Total Employees",
          value: summary.total_employees,
        },
        {
          label: "Leave Requests",
          value: summary.total_leave_requests,
        },
        {
          label: "Expense Claims",
          value: summary.total_expense_claims,
        },
        {
          label: "Pending Approvals",
          value: summary.pending_approval_steps,
        },
        {
          label: "Pending Leave",
          value: summary.pending_leave_requests,
        },
        {
          label: "Reimbursements",
          value: summary.total_reimbursements,
        },
      ]
    : [];

  return (
    <div className="dashboard-shell">
      <aside className="dashboard-sidebar">
        <div className="dashboard-brand">
          <span className="dashboard-brand-icon">
            LE
          </span>

          <div>
            <strong>Leave & Expense</strong>
            <small>Enterprise Management</small>
          </div>
        </div>

        <nav
          className="dashboard-nav"
          aria-label="Main navigation"
        >
          <button
            type="button"
            className={`dashboard-nav-item ${
              activePage === "dashboard" ? "active" : ""
            }`}
            aria-current={
              activePage === "dashboard" ? "page" : undefined
            }
            onClick={() => setActivePage("dashboard")}
          >
            Dashboard
          </button>

          <button
            type="button"
            className={`dashboard-nav-item ${
              activePage === "employees" ? "active" : ""
            }`}
            aria-current={
              activePage === "employees" ? "page" : undefined
            }
            onClick={() => setActivePage("employees")}
          >
            Employees
          </button>

          <button
  type="button"
  className={`dashboard-nav-item ${
    activePage === "leaves" ? "active" : ""
  }`}
  aria-current={
    activePage === "leaves" ? "page" : undefined
  }
  onClick={() => setActivePage("leaves")}
>
  Leave Management
</button>

          <button type="button" className={`dashboard-nav-item ${activePage === "expenses" ? "active" : ""}`} onClick={()=>setActivePage("expenses")}>Expenses</button>

          <button type="button" className={`dashboard-nav-item ${activePage === "approvals" ? "active" : ""}`} onClick={()=>setActivePage("approvals")}>Approvals</button>

          <button type="button" className={`dashboard-nav-item ${activePage === "reimbursements" ? "active" : ""}`} onClick={()=>setActivePage("reimbursements")}>Reimbursements</button>

          <button type="button" className={`dashboard-nav-item ${activePage === "ai" ? "active" : ""}`} onClick={()=>setActivePage("ai")}>AI Policy Assistant</button>
<button
  type="button"
  className={`dashboard-nav-item ${
    activePage === "analytics" ? "active" : ""
  }`}
  aria-current={activePage === "analytics" ? "page" : undefined}
  onClick={() => setActivePage("analytics")}
>
  Analytics & Reports
</button>
        </nav>

        <button
          type="button"
          className="dashboard-logout"
          onClick={onLogout}
        >
          Logout
        </button>
      </aside>

      <main className="dashboard-main">
        {activePage === "employees" ? (
  <EmployeesPage
    accessToken={accessToken}
    onLogout={onLogout}
  />
) : activePage === "leaves" ? (
   <LeaveManagementPage
    accessToken={accessToken}
    onLogout={onLogout}
  />
) : activePage === "expenses" ? (
  <ExpensesPage accessToken={accessToken} onLogout={onLogout}/>
) : activePage === "approvals" ? (
  <ApprovalsPage accessToken={accessToken}/>
) : activePage === "reimbursements" ? (
  <ReimbursementsPage accessToken={accessToken}/>
) : activePage === "ai" ? (
  <AIPolicyAssistantPage accessToken={accessToken}/>
) : activePage === "analytics" ? (
  <AnalyticsPage
    accessToken={accessToken}
    onLogout={onLogout}
  />
) : (
          <>
            <header className="dashboard-topbar">
              <div>
                <span className="dashboard-eyebrow">
                  ENTERPRISE OVERVIEW
                </span>

                <h1>Dashboard</h1>

                <p>
                  Monitor your organization's leave and
                  expense workflows.
                </p>
              </div>

              <button
                type="button"
                className="dashboard-refresh"
                onClick={() =>
                  setRefreshKey((value) => value + 1)
                }
                disabled={loading}
              >
                Refresh Data
              </button>
            </header>

            {loading && (
              <p role="status">
                Loading dashboard statistics...
              </p>
            )}

            {error && (
              <div
                className="dashboard-error"
                role="alert"
              >
                {error}
              </div>
            )}

            {summary && (
              <>
                <section
                  className="dashboard-stats"
                  aria-label="Statistics"
                >
                  {cards.map((card) => (
                    <article
                      className="dashboard-stat-card"
                      key={card.label}
                    >
                      <p>{card.label}</p>

                      <strong>
                        {card.value.toLocaleString()}
                      </strong>

                      <span>
                        Live database statistics
                      </span>
                    </article>
                  ))}
                </section>

                <section className="dashboard-financials">
                  <article className="dashboard-panel">
                    <h2>Expense Totals</h2>

                    <p>Grouped by currency</p>

                    {Object.entries(
                      summary.total_expense_amounts_by_currency
                    ).map(([currency, amount]) => (
                      <div
                        className="dashboard-financial-row"
                        key={currency}
                      >
                        <span>{currency}</span>

                        <strong>
                          {Number(amount).toLocaleString(
                            undefined,
                            {
                              minimumFractionDigits: 2,
                              maximumFractionDigits: 2,
                            }
                          )}
                        </strong>
                      </div>
                    ))}
                  </article>

                  <article className="dashboard-panel">
                    <h2>Paid Reimbursements</h2>

                    <p>
                      Completed reimbursement payments
                    </p>

                    {Object.entries(
                      summary.paid_reimbursement_amounts_by_currency
                    ).map(([currency, amount]) => (
                      <div
                        className="dashboard-financial-row"
                        key={currency}
                      >
                        <span>{currency}</span>

                        <strong>
                          {Number(amount).toLocaleString(
                            undefined,
                            {
                              minimumFractionDigits: 2,
                              maximumFractionDigits: 2,
                            }
                          )}
                        </strong>
                      </div>
                    ))}
                  </article>
                </section>
              </>
            )}
          </>
        )}
      </main>
    </div>
  );
}
