
-- Phase 7: Department Leave Utilization
-- Read-only PostgreSQL analytics

WITH employee_leave AS (
    SELECT
        e.id AS employee_id,
        e.department,
        e.country,
        lb.period_year,
        SUM(lb.entitled_days + lb.carryover_days + lb.adjustment_days)
            AS total_entitlement,
        SUM(lb.used_days) AS total_used,
        SUM(lb.pending_days) AS total_pending,
        SUM(
            lb.entitled_days
            + lb.carryover_days
            + lb.adjustment_days
            - lb.used_days
            - lb.pending_days
        ) AS total_available
    FROM employees e
    INNER JOIN leave_balances lb
        ON lb.employee_id = e.id
    WHERE lb.period_year = 2026
    GROUP BY
        e.id,
        e.department,
        e.country,
        lb.period_year
),
department_summary AS (
    SELECT
        department,
        country,
        COUNT(*) AS employees_with_balances,
        ROUND(SUM(total_entitlement), 2) AS entitlement_days,
        ROUND(SUM(total_used), 2) AS used_days,
        ROUND(SUM(total_pending), 2) AS pending_days,
        ROUND(SUM(total_available), 2) AS available_days,
        ROUND(
            100.0 * SUM(total_used)
            / NULLIF(SUM(total_entitlement), 0),
            2
        ) AS utilization_percentage
    FROM employee_leave
    GROUP BY department, country
)
SELECT
    *,
    DENSE_RANK() OVER (
        PARTITION BY country
        ORDER BY utilization_percentage DESC NULLS LAST
    ) AS utilization_rank
FROM department_summary
ORDER BY country, utilization_rank, department;
