
import { useEffect, useState } from "react";
import {
  getAnalytics,
  AnalyticsApiError,
  type AnalyticsEndpoint,
  type AnalyticsRecord,
} from "../../services/analytics";
import "../../css/AnalyticsPage.css";

interface AnalyticsPageProps {
  accessToken: string;
  onLogout: () => void;
}

const reports: {
  id: AnalyticsEndpoint;
  title: string;
  description: string;
}[] = [
  {
    id: "leave-utilization",
    title: "Leave Utilization",
    description: "Leave usage by department and country",
  },
  {
    id: "expenses",
    title: "Expense Analytics",
    description: "Expense trends and spending analysis",
  },
  {
    id: "approvals",
    title: "Approval Turnaround",
    description: "Approval processing performance",
  },
  {
    id: "reimbursements",
    title: "Reimbursements",
    description: "Reimbursement payment performance",
  },
];

function formatColumnName(name: string): string {
  return name
    .replace(/_/g, " ")
    .replace(/\b\w/g, (letter) => letter.toUpperCase());
}

export default function AnalyticsPage({
  accessToken,
  onLogout,
}: AnalyticsPageProps) {
  const [activeReport, setActiveReport] =
    useState<AnalyticsEndpoint>("leave-utilization");

  const [records, setRecords] = useState<AnalyticsRecord[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [refreshKey, setRefreshKey] = useState(0);

  useEffect(() => {
    const controller = new AbortController();

    async function loadAnalytics() {
      setLoading(true);
      setError("");
      setRecords([]);

      try {
        const data = await getAnalytics(
          accessToken,
          activeReport,
          controller.signal
        );

        if (!controller.signal.aborted) {
          setRecords(data);
        }
      } catch (err) {
        if (controller.signal.aborted) return;

        if (
          err instanceof AnalyticsApiError &&
          err.status === 401
        ) {
          onLogout();
          return;
        }

        setError(
          err instanceof Error
            ? err.message
            : "Unable to load analytics."
        );
      } finally {
        if (!controller.signal.aborted) {
          setLoading(false);
        }
      }
    }

    loadAnalytics();

    return () => controller.abort();
  }, [accessToken, activeReport, refreshKey, onLogout]);

  const currentReport = reports.find(
    (report) => report.id === activeReport
  );

  const columns =
    records.length > 0 ? Object.keys(records[0]) : [];

  return (
    <section className="analytics-page">
      <header className="analytics-header">
        <div>
          <span className="analytics-eyebrow">
            ENTERPRISE ANALYTICS
          </span>
          <h1>Analytics & Reports</h1>
          <p>
            Explore leave, expense, approval, and reimbursement
            performance using PostgreSQL analytics.
          </p>
        </div>

        <button
          type="button"
          className="analytics-refresh"
          onClick={() => setRefreshKey((value) => value + 1)}
          disabled={loading}
        >
          Refresh Data
        </button>
      </header>

      <div className="analytics-report-tabs">
        {reports.map((report) => (
          <button
            key={report.id}
            type="button"
            className={`analytics-report-tab ${
              activeReport === report.id ? "active" : ""
            }`}
            onClick={() => setActiveReport(report.id)}
            aria-pressed={activeReport === report.id}
          >
            {report.title}
          </button>
        ))}
      </div>

      <div className="analytics-report-panel">
        <div className="analytics-report-heading">
          <div>
            <h2>{currentReport?.title}</h2>
            <p>{currentReport?.description}</p>
          </div>

          {!loading && !error && (
            <span className="analytics-record-count">
              {records.length} records
            </span>
          )}
        </div>

        {loading && (
          <p role="status">Loading analytics data...</p>
        )}

        {error && (
          <div className="analytics-error" role="alert">
            {error}
          </div>
        )}

        {!loading && !error && records.length === 0 && (
          <p>No analytics records found.</p>
        )}

        {!loading && !error && records.length > 0 && (
          <div className="analytics-table-wrapper">
            <table className="analytics-table">
              <thead>
                <tr>
                  {columns.map((column) => (
                    <th key={column} scope="col">
                      {formatColumnName(column)}
                    </th>
                  ))}
                </tr>
              </thead>

              <tbody>
                {records.map((record, index) => (
                  <tr key={index}>
                    {columns.map((column) => (
                      <td key={column}>
                        {record[column] === null
                          ? "—"
                          : String(record[column])}
                      </td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </section>
  );
}
