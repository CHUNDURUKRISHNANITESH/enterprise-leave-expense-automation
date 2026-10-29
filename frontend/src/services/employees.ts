
const API_BASE_URL = (
  import.meta.env.VITE_API_BASE_URL ||
  "http://127.0.0.1:8000"
).replace(/\/$/, "");

export interface Employee {
  id: string;
  employee_number: string;
  first_name: string;
  last_name: string;
  email: string;
  job_title: string | null;
  department: string;
  country: string;
  currency: string;
  manager_id: string | null;
  cost_center_id: string | null;
  employment_start_date: string;
  employment_end_date: string | null;
  employment_status: string;
  is_approver: boolean;
  attributes: Record<string, unknown>;
  created_at: string;
  updated_at: string;
}

export interface EmployeeCreate {
  employee_number: string;
  first_name: string;
  last_name: string;
  email: string;
  department: string;
  country: string;
  employment_start_date: string;

  job_title?: string | null;
  currency?: string;
  manager_id?: string | null;
  cost_center_id?: string | null;
  employment_end_date?: string | null;
  employment_status?: string;
  is_approver?: boolean;
  attributes?: Record<string, unknown>;
}

export type EmployeeUpdate = Partial<{
  employee_number: string | null;
  first_name: string | null;
  last_name: string | null;
  email: string | null;
  job_title: string | null;
  department: string | null;
  country: string | null;
  currency: string | null;
  manager_id: string | null;
  cost_center_id: string | null;
  employment_start_date: string | null;
  employment_end_date: string | null;
  employment_status: string | null;
  is_approver: boolean | null;
  attributes: Record<string, unknown> | null;
}>;

export interface EmployeeFilters {
  offset?: number;
  limit?: number;
  department?: string;
  country?: string;
  search?: string;
}

export class EmployeeApiError extends Error {
  constructor(
    message: string,
    public readonly status?: number
  ) {
    super(message);
    this.name = "EmployeeApiError";
  }
}

async function employeeRequest<T>(
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
    if (options.signal?.aborted) throw error;

    throw new EmployeeApiError(
      "Unable to connect to the Employee API."
    );
  }

  if (response.status === 401) {
    throw new EmployeeApiError(
      "Your session has expired. Please sign in again.",
      401
    );
  }

  if (response.status === 403) {
    throw new EmployeeApiError(
      "You do not have permission to perform this action.",
      403
    );
  }

  if (response.status === 404) {
    throw new EmployeeApiError(
      "The requested employee was not found.",
      404
    );
  }

  if (!response.ok) {
    let message = `Employee request failed (HTTP ${response.status}).`;

    try {
      const body: unknown = await response.json();

      if (body && typeof body === "object" && "detail" in body) {
        const detail = (body as { detail: unknown }).detail;

        if (typeof detail === "string") {
          message = detail;
        } else if (Array.isArray(detail)) {
          message = detail
            .map((item: unknown) => {
              if (item && typeof item === "object" && "msg" in item) {
                return String((item as { msg: unknown }).msg);
              }
              return "Invalid field value";
            })
            .join("; ");
        }
      }
    } catch {
      // Keep the HTTP error message if the response is not JSON.
    }

    throw new EmployeeApiError(message, response.status);
  }

  return (await response.json()) as T;
}

export async function listEmployees(
  accessToken: string,
  filters: EmployeeFilters = {},
  signal?: AbortSignal
): Promise<Employee[]> {
  const params = new URLSearchParams();
if (filters.search?.trim()) {
  params.set("search", filters.search.trim());
}

  params.set("offset", String(filters.offset ?? 0));
  params.set("limit", String(filters.limit ?? 50));

  if (filters.department) {
    params.set("department", filters.department);
  }

  if (filters.country) {
    params.set("country", filters.country);
  }

  return employeeRequest<Employee[]>(
    `/api/v1/employees?${params.toString()}`,
    accessToken,
    { method: "GET", signal }
  );
}

export async function getEmployee(
  accessToken: string,
  employeeId: string,
  signal?: AbortSignal
): Promise<Employee> {
  return employeeRequest<Employee>(
    `/api/v1/employees/${encodeURIComponent(employeeId)}`,
    accessToken,
    { method: "GET", signal }
  );
}

export async function createEmployee(
  accessToken: string,
  payload: EmployeeCreate
): Promise<Employee> {
  return employeeRequest<Employee>(
    "/api/v1/employees",
    accessToken,
    {
      method: "POST",
      body: JSON.stringify(payload),
    }
  );
}

export async function updateEmployee(
  accessToken: string,
  employeeId: string,
  payload: EmployeeUpdate
): Promise<Employee> {
  return employeeRequest<Employee>(
    `/api/v1/employees/${encodeURIComponent(employeeId)}`,
    accessToken,
    {
      method: "PATCH",
      body: JSON.stringify(payload),
    }
  );
}
