
const API_BASE_URL = (
  import.meta.env.VITE_API_BASE_URL ||
  "http://127.0.0.1:8000"
).replace(/\/$/, "");

export type AnalyticsEndpoint =
  | "leave-utilization"
  | "expenses"
  | "approvals"
  | "reimbursements";

export type AnalyticsRecord = Record<
  string,
  string | number | boolean | null
>;

export class AnalyticsApiError extends Error {
  constructor(
    message: string,
    public readonly status?: number
  ) {
    super(message);
    this.name = "AnalyticsApiError";
  }
}

export async function getAnalytics(
  accessToken: string,
  endpoint: AnalyticsEndpoint,
  signal?: AbortSignal
): Promise<AnalyticsRecord[]> {
  let response: Response;

  try {
    response = await fetch(
      `${API_BASE_URL}/api/v1/analytics/${endpoint}`,
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

    throw new AnalyticsApiError(
      "Unable to connect to the analytics API."
    );
  }

  if (response.status === 401) {
    throw new AnalyticsApiError(
      "Your session has expired. Please sign in again.",
      401
    );
  }

  if (response.status === 403) {
    throw new AnalyticsApiError(
      "Only administrators can access analytics.",
      403
    );
  }

  if (!response.ok) {
    throw new AnalyticsApiError(
      `Analytics request failed (HTTP ${response.status}).`,
      response.status
    );
  }

  const data: unknown = await response.json();

  if (!Array.isArray(data)) {
    throw new AnalyticsApiError(
      "Unexpected analytics response format."
    );
  }

  return data as AnalyticsRecord[];
}

export function getLeaveUtilization(
  accessToken: string,
  signal?: AbortSignal
) {
  return getAnalytics(
    accessToken,
    "leave-utilization",
    signal
  );
}

export function getExpenseAnalytics(
  accessToken: string,
  signal?: AbortSignal
) {
  return getAnalytics(
    accessToken,
    "expenses",
    signal
  );
}

export function getApprovalAnalytics(
  accessToken: string,
  signal?: AbortSignal
) {
  return getAnalytics(
    accessToken,
    "approvals",
    signal
  );
}

export function getReimbursementAnalytics(
  accessToken: string,
  signal?: AbortSignal
) {
  return getAnalytics(
    accessToken,
    "reimbursements",
    signal
  );
}
