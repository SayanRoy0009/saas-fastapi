import math
from typing import Optional, List
from fastapi import APIRouter, HTTPException, Query, status
from pydantic import BaseModel, Field

# We import get_db from main
from main import get_db

api_router = APIRouter(tags=["REST APIs"])


# Helper to convert Decimal and datetime objects for clean JSON responses
def serialize_row(row: dict) -> dict:
    if not row:
        return row
    result = {}
    for k, v in row.items():
        if hasattr(v, "isoformat"):
            result[k] = v.isoformat()
        elif hasattr(v, "__float__"):
            result[k] = float(v)
        else:
            result[k] = v
    return result


def serialize_rows(rows: list) -> list:
    return [serialize_row(r) for r in rows]


# Pydantic Schemas
class PlanBase(BaseModel):
    name: str = Field(..., example="Pro")
    price: float = Field(..., example=24.99)
    description: str = Field(..., example="Best for growing teams")
    max_projects: int = Field(..., example=100)
    max_team_size: int = Field(..., example=50)
    target_user: str = Field(..., example="mid")


class PlanCreate(PlanBase):
    pass


class PlanUpdate(PlanBase):
    pass


# -----------------------------------------------------------------------------
# 1. Dashboard API
# -----------------------------------------------------------------------------
@api_router.get("/dashboard", summary="Get Dashboard KPIs and Monthly Trends")
def get_dashboard_data():
    conn = get_db()
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute("SELECT COUNT(*) AS total_customers FROM users")
        total_customers = cursor.fetchone()["total_customers"]

        cursor.execute("SELECT COUNT(*) AS active_subs FROM subscriptions WHERE plan_id IS NOT NULL")
        active_subs = cursor.fetchone()["active_subs"]

        cursor.execute("SELECT COUNT(*) AS incomplete_subs FROM subscriptions WHERE plan_id IS NULL")
        incomplete_subs = cursor.fetchone()["incomplete_subs"]

        cursor.execute("SELECT COUNT(*) AS total_plans FROM plans")
        total_plans = cursor.fetchone()["total_plans"]

        cursor.execute("""
            SELECT 
                MONTH(created_at) AS month,
                COUNT(*) AS user_count
            FROM users
            GROUP BY MONTH(created_at)
            ORDER BY month ASC
        """)
        user_data = cursor.fetchall()

        cursor.execute("""
            SELECT 
                MONTH(start_date) AS month,
                COUNT(*) AS subscription_count
            FROM subscriptions
            WHERE plan_id IS NOT NULL
            GROUP BY MONTH(start_date)
            ORDER BY month ASC
        """)
        sub_data = cursor.fetchall()

        return {
            "total_customers": total_customers,
            "active_subs": active_subs,
            "incomplete_subs": incomplete_subs,
            "total_plans": total_plans,
            "user_data": serialize_rows(user_data),
            "sub_data": serialize_rows(sub_data),
        }
    finally:
        cursor.close()
        conn.close()


# -----------------------------------------------------------------------------
# 2. Plans API
# -----------------------------------------------------------------------------
@api_router.get("/plans", summary="List All Subscription Plans")
def list_plans():
    conn = get_db()
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute("SELECT * FROM plans ORDER BY price ASC")
        plans = cursor.fetchall()
        return serialize_rows(plans)
    finally:
        cursor.close()
        conn.close()


@api_router.get("/plans/{plan_id}", summary="Get Single Plan Details")
def get_plan(plan_id: int):
    conn = get_db()
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute("SELECT * FROM plans WHERE id = %s", (plan_id,))
        plan = cursor.fetchone()
        if not plan:
            raise HTTPException(status_code=404, detail="Plan not found")
        return serialize_row(plan)
    finally:
        cursor.close()
        conn.close()


@api_router.post("/plans", status_code=status.HTTP_201_CREATED, summary="Create a New Subscription Plan")
def create_plan(plan: PlanCreate):
    conn = get_db()
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute("""
            INSERT INTO plans (name, price, description, max_projects, max_team_size, target_user)
            VALUES (%s, %s, %s, %s, %s, %s)
        """, (plan.name, plan.price, plan.description, plan.max_projects, plan.max_team_size, plan.target_user))
        conn.commit()
        new_id = cursor.lastrowid
        cursor.execute("SELECT * FROM plans WHERE id = %s", (new_id,))
        return serialize_row(cursor.fetchone())
    finally:
        cursor.close()
        conn.close()


