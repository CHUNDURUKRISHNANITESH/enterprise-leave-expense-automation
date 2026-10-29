
export interface LeaveBalance {
  id: string;
  employee_id: string;
  leave_policy_id: string;
  period_year: number;
  entitled_days: string;
  used_days: string;
  pending_days: string;
  carryover_days: string;
  adjustment_days: string;
  available_days: string;
  last_calculated_at: string | null;
  notes: string | null;
  created_at: string;
  updated_at: string;
}

export class LeaveBalanceApiError extends Error {
  constructor(
    message: string,
    public status: number
  ) {
    super(message);
    this.name = "LeaveBalanceApiError";
  }
}

export async function getEmployeeLeaveBalances(
  accessToken: string,
  employeeId: string,
  year: number = new Date().getFullYear(),
  signal?: AbortSignal
): Promise<LeaveBalance[]> {
  const response = await fetch(
    `http://127.0.0.1:8000/api/v1/leaves/balances/${encodeURIComponent(employeeId)}?year=${year}`,
    {
      method: "GET",
      headers: {
        Authorization: `Bearer ${accessToken}`,
        Accept: "application/json",
      },
      signal,
    }
  );

  if (!response.ok) {
    let message = "Unable to load employee leave balances.";

    try {
      const errorData: { detail?: unknown } = await response.json();

      if (typeof errorData.detail === "string") {
        message = errorData.detail;
      }
    } catch {
      // Keep the default error message.
    }

    throw new LeaveBalanceApiError(message, response.status);
  }

  return (await response.json()) as LeaveBalance[];
}
