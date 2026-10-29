
-- Phase 7: Reimbursement Analytics
-- Read-only PostgreSQL report

WITH reimbursement_details AS (
    SELECT
        r.id AS reimbursement_id,
        e.department,
        ec.country,
        r.currency,
        r.amount,
        r.status,
        r.initiated_at,
        r.paid_at,

        CASE
            WHEN r.status = 'PAID'
             AND r.initiated_at IS NOT NULL
             AND r.paid_at >= r.initiated_at
            THEN EXTRACT(
                EPOCH FROM (r.paid_at - r.initiated_at)
            ) / 3600.0
        END AS processing_hours

    FROM reimbursements r
    INNER JOIN expense_claims ec
        ON ec.id = r.claim_id
    INNER JOIN employees e
        ON e.id = ec.employee_id
),

department_summary AS (
    SELECT
        country,
        department,
        currency,

        COUNT(*) AS total_reimbursements,

        COUNT(*) FILTER (
            WHERE status = 'PAID'
        ) AS paid_count,

        COUNT(*) FILTER (
            WHERE status = 'PENDING'
        ) AS pending_count,

        COUNT(*) FILTER (
            WHERE status = 'PROCESSING'
        ) AS processing_count,

        COUNT(*) FILTER (
            WHERE status = 'FAILED'
        ) AS failed_count,

        COUNT(*) FILTER (
            WHERE status = 'CANCELLED'
        ) AS cancelled_count,

        ROUND(SUM(amount), 2) AS total_amount,

        COALESCE(
            ROUND(SUM(amount) FILTER (
                WHERE status = 'PAID'
            ), 2),
            0
        ) AS paid_amount,

        COALESCE(
            ROUND(SUM(amount) FILTER (
                WHERE status = 'FAILED'
            ), 2),
            0
        ) AS failed_amount,

        ROUND(
            100.0 * COUNT(*) FILTER (
                WHERE status = 'PAID'
            ) / NULLIF(COUNT(*), 0),
            2
        ) AS payment_success_percentage,

        ROUND(
            AVG(processing_hours), 2
        ) AS avg_processing_hours

    FROM reimbursement_details
    GROUP BY
        country,
        department,
        currency
),

ranked_summary AS (
    SELECT
        *,
        DENSE_RANK() OVER (
            PARTITION BY country, currency
            ORDER BY paid_amount DESC
        ) AS paid_amount_rank

    FROM department_summary
)

SELECT
    country,
    department,
    currency,
    total_reimbursements,
    paid_count,
    pending_count,
    processing_count,
    failed_count,
    cancelled_count,
    total_amount,
    paid_amount,
    failed_amount,
    payment_success_percentage,
    avg_processing_hours,
    paid_amount_rank
FROM ranked_summary
ORDER BY
    country,
    currency,
    paid_amount_rank,
    department;
