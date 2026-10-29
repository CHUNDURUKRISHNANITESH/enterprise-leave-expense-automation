
import { useEffect, useState, type FormEvent } from "react";
import {
  createLeaveRequest,
  LeaveApiError,
  type LeaveRequest,
} from "../../services/leaves";
import {
  getCurrentUser,
  type CurrentUser,
} from "../../services/currentUser";
import {
  getAvailableLeavePolicies,
  type AvailableLeavePolicy,
} from "../../services/leavePolicies";
import "../../css/CreateLeaveRequestForm.css";

interface CreateLeaveRequestFormProps {
  accessToken: string;
  onCreated: (request: LeaveRequest) => void;
  onCancel: () => void;
  onLogout: () => void;
}

function calculateWorkingDays(start: string, end: string): number {
  if (!start || !end || end < start) return 0;

  const startDate = new Date(`${start}T12:00:00Z`);
  const endDate = new Date(`${end}T12:00:00Z`);

  if (
    Number.isNaN(startDate.getTime()) ||
    Number.isNaN(endDate.getTime())
  ) {
    return 0;
  }

  let count = 0;
  const current = new Date(startDate);

  while (current <= endDate) {
    const weekday = current.getUTCDay();

    if (weekday !== 0 && weekday !== 6) {
      count += 1;
    }

    current.setUTCDate(current.getUTCDate() + 1);
  }

  return count;
}

