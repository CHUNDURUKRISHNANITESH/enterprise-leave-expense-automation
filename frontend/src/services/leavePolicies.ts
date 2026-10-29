
const API_BASE_URL = (
  import.meta.env.VITE_API_BASE_URL ||
  "http://127.0.0.1:8000"
).replace(/\/$/, "");

export interface AvailableLeavePolicy {
  id: string;
  name: string;
  leave_type: string;
  available_days: string;
  annual_entitlement: string;
  max_consecutive_days: number | null;
  effective_from: string;
  effective_to: string | null;
}

export class LeavePoliciesApiError extends Error {
  constructor(
    message: string,
    public readonly status?: number
  ) {
    super(message);
    this.name = "LeavePoliciesApiError";
  }
}

export async function getAvailableLeavePolicies(
  accessToken: string,
  year: number = new Date().getFullYear(),
  signal?: AbortSignal
): Promise<AvailableLeavePolicy[]> {
  const response = await fetch(
    `${API_BASE_URL}/api/v1/leaves/policies?year=${year}`,
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
    let message = "Unable to load available leave policies.";

    try {
      const errorData: { detail?: unknown } = await response.json();

      if (typeof errorData.detail === "string") {
        message = errorData.detail;
      }
    } catch {
      // Keep the default error message.
    }

    throw new LeavePoliciesApiError(message, response.status);
  }

  return (await response.json()) as AvailableLeavePolicy[];
}
