
const API_BASE_URL = (
  import.meta.env.VITE_API_BASE_URL ||
  "http://127.0.0.1:8000"
).replace(/\/$/, "");

export type LeaveStatus =
  | "DRAFT"
  | "SUBMITTED"
  | "PENDING_APPROVAL"
  | "NEEDS_REVIEW"
  | "APPROVED"
  | "REJECTED"
  | "CANCELLED";

export interface LeaveRequest {
  id: string;
  employee_id: string;
  leave_policy_id: string;
  start_date: string;
  end_date: string;
  requested_days: string;
  reason: string | null;
  status: LeaveStatus;
  submitted_at: string | null;
  decided_at: string | null;
  decision_reason: string | null;
  anomaly_flags: string[];
  metadata_json: Record<string, unknown>;
  created_at: string;
  updated_at: string;
}

export interface LeaveRequestCreate {
  employee_id: string;
  leave_policy_id: string;
  start_date: string;
  end_date: string;
  requested_days: string;
  reason?: string | null;
  metadata_json?: Record<string, unknown>;
}

export interface LeaveFilters {
  employee_id?: string;
  status?: LeaveStatus;
  start_date?: string;
  end_date?: string;
  offset?: number;
  limit?: number;
}

export interface LeaveRejectionPayload {
  reason: string;
}

export class LeaveApiError extends Error {
  constructor(
    message: string,
    public readonly status?: number
  ) {
    super(message);
    this.name = "LeaveApiError";
  }
}

async function leaveRequest<T>(
  path: string,
  accessToken: string,
  options: RequestInit = {}
): Promise<T> {
  let response: Response;

  try {
    response = await fetch(`${API_BASE_URL}${path}`, {
      ...options,
      headers: {
        Accept: "application/json",
        Authorization: `Bearer ${accessToken}`,
        ...(options.body
          ? { "Content-Type": "application/json" }
          : {}),
        ...options.headers,
      },
    });
  } catch (error) {
    if (options.signal?.aborted) {
      throw error;
    }

    throw new LeaveApiError(
      "Unable to connect to the Leave Management API."
    );
  }

  if (response.status === 401) {
    throw new LeaveApiError(
      "Your session has expired. Please log in again.",
      401
    );
  }

  if (!response.ok) {
    let message = `Leave API request failed (${response.status}).`;

    try {
      const data: unknown = await response.json();

      if (data && typeof data === "object" && "detail" in data) {
        const detail = (data as { detail: unknown }).detail;

        if (typeof detail === "string") {
          message = detail;
        } else if (Array.isArray(detail)) {
          message = detail
            .map((item) =>
              typeof item === "object" &&
              item !== null &&
              "msg" in item
                ? String(item.msg)
                : JSON.stringify(item)
            )
            .join("; ");
        }
      }
    } catch {
      // Preserve the fallback error message.
    }

    throw new LeaveApiError(message, response.status);
  }

  return (await response.json()) as T;
}

export async function listLeaveRequests(
  accessToken: string,
  filters: LeaveFilters = {},
  signal?: AbortSignal
): Promise<LeaveRequest[]> {
  const params = new URLSearchParams();

  if (filters.employee_id) {
    params.set("employee_id", filters.employee_id);
  }

  if (filters.status) {
    params.set("status", filters.status);
  }

  if (filters.start_date) {
    params.set("start_date", filters.start_date);
  }

  if (filters.end_date) {
    params.set("end_date", filters.end_date);
  }

  params.set("offset", String(filters.offset ?? 0));
  params.set("limit", String(filters.limit ?? 20));

  return leaveRequest<LeaveRequest[]>(
    `/api/v1/leaves?${params.toString()}`,
    accessToken,
    { signal }
  );
}

export async function getLeaveRequest(
  accessToken: string,
  leaveRequestId: string,
  signal?: AbortSignal
): Promise<LeaveRequest> {
  return leaveRequest<LeaveRequest>(
    `/api/v1/leaves/${encodeURIComponent(leaveRequestId)}`,
    accessToken,
    { signal }
  );
}

export async function createLeaveRequest(
  accessToken: string,
  payload: LeaveRequestCreate
): Promise<LeaveRequest> {
  return leaveRequest<LeaveRequest>(
    "/api/v1/leaves",
    accessToken,
    {
      method: "POST",
      body: JSON.stringify(payload),
    }
  );
}

export async function submitLeaveRequest(
  accessToken: string,
  leaveRequestId: string
): Promise<LeaveRequest> {
  return leaveRequest<LeaveRequest>(
    `/api/v1/leaves/${encodeURIComponent(leaveRequestId)}/submit`,
    accessToken,
    { method: "POST" }
  );
}

export async function approveLeaveRequest(
  accessToken: string,
  leaveRequestId: string
): Promise<LeaveRequest> {
  return leaveRequest<LeaveRequest>(
    `/api/v1/leaves/${encodeURIComponent(leaveRequestId)}/approve`,
    accessToken,
    { method: "POST" }
  );
}

export async function rejectLeaveRequest(
  accessToken: string,
  leaveRequestId: string,
  reason: string
): Promise<LeaveRequest> {
  return leaveRequest<LeaveRequest>(
    `/api/v1/leaves/${encodeURIComponent(leaveRequestId)}/reject`,
    accessToken,
    {
      method: "POST",
      body: JSON.stringify({ reason }),
    }
  );
}
