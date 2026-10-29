const API_BASE_URL = (import.meta.env.VITE_API_BASE_URL || "http://127.0.0.1:8000").replace(/\/$/, "");

export interface LoginRequest {
  email: string;
  password: string;
}

export interface TokenResponse {
  access_token: string;
  token_type: string;
  expires_in: number;
}

export class AuthenticationError extends Error {
  constructor(message: string) {
    super(message);
    this.name = "AuthenticationError";
  }
}

export async function login(credentials: LoginRequest): Promise<TokenResponse> {
  let response: Response;
  try {
    response = await fetch(`${API_BASE_URL}/api/v1/auth/login`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(credentials),
    });
  } catch {
    throw new AuthenticationError("Cannot connect to the server. Please try again.");
  }

  if (!response.ok) {
    if (response.status === 401) throw new AuthenticationError("Invalid email or password.");
    if (response.status === 403) throw new AuthenticationError("Your account is inactive.");
    throw new AuthenticationError(`Sign in failed (HTTP ${response.status}).`);
  }
  const result: TokenResponse = await response.json();
  if (!result.access_token || result.token_type.toLowerCase() !== "bearer") {
    throw new AuthenticationError("Unexpected authentication response.");
  }
  return result;
}
