
import { useEffect, useRef, useState } from "react";
import {
  listEmployees,
  type Employee,
  EmployeeApiError,
} from "../../services/employees";
import "../../css/EmployeesPage.css";
import EmployeeForm from "./EmployeeForm";
import EmployeeLeaveBalances from "./EmployeeLeaveBalances";

interface EmployeesPageProps {
  accessToken: string;
  onLogout: () => void;
}

const PAGE_SIZE = 20;

export default function EmployeesPage({
  accessToken,
  onLogout,
}: EmployeesPageProps) {
  const [employees, setEmployees] = useState<Employee[]>([]);
  const [search, setSearch] = useState("");
const [debouncedSearch, setDebouncedSearch] = useState("");
  const [department, setDepartment] = useState("");
  const [country, setCountry] = useState("");
  const [page, setPage] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [selectedEmployee, setSelectedEmployee] =
    useState<Employee | null>(null);
const detailsRef = useRef<HTMLDivElement | null>(null);
const [showCreateForm, setShowCreateForm] = useState(false);
const [editingEmployee, setEditingEmployee] = useState<Employee | null>(null);
const [refreshKey, setRefreshKey] = useState(0);
const [balanceEmployee, setBalanceEmployee] = useState<Employee | null>(null);

useEffect(() => {
  const timer = window.setTimeout(() => {
    setDebouncedSearch(search.trim());
  }, 400);

  return () => window.clearTimeout(timer);
}, [search]);
useEffect(() => {
  if (selectedEmployee) {
    detailsRef.current?.scrollIntoView({
      behavior: "smooth",
      block: "start",
    });
  }
}, [selectedEmployee]);

  useEffect(() => {
    const controller = new AbortController();

    async function loadEmployees() {
      setLoading(true);
      setError("");

      try {
        const data = await listEmployees(accessToken, {
  offset: page * PAGE_SIZE,
  limit: PAGE_SIZE,
  search: debouncedSearch || undefined,
  department: department.trim() || undefined,
  country: country.trim() || undefined,
}, controller.signal);

        if (!controller.signal.aborted) {
          setEmployees(data);
        }
      } catch (err) {
        if (controller.signal.aborted) return;

        if (err instanceof EmployeeApiError && err.status === 401) {
          onLogout();
          return;
        }

        setError(
          err instanceof Error
            ? err.message
            : "Unable to load employees."
        );
      } finally {
        if (!controller.signal.aborted) setLoading(false);
      }
    }

    loadEmployees();

    return () => controller.abort();
  }, [accessToken, onLogout, page,debouncedSearch, department, country, refreshKey]);

const filteredEmployees = employees;

  return (
    <section className="employees-page">
      <header className="employees-header">
  <div>
    <span className="dashboard-eyebrow">WORKFORCE MANAGEMENT</span>
    <h1>Employees</h1>
    <p>View and manage employee records across departments.</p>
  </div>

  <button
    type="button"
    className="employees-add-button"
    onClick={() => {
      setSelectedEmployee(null);
      setShowCreateForm(true);
      setEditingEmployee(null);
      setBalanceEmployee(null);
    }}
  >
    + Add Employee
  </button>
</header>

{balanceEmployee && (
  <EmployeeLeaveBalances
    key={balanceEmployee.id}
    accessToken={accessToken}
    employee={balanceEmployee}
    onLogout={onLogout}
    onClose={() => setBalanceEmployee(null)}
  />
)}

{showCreateForm && (
  <EmployeeForm
    accessToken={accessToken}
    onLogout={onLogout}
    onCancel={() => setShowCreateForm(false)}
    onCreated={() => {
      setShowCreateForm(false);
      setSearch("");
      setDepartment("");
      setCountry("");
      setPage(0);
      setRefreshKey((value) => value + 1);
    }}
  />
)}

{editingEmployee && (
  <EmployeeForm
    key={editingEmployee.id}
    accessToken={accessToken}
    employee={editingEmployee}
    onLogout={onLogout}
    onCancel={() => setEditingEmployee(null)}
    onCreated={() => {
      setEditingEmployee(null);
      setSelectedEmployee(null);
      setRefreshKey((value) => value + 1);
    }}
  />
)}
      <div className="employees-toolbar">
      
       <input
  type="search"
  placeholder="Search by name, email, or employee number..."
  value={search}
  onChange={(event) => {
    setSearch(event.target.value);
    setPage(0);
  }}
/>

        <input
          type="text"
          placeholder="Department"
          value={department}
          onChange={(event) => {
            setDepartment(event.target.value);
            setPage(0);
          }}
        />

        <input
          type="text"
          placeholder="Country code (IN, US, GB)"
          maxLength={2}
          value={country}
          onChange={(event) => {
            setCountry(event.target.value.toUpperCase());
            setPage(0);
          }}
        />
      </div>

      {loading && <p role="status">Loading employees...</p>}

      {error && (
        <p className="dashboard-error" role="alert">
          {error}
        </p>
      )}

      {!loading && !error && (
        <>
          <div className="employees-table-wrap">
            <table className="employees-table">
              <thead>
                <tr>
                  <th>Employee</th>
                  <th>Employee ID</th>
                  <th>Department</th>
                  <th>Country</th>
                  <th>Status</th>
                  <th>Action</th>
                </tr>
              </thead>

              <tbody>
                {filteredEmployees.map((employee) => (
                  <tr key={employee.id}>
                    <td>
                      <strong>
                        {employee.first_name} {employee.last_name}
                      </strong>
                      <small>{employee.email}</small>
                    </td>
                    <td>{employee.employee_number}</td>
                    <td>{employee.department}</td>
                    <td>{employee.country}</td>
                    <td>
                      <span className="employees-status">
                        {employee.employment_status}
                      </span>
                    </td>
                    <td>
  <div className="employees-row-actions">
    <button
      type="button"
      onClick={() => {
        setSelectedEmployee(employee);
        setEditingEmployee(null);
      }}
    >
      View
    </button>

    <button
      type="button"
      onClick={() => {
        setSelectedEmployee(null);
        setShowCreateForm(false);
        setEditingEmployee(employee);
      }}
    >
      Edit
    </button>
    <button
  type="button"
  onClick={() => {
    setSelectedEmployee(null);
    setEditingEmployee(null);
    setShowCreateForm(false);
    setBalanceEmployee(employee);
  }}
>
  Leave Balances
</button>
  </div>
</td>
                  </tr>
                ))}

                {filteredEmployees.length === 0 && (
                  <tr>
                    <td colSpan={6}>No employees found.</td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>

          <div className="employees-pagination">
            <span>Page {page + 1}</span>

            <div>
              <button
                type="button"
                disabled={page === 0}
                onClick={() => setPage((value) => value - 1)}
              >
                Previous
              </button>

              <button
                type="button"
                disabled={employees.length < PAGE_SIZE}
                onClick={() => setPage((value) => value + 1)}
              >
                Next
              </button>
            </div>
          </div>
        </>
      )}

      {selectedEmployee && (
        <div
    ref={detailsRef}
    className="employees-detail"
    role="region"
    aria-label="Selected employee details"
  >
          <div className="employees-detail-header">
            <h2>Employee Details</h2>
            <button
              type="button"
              onClick={() => setSelectedEmployee(null)}
            >
              Close
            </button>
          </div>

          <p>
            <strong>Name:</strong>{" "}
            {selectedEmployee.first_name}{" "}
            {selectedEmployee.last_name}
          </p>
          <p><strong>Email:</strong> {selectedEmployee.email}</p>
          <p>
            <strong>Job Title:</strong>{" "}
            {selectedEmployee.job_title || "Not specified"}
          </p>
          <p>
            <strong>Department:</strong>{" "}
            {selectedEmployee.department}
          </p>
          <p>
            <strong>Country:</strong> {selectedEmployee.country}
          </p>
          <p>
            <strong>Start Date:</strong>{" "}
            {selectedEmployee.employment_start_date}
          </p>
          <p>
            <strong>Approver:</strong>{" "}
            {selectedEmployee.is_approver ? "Yes" : "No"}
          </p>
        </div>
      )}
    </section>
  );
}
