
import { useEffect, useState } from "react";
import {
  LeaveApiError,
  listLeaveRequests,
  submitLeaveRequest,
  type LeaveRequest,
  type LeaveStatus,
} from "../../services/leaves";
import "../../css/LeaveManagementPage.css";
import CreateLeaveRequestForm from "./CreateLeaveRequestForm";

interface LeaveManagementPageProps {
  accessToken: string;
  onLogout: () => void;
}

const PAGE_SIZE = 20;

export default function LeaveManagementPage({
  accessToken,
  onLogout,
}: LeaveManagementPageProps) {
  const [submitting, setSubmitting] = useState(false);
  const [requests, setRequests] = useState<LeaveRequest[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [page, setPage] = useState(0);
  const [selectedRequest, setSelectedRequest] =
    useState<LeaveRequest | null>(null);
  const [statusFilter, setStatusFilter] =
    useState<LeaveStatus | "">("");
  const [refreshKey, setRefreshKey] = useState(0);
const [showCreateForm, setShowCreateForm] = useState(false);

  useEffect(() => {
    const controller = new AbortController();

    async function loadRequests() {
      setLoading(true);
      setError("");

      try {
        const data = await listLeaveRequests(
          accessToken,
          {
            offset: page * PAGE_SIZE,
            limit: PAGE_SIZE,
            ...(statusFilter ? { status: statusFilter } : {}),
          },
          controller.signal
        );

        if (!controller.signal.aborted) {
          setRequests(data);
        }
      } catch (err) {
        if (controller.signal.aborted) return;

        if (err instanceof LeaveApiError) {
          if (err.status === 401) {
            onLogout();
            return;
          }

          setError(err.message);
        } else {
          setError("Unable to load leave requests.");
        }
      } finally {
        if (!controller.signal.aborted) {
          setLoading(false);
        }
      }
    }

    void loadRequests();

    return () => controller.abort();
  }, [accessToken, onLogout, page, refreshKey, statusFilter]);

  return (
    <section className="leaves-page">
      {/* Page Header */}
      <header className="leaves-header">
        <div>
          <span className="leaves-eyebrow">
            WORKFORCE OPERATIONS
          </span>

          <h1>Leave Management</h1>

          <p>
            View employee leave requests and track their
            approval status.
          </p>
        </div>

        <div className="leaves-header-actions">
  <button
    type="button"
    className="leaves-create-button"
    onClick={() => {
      setShowCreateForm(true);
      setSelectedRequest(null);
    }}
  >
    + Create Leave Request
  </button>

  <button
    type="button"
    className="leaves-refresh"
    disabled={loading}
    onClick={() => setRefreshKey((value) => value + 1)}
  >
    Refresh Requests
  </button>
</div>
      </header>

{showCreateForm && (
  <CreateLeaveRequestForm
    accessToken={accessToken}
    onLogout={onLogout}
    onCancel={() => setShowCreateForm(false)}
    onCreated={() => {
      setShowCreateForm(false);
      setSelectedRequest(null);
      setStatusFilter("");
      setPage(0);
      setRefreshKey((value) => value + 1);
    }}
  />
)}

      {/* Leave Requests Panel */}
      <div className="leaves-panel">
        {/* Status Filter */}
        <div className="leaves-filters">
          <label htmlFor="leave-status-filter">
            Filter by Status
          </label>

          <select
            id="leave-status-filter"
            value={statusFilter}
            onChange={(event) => {
              setStatusFilter(
                event.target.value as LeaveStatus | ""
              );
              setPage(0);
              setSelectedRequest(null);
            }}
          >
            <option value="">All Statuses</option>
            <option value="DRAFT">Draft</option>
            <option value="SUBMITTED">Submitted</option>
            <option value="PENDING_APPROVAL">
              Pending Approval
            </option>
            <option value="NEEDS_REVIEW">Needs Review</option>
            <option value="APPROVED">Approved</option>
            <option value="REJECTED">Rejected</option>
            <option value="CANCELLED">Cancelled</option>
          </select>
        </div>

        {/* Panel Heading */}
        <div className="leaves-panel-heading">
          <h2>Leave Requests</h2>
          <span>{requests.length} shown</span>
        </div>

        {/* Loading */}
        {loading && (
          <p role="status">
            Loading leave requests...
          </p>
        )}

        {/* Error */}
        {error && (
          <div className="leaves-error" role="alert">
            {error}
          </div>
        )}

        {/* Empty State */}
        {!loading && !error && requests.length === 0 && (
          <p className="leaves-empty">
            No leave requests found.
          </p>
        )}

        {/* Leave Requests Table */}
        {!loading && !error && requests.length > 0 && (
          <div className="leaves-table-wrapper">
            <table className="leaves-table">
              <thead>
                <tr>
                  <th>Request ID</th>
                  <th>Employee ID</th>
                  <th>Policy ID</th>
                  <th>Start Date</th>
                  <th>End Date</th>
                  <th>Days</th>
                  <th>Status</th>
                  <th>Actions</th>
                </tr>
              </thead>

              <tbody>
                {requests.map((request) => (
                  <tr key={request.id}>
                    <td>{request.id}</td>
                    <td>{request.employee_id}</td>
                    <td>{request.leave_policy_id}</td>
                    <td>{request.start_date}</td>
                    <td>{request.end_date}</td>
                    <td>{request.requested_days}</td>

                    <td>
                      <span className="leaves-status">
                        {request.status.replace(/_/g, " ")}
                      </span>
                    </td>

                    <td>
                      <button
                        type="button"
                        className="leaves-view-button"
                        onClick={() =>
                          setSelectedRequest(request)
                        }
                      >
                        View Details
                      </button>
                      {request.status === "DRAFT" && (
                        <button type="button" disabled={submitting} onClick={async () => {
                          if (!window.confirm("Submit this leave request for approval?")) return;
                          setSubmitting(true); setError("");
                          try { await submitLeaveRequest(accessToken, request.id); setSelectedRequest(null); setRefreshKey(v => v + 1); }
                          catch (err) { if (err instanceof LeaveApiError && err.status === 401) onLogout(); else setError(err instanceof Error ? err.message : "Unable to submit leave request."); }
                          finally { setSubmitting(false); }
                        }}>Submit Draft</button>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}

        {/* Pagination */}
        <div className="leaves-pagination">
          <button
            type="button"
            disabled={loading || page === 0}
            onClick={() => {
              setPage((value) =>
                Math.max(0, value - 1)
              );
              setSelectedRequest(null);
            }}
          >
            Previous
          </button>

          <span>Page {page + 1}</span>

          <button
            type="button"
            disabled={
              loading || requests.length < PAGE_SIZE
            }
            onClick={() => {
              setPage((value) => value + 1);
              setSelectedRequest(null);
            }}
          >
            Next
          </button>
        </div>
      </div>

      {/* Leave Request Details Panel */}
      {selectedRequest && (
        <section
          className="leaves-details"
          aria-label="Leave request details"
        >
          <div className="leaves-details-header">
            <h2>Leave Request Details</h2>

            <button
              type="button"
              className="leaves-close-button"
              onClick={() =>
                setSelectedRequest(null)
              }
            >
              Close
            </button>
          </div>

          <dl className="leaves-details-grid">
            <div>
              <dt>Request ID</dt>
              <dd>{selectedRequest.id}</dd>
            </div>

            <div>
              <dt>Employee ID</dt>
              <dd>{selectedRequest.employee_id}</dd>
            </div>

            <div>
              <dt>Leave Policy ID</dt>
              <dd>{selectedRequest.leave_policy_id}</dd>
            </div>

            <div>
              <dt>Status</dt>
              <dd>
                {selectedRequest.status.replace(/_/g, " ")}
              </dd>
            </div>

            <div>
              <dt>Start Date</dt>
              <dd>{selectedRequest.start_date}</dd>
            </div>

            <div>
              <dt>End Date</dt>
              <dd>{selectedRequest.end_date}</dd>
            </div>

            <div>
              <dt>Requested Days</dt>
              <dd>{selectedRequest.requested_days}</dd>
            </div>

            <div>
              <dt>Reason</dt>
              <dd>
                {selectedRequest.reason || "Not provided"}
              </dd>
            </div>

            <div>
              <dt>Submitted At</dt>
              <dd>
                {selectedRequest.submitted_at ||
                  "Not submitted"}
              </dd>
            </div>

            <div>
              <dt>Decided At</dt>
              <dd>
                {selectedRequest.decided_at ||
                  "Not decided"}
              </dd>
            </div>

            <div>
              <dt>Decision Reason</dt>
              <dd>
                {selectedRequest.decision_reason ||
                  "Not provided"}
              </dd>
            </div>

            <div>
              <dt>Anomaly Flags</dt>
              <dd>
                {selectedRequest.anomaly_flags.length > 0
                  ? selectedRequest.anomaly_flags.join(", ")
                  : "None"}
              </dd>
            </div>

            <div>
              <dt>Created At</dt>
              <dd>{selectedRequest.created_at}</dd>
            </div>

            <div>
              <dt>Updated At</dt>
              <dd>{selectedRequest.updated_at}</dd>
            </div>
          </dl>
        </section>
      )}
    </section>
  );
}
