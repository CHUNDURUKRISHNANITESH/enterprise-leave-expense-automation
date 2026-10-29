
-- Phase 7: Approval Turnaround Analytics
-- Read-only PostgreSQL report

WITH approval_details AS (
    SELECT
        a.id AS approval_id,
        a.approver_employee_id,
        COALESCE(e.department, 'Unassigned') AS department,
        COALESCE(e.country, 'N/A') AS country,

        CASE
            WHEN a.leave_request_id IS NOT NULL THEN 'LEAVE'
            ELSE 'EXPENSE'
        END AS request_type,

        a.status,
        a.assigned_at,
        a.decided_at,

        CASE
            WHEN a.assigned_at IS NOT NULL
             AND a.decided_at >= a.assigned_at
             AND a.status IN ('APPROVED', 'REJECTED')
            THEN EXTRACT(
                EPOCH FROM (a.decided_at - a.assigned_at)
            ) / 3600.0
        END AS turnaround_hours,

        CASE
            WHEN a.status = 'PENDING'
             AND a.assigned_at IS NOT NULL
            THEN EXTRACT(
                EPOCH FROM (CURRENT_TIMESTAMP - a.assigned_at)
            ) / 3600.0
        END AS pending_hours

    FROM approval_steps a
    LEFT JOIN employees e
        ON a.approver_employee_id = e.id
),

approver_summary AS (
    SELECT
        approver_employee_id,
        department,
        country,
        request_type,

        COUNT(*) AS total_steps,

        COUNT(*) FILTER (
            WHERE status = 'APPROVED'
        ) AS approved_count,

        COUNT(*) FILTER (
            WHERE status = 'REJECTED'
        ) AS rejected_count,

        COUNT(*) FILTER (
            WHERE status = 'PENDING'
        ) AS pending_count,

        COUNT(turnaround_hours) AS timed_decisions,

        ROUND(
            AVG(turnaround_hours), 2
        ) AS avg_turnaround_hours,

        ROUND(
            MAX(turnaround_hours), 2
        ) AS max_turnaround_hours,

        ROUND(
            AVG(pending_hours), 2
        ) AS avg_pending_hours

    FROM approval_details
    GROUP BY
        approver_employee_id,
        department,
        country,
        request_type
),

ranked_approvers AS (
    SELECT
        *,
        DENSE_RANK() OVER (
            PARTITION BY country, request_type
            ORDER BY avg_turnaround_hours ASC NULLS LAST
        ) AS turnaround_rank
    FROM approver_summary
)

SELECT
    approver_employee_id,
    department,
    country,
    request_type,
    total_steps,
    approved_count,
    rejected_count,
    pending_count,
    timed_decisions,
    avg_turnaround_hours,
    max_turnaround_hours,
    avg_pending_hours,
    turnaround_rank
FROM ranked_approvers
ORDER BY
    country,
    request_type,
    turnaround_rank,
    approver_employee_id;