export default function CreateLeaveRequestForm({
  accessToken,
  onCreated,
  onCancel,
  onLogout,
}: CreateLeaveRequestFormProps) {
  const [currentUser, setCurrentUser] =
    useState<CurrentUser | null>(null);
  const [policies, setPolicies] =
    useState<AvailableLeavePolicy[]>([]);
  const [policyId, setPolicyId] = useState("");
  const [startDate, setStartDate] = useState("");
  const [endDate, setEndDate] = useState("");
  const [reason, setReason] = useState("");
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");

  const requestedDays = calculateWorkingDays(startDate, endDate);
  const selectedPolicy = policies.find(
    (policy) => policy.id === policyId
  );

  useEffect(() => {
    const controller = new AbortController();

    async function loadUser() {
      setLoading(true);
      setError("");

      try {
        const user = await getCurrentUser(
          accessToken,
          controller.signal
        );

        if (!controller.signal.aborted) {
          setCurrentUser(user);
        }
      } catch (err) {
        if (controller.signal.aborted) return;

        if (
          err instanceof Error &&
          "status" in err &&
          err.status === 401
        ) {
          onLogout();
          return;
        }

        setError(
          err instanceof Error
            ? err.message
            : "Unable to identify the current employee."
        );
      } finally {
        if (!controller.signal.aborted) {
          setLoading(false);
        }
      }
    }

    void loadUser();

    return () => controller.abort();
  }, [accessToken, onLogout]);

  useEffect(() => {
    if (!currentUser) return;

    const controller = new AbortController();
    const year = startDate
      ? Number(startDate.slice(0, 4))
      : new Date().getFullYear();

    async function loadPolicies() {
      try {
        const result = await getAvailableLeavePolicies(
          accessToken,
          year,
          controller.signal
        );

        if (controller.signal.aborted) return;

        setPolicies(result);
        setPolicyId((previous) =>
          result.some((policy) => policy.id === previous)
            ? previous
            : ""
        );
      } catch (err) {
        if (controller.signal.aborted) return;

        if (
          err instanceof Error &&
          "status" in err &&
          err.status === 401
        ) {
          onLogout();
          return;
        }

        setPolicies([]);
        setPolicyId("");
        setError(
          err instanceof Error
            ? err.message
            : "Unable to load leave policies."
        );
      }
    }

    void loadPolicies();

    return () => controller.abort();
  }, [accessToken, currentUser, startDate, onLogout]);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError("");

    if (!currentUser || !selectedPolicy) {
      setError("Please select an available leave policy.");
      return;
    }

    if (!startDate || !endDate || endDate < startDate) {
      setError("Please select a valid date range.");
      return;
    }

    if (startDate.slice(0, 4) !== endDate.slice(0, 4)) {
      setError(
        "For now, create separate requests for different calendar years."
      );
      return;
    }

    if (requestedDays <= 0) {
      setError("The selected dates must include a working day.");
      return;
    }

    if (
      startDate < selectedPolicy.effective_from ||
      (selectedPolicy.effective_to !== null &&
        endDate > selectedPolicy.effective_to)
    ) {
      setError("Selected dates fall outside the policy period.");
      return;
    }

    if (
      selectedPolicy.max_consecutive_days !== null &&
      requestedDays > selectedPolicy.max_consecutive_days
    ) {
      setError("Requested days exceed the policy limit.");
      return;
    }

    if (requestedDays > Number(selectedPolicy.available_days)) {
      setError("Insufficient available leave balance.");
      return;
    }

    setSaving(true);

    try {
      const request = await createLeaveRequest(accessToken, {
        employee_id: currentUser.employee_id,
        leave_policy_id: selectedPolicy.id,
        start_date: startDate,
        end_date: endDate,
        requested_days: String(requestedDays),
        reason: reason.trim() || null,
        metadata_json: {},
      });

      onCreated(request);
    } catch (err) {
      if (err instanceof LeaveApiError && err.status === 401) {
        onLogout();
        return;
      }

      setError(
        err instanceof Error
          ? err.message
          : "Unable to create leave request."
      );
    } finally {
      setSaving(false);
    }
  }

  return (
    <section className="create-leave-form">
      <div className="create-leave-form-header">
        <div>
          <h2>Create Leave Request</h2>
          <p>Complete the details to save a new draft.</p>
        </div>

        <button type="button" onClick={onCancel}>
          Close
        </button>
      </div>

      {loading ? (
        <p>Identifying your employee account...</p>
      ) : (
        <form onSubmit={handleSubmit}>
          {error && <p role="alert" className="create-leave-error">{error}</p>}

          <label>
            Employee ID
            <input
              type="text"
              value={currentUser?.employee_id ?? ""}
              readOnly
            />
          </label>

          <label>
            Leave Policy
            <select
              required
              value={policyId}
              onChange={(event) => setPolicyId(event.target.value)}
            >
              <option value="">Select a leave policy</option>
              {policies.map((policy) => (
                <option key={policy.id} value={policy.id}>
                  {policy.name} ({policy.leave_type})
                </option>
              ))}
            </select>
          </label>

          {selectedPolicy && (
            <p className="create-leave-balance">
              Available balance: {selectedPolicy.available_days} days
            </p>
          )}

          <div className="create-leave-date-grid">
            <label>
              Start Date
              <input
                type="date"
                required
                value={startDate}
                onChange={(event) => setStartDate(event.target.value)}
              />
            </label>

            <label>
              End Date
              <input
                type="date"
                required
                min={startDate || undefined}
                value={endDate}
                onChange={(event) => setEndDate(event.target.value)}
              />
            </label>
          </div>

          <p className="create-leave-working-days">
            Working days (Monday–Friday): <strong>{requestedDays}</strong>
          </p>

          <label>
            Reason (optional)
            <textarea
              rows={4}
              maxLength={2000}
              value={reason}
              onChange={(event) => setReason(event.target.value)}
              placeholder="Enter the reason for your leave..."
            />
          </label>

          <div className="create-leave-actions">
            <button type="button" onClick={onCancel} disabled={saving}>
              Cancel
            </button>
            <button
              type="submit"
              disabled={
                saving ||
                loading ||
                !currentUser ||
                !selectedPolicy ||
                requestedDays === 0
              }
            >
              {saving ? "Creating..." : "Create Draft"}
            </button>
          </div>
        </form>
      )}
    </section>
  );
}
