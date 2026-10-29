
-- Phase 7: Expense Analytics by Department and Category
-- Read-only PostgreSQL report

WITH expense_details AS (
    SELECT
        ec.id AS claim_id,
        e.department,
        ec.country,
        ec.currency,
        ec.status,
        el.category,
        el.line_amount,
        ec.total_amount,
        ec.expense_date
    FROM expense_claims ec
    INNER JOIN employees e
        ON ec.employee_id = e.id
    INNER JOIN expense_lines el
        ON el.claim_id = ec.id
    WHERE ec.expense_date >= DATE '2026-01-01'
      AND ec.expense_date < DATE '2027-01-01'
),

category_summary AS (
    SELECT
        department,
        country,
        currency,
        category,
        COUNT(DISTINCT claim_id) AS total_claims,
        COUNT(*) AS total_expense_lines,

        ROUND(SUM(line_amount), 2) AS total_spending,

        ROUND(
            SUM(line_amount) FILTER (
                WHERE status IN (
                    'APPROVED',
                    'REIMBURSEMENT_PENDING',
                    'REIMBURSED'
                )
            ),
            2
        ) AS approved_spending,

        ROUND(
            SUM(line_amount) FILTER (
                WHERE status = 'REJECTED'
            ),
            2
        ) AS rejected_spending,

        ROUND(AVG(line_amount), 2) AS average_line_amount

    FROM expense_details
    GROUP BY
        department,
        country,
        currency,
        category
),

ranked_categories AS (
    SELECT
        *,
        DENSE_RANK() OVER (
            PARTITION BY country, currency
            ORDER BY total_spending DESC
        ) AS spending_rank,

        ROUND(
            100.0 * total_spending
            / NULLIF(
                SUM(total_spending) OVER (
                    PARTITION BY country, currency
                ),
                0
            ),
            2
        ) AS spending_percentage

    FROM category_summary
)

SELECT
    department,
    country,
    currency,
    category,
    total_claims,
    total_expense_lines,
    total_spending,
    COALESCE(approved_spending, 0) AS approved_spending,
    COALESCE(rejected_spending, 0) AS rejected_spending,
    average_line_amount,
    spending_percentage,
    spending_rank
FROM ranked_categories
ORDER BY
    country,
    currency,
    spending_rank,
    department,
    category;
