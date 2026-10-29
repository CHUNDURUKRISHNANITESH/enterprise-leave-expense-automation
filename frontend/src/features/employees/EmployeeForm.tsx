
import { useState, type FormEvent } from "react";
import {
  createEmployee,
  updateEmployee,
  EmployeeApiError,
  type Employee,
  type EmployeeCreate,
} from "../../services/employees";
import "../../css/EmployeeForm.css";

interface EmployeeFormProps {
  accessToken: string;
  employee?: Employee | null;
  onCreated: () => void;
  onCancel: () => void;
  onLogout: () => void;
}

function initialForm(employee?: Employee | null): EmployeeCreate {
  if (employee) {
    return {
      employee_number: employee.employee_number,
      first_name: employee.first_name,
      last_name: employee.last_name,
      email: employee.email,
      department: employee.department,
      country: employee.country,
      currency: employee.currency,
      employment_start_date: employee.employment_start_date,
      job_title: employee.job_title ?? "",
      employment_status: employee.employment_status,
      is_approver: employee.is_approver,
    };
  }

  return {
    employee_number: "",
    first_name: "",
    last_name: "",
    email: "",
    department: "",
    country: "IN",
    currency: "INR",
    employment_start_date: new Date().toLocaleDateString("en-CA"),
    job_title: "",
    employment_status: "ACTIVE",
    is_approver: false,
  };
}

export default function EmployeeForm({
  accessToken,
  employee,
  onCreated,
  onCancel,
  onLogout,
}: EmployeeFormProps) {
  const isEditing = Boolean(employee);

  const [form, setForm] = useState<EmployeeCreate>(() =>
    initialForm(employee)
  );

  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");

  function updateField<K extends keyof EmployeeCreate>(
    field: K,
    value: EmployeeCreate[K]
  ) {
    setForm((current) => ({
      ...current,
      [field]: value,
    }));
  }

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();

    if (saving) return;

    setSaving(true);
    setError("");

    const payload = {
      ...form,
      employee_number: form.employee_number.trim(),
      first_name: form.first_name.trim(),
      last_name: form.last_name.trim(),
      email: form.email.trim(),
      department: form.department.trim(),
      country: form.country.trim().toUpperCase(),
      currency: form.currency?.trim().toUpperCase() || "INR",
      job_title: form.job_title?.trim() || null,
    };

    try {
      if (employee) {
        await updateEmployee(accessToken, employee.id, payload);
      } else {
        await createEmployee(accessToken, payload);
      }

      onCreated();
    } catch (err) {
      if (err instanceof EmployeeApiError && err.status === 401) {
        onLogout();
        return;
      }

      setError(
        err instanceof Error
          ? err.message
          : "Unable to save employee information."
      );
    } finally {
      setSaving(false);
    }
  }

  return (
    <section className="employee-form-card">
      <div className="employee-form-header">
        <div>
          <h2>{isEditing ? "Edit Employee" : "Add New Employee"}</h2>
          <p>
            {isEditing
              ? "Update the existing employee's information."
              : "Enter the new employee's information below."}
          </p>
        </div>

        <button type="button" onClick={onCancel} disabled={saving}>
          Cancel
        </button>
      </div>

      <form onSubmit={handleSubmit} className="employee-form">
        <div className="employee-form-grid">
          <label>
            Employee Number *
            <input
              required
              value={form.employee_number}
              onChange={(e) =>
                updateField("employee_number", e.target.value)
              }
            />
          </label>

          <label>
            First Name *
            <input
              required
              value={form.first_name}
              onChange={(e) =>
                updateField("first_name", e.target.value)
              }
            />
          </label>

          <label>
            Last Name *
            <input
              required
              value={form.last_name}
              onChange={(e) =>
                updateField("last_name", e.target.value)
              }
            />
          </label>

          <label>
            Email *
            <input
              required
              type="email"
              value={form.email}
              onChange={(e) =>
                updateField("email", e.target.value)
              }
            />
          </label>

          <label>
            Department *
            <input
              required
              value={form.department}
              onChange={(e) =>
                updateField("department", e.target.value)
              }
            />
          </label>

          <label>
            Job Title
            <input
              value={form.job_title ?? ""}
              onChange={(e) =>
                updateField("job_title", e.target.value)
              }
            />
          </label>

          <label>
            Country Code *
            <input
              required
              minLength={2}
              maxLength={2}
              value={form.country}
              onChange={(e) =>
                updateField("country", e.target.value.toUpperCase())
              }
            />
          </label>

          <label>
            Currency
            <input
              maxLength={3}
              value={form.currency ?? ""}
              onChange={(e) =>
                updateField("currency", e.target.value.toUpperCase())
              }
            />
          </label>

          <label>
            Employment Start Date *
            <input
              required
              type="date"
              value={form.employment_start_date}
              onChange={(e) =>
                updateField("employment_start_date", e.target.value)
              }
            />
          </label>

          <label>
            Employment Status
            <select
              value={form.employment_status}
              onChange={(e) =>
                updateField("employment_status", e.target.value)
              }
            >
              <option value="ACTIVE">Active</option>
              <option value="INACTIVE">Inactive</option>
              <option value="ON_LEAVE">On Leave</option>
            </select>
          </label>
        </div>

        <label className="employee-form-checkbox">
          <input
            type="checkbox"
            checked={form.is_approver ?? false}
            onChange={(e) =>
              updateField("is_approver", e.target.checked)
            }
          />
          Employee is an approver
        </label>

        {error && (
          <p className="employee-form-error" role="alert">
            {error}
          </p>
        )}

        <div className="employee-form-actions">
          <button type="button" onClick={onCancel} disabled={saving}>
            Cancel
          </button>

          <button type="submit" disabled={saving}>
            {saving
              ? "Saving..."
              : isEditing
                ? "Save Changes"
                : "Create Employee"}
          </button>
        </div>
      </form>
    </section>
  );
}
