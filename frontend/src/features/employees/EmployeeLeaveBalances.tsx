
import { useEffect, useState } from "react";
import {
  getEmployeeLeaveBalances,
  LeaveBalanceApiError,
  type LeaveBalance,
} from "../../services/leaveBalances";
import type { Employee } from "../../services/employees";
import "../../css/EmployeeLeaveBalances.css";

interface EmployeeLeaveBalancesProps {
  accessToken: string;
  employee: Employee;
  onClose: () => void;
  onLogout: () => void;
}

export default function EmployeeLeaveBalances({
  accessToken,
  employee,
  onClose,
  onLogout,
}: EmployeeLeaveBalancesProps) {
  const [year, setYear] = useState(new Date().getFullYear());
  const [balances, setBalances] = useState<LeaveBalance[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    const controller = new AbortController();

    async function loadBalances() {
      setLoading(true);
      setError("");
      setBalances([]);

      try {
        const data = await getEmployeeLeaveBalances(
          accessToken,
          employee.id,
          year,
          controller.signal
        );

        if (!controller.signal.aborted) {
          setBalances(data);
        }
      } catch (err) {
        if (controller.signal.aborted) return;

        if (
          err instanceof LeaveBalanceApiError &&
          err.status === 401
        ) {
          onLogout();
          return;
        }

        setError(
          err instanceof Error
            ? err.message
            : "Unable to load leave balances."
        );
      } finally {
        if (!controller.signal.aborted) {
          setLoading(false);
        }
      }
    }

    void loadBalances();

    return () => controller.abort();
  }, [accessToken, employee.id, year, onLogout]);

  function formatDays(value: string) {
    const days = Number(value);
    return Number.isFinite(days) ? days.toFixed(2) : value;
  }

  const totalAvailable = balances.reduce(
    (sum, balance) => sum + Number(balance.available_days),
    0
  );

  return (
    <section className="employee-leave-balances">
      <div className="employee-leave-balances-header">
        <div>
          <span className="dashboard-eyebrow">
            LEAVE MANAGEMENT
          </span>

          <h2>Employee Leave Balances</h2>

          <p>
            {employee.first_name} {employee.last_name}
            {" · "}
            {employee.employee_number}
          </p>
        </div>

        <button type="button" onClick={onClose}>
          Close
        </button>
      </div>

      <div className="employee-leave-balances-toolbar">
        <label htmlFor="leave-balance-year">
          Balance Year
        </label>

        <input
          id="leave-balance-year"
          type="number"
          min={2000}
          max={2200}
          value={year}
          onChange={(event) => {
            const value = Number(event.target.value);

            if (
              Number.isInteger(value) &&
              value >= 2000 &&
              value <= 2200
            ) {
              setYear(value);
            }
          }}
        />
      </div>

      {loading && (
        <p role="status">Loading leave balances...</p>
      )}

      {error && (
        <p className="employee-leave-balances-error" role="alert">
          {error}
        </p>
      )}

      {!loading && !error && (
        <>
          <div className="employee-leave-balances-summary">
            <span>Total Available Leave</span>
            <strong>{totalAvailable.toFixed(2)} days</strong>
          </div>

          {balances.length === 0 ? (
            <p className="employee-leave-balances-empty">
              No leave balances found for {year}.
            </p>
          ) : (
            <div className="employee-leave-balances-table-wrap">
              <table className="employee-leave-balances-table">
                <thead>
                  <tr>
                    <th>Leave Policy ID</th>
                    <th>Entitled</th>
                    <th>Used</th>
                    <th>Pending</th>
                    <th>Carryover</th>
                    <th>Adjustments</th>
                    <th>Available</th>
                  </tr>
                </thead>

                <tbody>
                  {balances.map((balance) => (
                    <tr key={balance.id}>
                      <td title={balance.leave_policy_id}>
                        {balance.leave_policy_id}
                      </td>
                      <td>{formatDays(balance.entitled_days)}</td>
                      <td>{formatDays(balance.used_days)}</td>
                      <td>{formatDays(balance.pending_days)}</td>
                      <td>{formatDays(balance.carryover_days)}</td>
                      <td>{formatDays(balance.adjustment_days)}</td>
                      <td>
                        <strong>
                          {formatDays(balance.available_days)}
                        </strong>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </>
      )}
    </section>
  );
}