@api_router.put("/plans/{plan_id}", summary="Update a Subscription Plan")
def update_plan(plan_id: int, plan: PlanUpdate):
    conn = get_db()
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute("SELECT id FROM plans WHERE id = %s", (plan_id,))
        if not cursor.fetchone():
            raise HTTPException(status_code=404, detail="Plan not found")

        cursor.execute("""
            UPDATE plans
            SET name=%s, price=%s, description=%s,
                max_projects=%s, max_team_size=%s, target_user=%s
            WHERE id=%s
        """, (plan.name, plan.price, plan.description, plan.max_projects, plan.max_team_size, plan.target_user, plan_id))
        conn.commit()
        cursor.execute("SELECT * FROM plans WHERE id = %s", (plan_id,))
        return serialize_row(cursor.fetchone())
    finally:
        cursor.close()
        conn.close()


@api_router.delete("/plans/{plan_id}", summary="Delete a Subscription Plan")
def delete_plan_api(plan_id: int):
    conn = get_db()
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT id FROM plans WHERE id = %s", (plan_id,))
        if not cursor.fetchone():
            raise HTTPException(status_code=404, detail="Plan not found")
        cursor.execute("DELETE FROM plans WHERE id = %s", (plan_id,))
        conn.commit()
        return {"message": "Plan deleted successfully", "id": plan_id}
    finally:
        cursor.close()
        conn.close()


# -----------------------------------------------------------------------------
# 3. Customers API
# -----------------------------------------------------------------------------
@api_router.get("/customers", summary="Search and Paginate Customers")
def list_customers(
    page: int = Query(1, ge=1, description="Page number"),
    per_page: int = Query(10, ge=1, le=100, description="Items per page"),
    search: Optional[str] = Query(None, description="Search term for username or email"),
    subscription: Optional[str] = Query(None, description="Filter by plan name, e.g. Free, Pro"),
    sort: str = Query("desc", pattern="^(asc|desc)$", description="Sort order by join date (asc/desc)"),
    date_start: Optional[str] = Query(None, description="Filter joined on or after (YYYY-MM-DD)"),
    date_end: Optional[str] = Query(None, description="Filter joined on or before (YYYY-MM-DD)")
):
    offset = (page - 1) * per_page
    where_clauses = []
    params = []

    if search:
        search_term = f"%{search.strip()}%"
        where_clauses.append("(u.username LIKE %s OR u.email LIKE %s OR p.name LIKE %s)")
        params += [search_term] * 3

    if subscription:
        sub = subscription.strip()
        if sub.lower() == "free":
            where_clauses.append("s.plan_id IS NULL")
        else:
            where_clauses.append("p.name = %s")
            params.append(sub)

    if date_start:
        where_clauses.append("DATE(u.created_at) >= %s")
        params.append(date_start.strip())

    if date_end:
        where_clauses.append("DATE(u.created_at) <= %s")
        params.append(date_end.strip())

    where_sql = "WHERE " + " AND ".join(where_clauses) if where_clauses else ""

    conn = get_db()
    cursor = conn.cursor(dictionary=True)
    try:
        count_query = f"""
            SELECT COUNT(*) AS total
            FROM users u
            LEFT JOIN subscriptions s ON s.user_id = u.id
            LEFT JOIN plans p ON p.id = s.plan_id
            {where_sql}
        """
        cursor.execute(count_query, params)
        total = cursor.fetchone()["total"]
        total_pages = (total + per_page - 1) // per_page if total > 0 else 1

        sort_dir = "ASC" if sort.lower() == "asc" else "DESC"
        data_query = f"""
            SELECT u.id, u.username, u.email, u.created_at,
                   CASE WHEN s.plan_id IS NULL THEN 'Free' ELSE p.name END AS subscription_type
            FROM users u
            LEFT JOIN subscriptions s ON s.user_id = u.id
            LEFT JOIN plans p ON p.id = s.plan_id
            {where_sql}
            ORDER BY u.created_at {sort_dir}
            LIMIT %s OFFSET %s
        """
        cursor.execute(data_query, params + [per_page, offset])
        rows = cursor.fetchall()

        return {
            "total": total,
            "page": page,
            "per_page": per_page,
            "total_pages": total_pages,
            "customers": serialize_rows(rows)
        }
    finally:
        cursor.close()
        conn.close()


