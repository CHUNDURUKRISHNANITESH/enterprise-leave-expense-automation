
const API_BASE_URL = (
  import.meta.env.VITE_API_BASE_URL ||
  "http://127.0.0.1:8000"
).replace(/\/$/, "");

export interface CurrentUser {
  user_id: string;
  employee_id: string;
  role: string;
}

export class CurrentUserApiError extends Error {
  constructor(
    message: string,
    public readonly status?: number
  ) {
    super(message);
    this.name = "CurrentUserApiError";
  }
}

export async function getCurrentUser(
  accessToken: string,
  signal?: AbortSignal
): Promise<CurrentUser> {
  let response: Response;

  try {
    response = await fetch(`${API_BASE_URL}/api/v1/auth/me`, {
      method: "GET",
      headers: {
        Accept: "application/json",
        Authorization: `Bearer ${accessToken}`,
      },
      signal,
    });
  } catch (error) {
    if (signal?.aborted) {
      throw error;
    }

    throw new CurrentUserApiError(
      "Unable to connect to the authentication API."
    );
  }

  if (response.status === 401) {
    throw new CurrentUserApiError(
      "Your session has expired. Please log in again.",
      401
    );
  }

  if (!response.ok) {
    let message = `Unable to retrieve current user (${response.status}).`;

    try {
      const data: unknown = await response.json();

      if (
        data &&
        typeof data === "object" &&
        "detail" in data &&
        typeof data.detail === "string"
      ) {
        message = data.detail;
      }
    } catch {
      // Keep the fallback message.
    }

    throw new CurrentUserApiError(message, response.status);
  }

  return (await response.json()) as CurrentUser;
}
