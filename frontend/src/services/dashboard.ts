
const API_BASE_URL = (
  import.meta.env.VITE_API_BASE_URL ||
  "http://127.0.0.1:8000"
).replace(/\/$/, "");

export interface DashboardSummary {
  total_employees: number;
  total_leave_requests: number;
  pending_leave_requests: number;
  total_expense_claims: number;
  total_expense_amounts_by_currency: Record<string, string>;
  pending_approval_steps: number;
  total_reimbursements: number;
  paid_reimbursement_amounts_by_currency: Record<string, string>;
}

export class DashboardApiError extends Error {
  constructor(
    message: string,
    public readonly status?: number
  ) {
    super(message);
    this.name = "DashboardApiError";
  }
}

export async function getDashboardSummary(
  accessToken: string,
  signal?: AbortSignal
): Promise<DashboardSummary> {
  let response: Response;

  try {
    response = await fetch(
      `${API_BASE_URL}/api/v1/dashboard/summary`,
      {
        method: "GET",
        headers: {
          Authorization: `Bearer ${accessToken}`,
          Accept: "application/json",
        },
        signal,
      }
    );
  } catch (error) {
    if (signal?.aborted) {
      throw error;
    }

    throw new DashboardApiError(
      "Unable to connect to the dashboard API."
    );
  }

  if (response.status === 401) {
    throw new DashboardApiError(
      "Your session has expired. Please sign in again.",
      401
    );
  }

  if (response.status === 403) {
    throw new DashboardApiError(
      "You do not have permission to view the dashboard.",
      403
    );
  }

  if (!response.ok) {
    throw new DashboardApiError(
      `Dashboard request failed (HTTP ${response.status}).`,
      response.status
    );
  }

  return (await response.json()) as DashboardSummary;
}