# -----------------------------------------------------------------------------
# 4. Subscriptions API & Chart Data
# -----------------------------------------------------------------------------
@api_router.get("/subscriptions", summary="List and Paginate Subscription Records")
def list_subscriptions(
    page: int = Query(1, ge=1),
    per_page: int = Query(5, ge=1, le=50),
    search: Optional[str] = Query(None),
    plan: Optional[str] = Query(None),
    date_start: Optional[str] = Query(None),
    date_end: Optional[str] = Query(None)
):
    offset = (page - 1) * per_page
    where_clauses = []
    params = []

    if search:
        search_term = f"%{search.strip()}%"
        where_clauses.append("(u.username LIKE %s OR u.email LIKE %s OR p.name LIKE %s)")
        params += [search_term] * 3

    if plan:
        plan_filter = plan.strip()
        where_clauses.append("(p.name = %s OR (p.name IS NULL AND %s = 'Free'))")
        params += [plan_filter, plan_filter]

    if date_start:
        where_clauses.append("s.start_date >= %s")
        params.append(date_start.strip())

    if date_end:
        where_clauses.append("s.start_date <= %s")
        params.append(date_end.strip())

    where_sql = "WHERE " + " AND ".join(where_clauses) if where_clauses else ""

    conn = get_db()
    cursor = conn.cursor(dictionary=True)
    try:
        count_query = f"""
            SELECT COUNT(*) AS total_count
            FROM subscriptions s
            LEFT JOIN plans p ON p.id = s.plan_id
            LEFT JOIN users u ON u.id = s.user_id
            {where_sql}
        """
        cursor.execute(count_query, params)
        total_count = cursor.fetchone()["total_count"]
        total_pages = math.ceil(total_count / per_page) if total_count else 1

        data_query = f"""
            SELECT s.id, p.name AS plan_name, u.username, u.email, s.start_date
            FROM subscriptions s
            LEFT JOIN plans p ON p.id = s.plan_id
            LEFT JOIN users u ON u.id = s.user_id
            {where_sql}
            ORDER BY s.start_date DESC
            LIMIT %s OFFSET %s
        """
        cursor.execute(data_query, params + [per_page, offset])
        details = cursor.fetchall()

        return {
            "total_count": total_count,
            "page": page,
            "per_page": per_page,
            "total_pages": total_pages,
            "subscriptions": serialize_rows(details)
        }
    finally:
        cursor.close()
        conn.close()


@api_router.get("/subscriptions/chart", summary="Get 12-Month Subscription Data for Charts")
def get_subscription_chart_data():
    conn = get_db()
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute("""
            SELECT MONTH(start_date) AS month,
                   CASE WHEN plan_id IS NULL THEN 'Free' ELSE p.name END AS plan_name,
                   COUNT(*) AS count
            FROM subscriptions s
            LEFT JOIN plans p ON p.id = s.plan_id
            GROUP BY MONTH(start_date), plan_name
            ORDER BY MONTH(start_date)
        """)
        raw = cursor.fetchall()

        months = list(range(1, 13))
        plan_names = sorted(list(set(row["plan_name"] for row in raw))) if raw else ["Free", "Basic", "Pro", "Premium"]
        plan_data = {plan: [0] * 12 for plan in plan_names}

        for row in raw:
            m = row["month"] - 1
            if 0 <= m < 12 and row["plan_name"] in plan_data:
                plan_data[row["plan_name"]][m] = row["count"]

        return {
            "months": months,
            "plan_names": plan_names,
            "plan_data": plan_data
        }
    finally:
        cursor.close()
        conn.close()
