import math
import os
import json
import urllib.parse
from typing import Optional
from markupsafe import Markup

from fastapi import FastAPI, Request, status
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.middleware.sessions import SessionMiddleware
from werkzeug.security import generate_password_hash, check_password_hash
import mysql.connector

from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Initialize FastAPI App
app = FastAPI(title="SaaS Admin Portal")

# Secret key for session signing
SECRET_KEY = os.getenv("SECRET_KEY", "secretkey")
app.add_middleware(SessionMiddleware, secret_key=SECRET_KEY)

# Mount Static Files
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
app.mount("/static", StaticFiles(directory=os.path.join(BASE_DIR, "static")), name="static")

# Database Connection Helper
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_USER = os.getenv("DB_USER", "root")
DB_PASS = os.getenv("DB_PASS", "")
DB_NAME = os.getenv("DB_NAME", "saas_fastapi")


def get_db():
    return mysql.connector.connect(
        host=DB_HOST,
        user=DB_USER,
        passwd=DB_PASS,
        db=DB_NAME
    )


# Mount REST API Router
from api import api_router
app.include_router(api_router, prefix="/api")


# Compatibility Adapter: Allow templates to access request.args like in Flask
class ArgsAdapter:
    def __init__(self, query_params):
        self._params = query_params

    def get(self, key, default=""):
        val = self._params.get(key)
        return val if val is not None else default

    def to_dict(self, flat=True):
        return dict(self._params)

    def __getitem__(self, key):
        return self._params[key]

    def __contains__(self, key):
        return key in self._params


@property
def _request_args_prop(self: Request):
    if not hasattr(self, "_cached_args"):
        self._cached_args = ArgsAdapter(self.query_params)
    return self._cached_args


Request.args = _request_args_prop


# Flash messaging helper
def flash(request: Request, message: str, category: str = "message"):
    if "_flashes" not in request.session:
        request.session["_flashes"] = []
    request.session["_flashes"].append(message)


def get_flashed_messages_helper(request: Request):
    def _getter():
        return request.session.pop("_flashes", [])
    return _getter


# Custom url_for helper to support both Flask ('filename') and FastAPI ('path') conventions
def make_url_for(app_instance: FastAPI):
    def custom_url_for(name: str, **kwargs):
        if name == "static" and "filename" in kwargs:
            kwargs["path"] = kwargs.pop("filename")
        try:
            return app_instance.url_path_for(name, **kwargs)
        except Exception:
            if name == "static":
                return f"/static/{kwargs.get('path', '')}"
            return f"/{name.lstrip('/')}"
    return custom_url_for


# Setup Jinja2 Templates
templates = Jinja2Templates(directory=os.path.join(BASE_DIR, "templates"))
templates.env.add_extension("jinja2.ext.do")
templates.env.globals["url_for"] = make_url_for(app)
templates.env.filters["urlencode"] = lambda d: urllib.parse.urlencode(d)
templates.env.filters["tojson"] = lambda obj: Markup(json.dumps(obj, default=str))


def render_template(request: Request, template_name: str, context: Optional[dict] = None):
    ctx = {
        "get_flashed_messages": get_flashed_messages_helper(request),
    }
    if context:
        ctx.update(context)
    try:
        return templates.TemplateResponse(request=request, name=template_name, context=ctx)
    except TypeError:
        ctx["request"] = request
        return templates.TemplateResponse(template_name, ctx)


# -----------------------------------------------------------------------------
# Authentication Routes
# -----------------------------------------------------------------------------

@app.get("/")
def home(request: Request):
    if "username" in request.session:
        return RedirectResponse(url="/dashboard", status_code=status.HTTP_303_SEE_OTHER)
    return RedirectResponse(url="/login", status_code=status.HTTP_303_SEE_OTHER)


@app.get("/register", response_class=HTMLResponse)
def register_page(request: Request):
    if "username" in request.session:
        return RedirectResponse(url="/dashboard", status_code=status.HTTP_303_SEE_OTHER)
    return render_template(request, "saas-register.html")


@app.post("/register")
async def register(request: Request):
    if "username" in request.session:
        return RedirectResponse(url="/dashboard", status_code=status.HTTP_303_SEE_OTHER)

    form = await request.form()
    username = form.get("username", "").strip()
    email = form.get("email", "").strip()
    raw_password = form.get("password", "")
    hashed_password = generate_password_hash(raw_password)

    conn = get_db()
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute("SELECT * FROM users WHERE username = %s OR email = %s", (username, email))
        existing_user = cursor.fetchone()

        if existing_user:
            return HTMLResponse(content="username / email already exists . . .", status_code=400)

        cursor.execute(
            "INSERT INTO users (username, email, password) VALUES (%s, %s, %s)",
            (username, email, hashed_password)
        )
        conn.commit()
        return RedirectResponse(url="/login", status_code=status.HTTP_303_SEE_OTHER)
    finally:
        cursor.close()
        conn.close()


@app.get("/login", response_class=HTMLResponse)
def login_page(request: Request):
    if "username" in request.session:
        return RedirectResponse(url="/dashboard", status_code=status.HTTP_303_SEE_OTHER)
    return render_template(request, "saas-login.html")


@app.post("/login")
async def login(request: Request):
    form = await request.form()
    username = form.get("username", "").strip()
    password = form.get("password", "")

    conn = get_db()
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute("SELECT * FROM users WHERE username = %s", (username,))
        user = cursor.fetchone()

        if user and check_password_hash(user["password"], password):
            request.session["username"] = user["username"]
            return RedirectResponse(url="/dashboard", status_code=status.HTTP_303_SEE_OTHER)
        else:
            flash(request, "Invalid Credntials . . . ")
            return RedirectResponse(url="/login", status_code=status.HTTP_303_SEE_OTHER)
    finally:
        cursor.close()
        conn.close()


@app.get("/logout")
def logout(request: Request):
    request.session.pop("username", None)
    return RedirectResponse(url="/login", status_code=status.HTTP_303_SEE_OTHER)


# -----------------------------------------------------------------------------
# Dashboard & Analytics
# -----------------------------------------------------------------------------

@app.get("/dashboard", response_class=HTMLResponse)
def dashboard(request: Request):
    if "username" not in request.session or request.session["username"] != "admin":
        return RedirectResponse(url="/login", status_code=status.HTTP_303_SEE_OTHER)

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
        """)
        user_data = cursor.fetchall()

        cursor.execute("""
            SELECT 
                MONTH(start_date) AS month,
                COUNT(*) AS subscription_count
            FROM subscriptions
            WHERE plan_id IS NOT NULL
            GROUP BY MONTH(start_date)
        """)
        sub_data = cursor.fetchall()

        return render_template(
            request,
            "saas-dashboard.html",
            {
                "total_customers": total_customers,
                "active_subs": active_subs,
                "incomplete_subs": incomplete_subs,
                "total_plans": total_plans,
                "user_data": user_data,
                "sub_data": sub_data,
            }
        )
    finally:
        cursor.close()
        conn.close()


# -----------------------------------------------------------------------------
# Plans Management
# -----------------------------------------------------------------------------

@app.get("/plans", response_class=HTMLResponse)
def plans(request: Request):
    if "username" not in request.session or request.session["username"] != "admin":
        return RedirectResponse(url="/login", status_code=status.HTTP_303_SEE_OTHER)

    conn = get_db()
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute("SELECT * FROM plans")
        plans_list = cursor.fetchall()
        return render_template(request, "saas-plans.html", {"plans": plans_list})
    finally:
        cursor.close()
        conn.close()


@app.post("/plans/add")
async def add_plan(request: Request):
    if "username" not in request.session or request.session["username"] != "admin":
        return RedirectResponse(url="/login", status_code=status.HTTP_303_SEE_OTHER)

    form = await request.form()
    name = form.get("name")
    price = form.get("price")
    description = form.get("description")
    max_projects = form.get("max_projects")
    max_team_size = form.get("max_team_size")
    target_user = form.get("target_user")

    conn = get_db()
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute("""
            INSERT INTO plans (name, price, description, max_projects, max_team_size, target_user)
            VALUES (%s, %s, %s, %s, %s, %s)
        """, (name, price, description, max_projects, max_team_size, target_user))
        conn.commit()
        flash(request, "New plan added successfully.")
        return RedirectResponse(url="/plans", status_code=status.HTTP_303_SEE_OTHER)
    finally:
        cursor.close()
        conn.close()


@app.post("/plans/edit/{plan_id}")
async def edit_plan(plan_id: int, request: Request):
    if "username" not in request.session or request.session["username"] != "admin":
        return RedirectResponse(url="/login", status_code=status.HTTP_303_SEE_OTHER)

    form = await request.form()
    name = form.get("name")
    price = form.get("price")
    description = form.get("description")
    max_projects = form.get("max_projects")
    max_team_size = form.get("max_team_size")
    target_user = form.get("target_user")

    conn = get_db()
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute("""
            UPDATE plans
            SET name=%s, price=%s, description=%s,
                max_projects=%s, max_team_size=%s, target_user=%s
            WHERE id=%s
        """, (name, price, description, max_projects, max_team_size, target_user, plan_id))
        conn.commit()
        flash(request, "Plan updated successfully.")
        return RedirectResponse(url="/plans", status_code=status.HTTP_303_SEE_OTHER)
    finally:
        cursor.close()
        conn.close()


@app.post("/plans/delete/{plan_id}")
def delete_plan(plan_id: int, request: Request):
    if "username" not in request.session or request.session["username"] != "admin":
        return RedirectResponse(url="/login", status_code=status.HTTP_303_SEE_OTHER)

    conn = get_db()
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute("DELETE FROM plans WHERE id = %s", (plan_id,))
        conn.commit()
        flash(request, "Plan deleted successfully.")
        return RedirectResponse(url="/plans", status_code=status.HTTP_303_SEE_OTHER)
    finally:
        cursor.close()
        conn.close()


# -----------------------------------------------------------------------------
# Customers Page
# -----------------------------------------------------------------------------

@app.get("/customers", response_class=HTMLResponse)
def customers(request: Request):
    if "username" not in request.session or request.session["username"] != "admin":
        return RedirectResponse(url="/login", status_code=status.HTTP_303_SEE_OTHER)

    try:
        page = int(request.query_params.get("page", 1))
        if page < 1:
            page = 1
    except ValueError:
        page = 1

    per_page = 10
    offset = (page - 1) * per_page
    search = request.query_params.get("search", "").strip()
    subscription = request.query_params.get("subscription", "")
    sort_order = request.query_params.get("sort", "desc").lower()
    date_start = request.query_params.get("date_start", "").strip()
    date_end = request.query_params.get("date_end", "").strip()

    where_clauses = []
    params = []

    if search:
        like = f"%{search}%"
        where_clauses.append("(u.username LIKE %s OR u.email LIKE %s OR p.name LIKE %s)")
        params += [like] * 3

    if subscription:
        if subscription.lower() == "free":
            where_clauses.append("s.plan_id IS NULL")
        else:
            where_clauses.append("p.name = %s")
            params.append(subscription)

    if date_start:
        where_clauses.append("DATE(u.created_at) >= %s")
        params.append(date_start)

    if date_end:
        where_clauses.append("DATE(u.created_at) <= %s")
        params.append(date_end)

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

        prev_page = page - 1 if page > 1 else None
        next_page = page + 1 if page < total_pages else None

        sort_dir = "ASC" if sort_order == "asc" else "DESC"
        data_query = f"""
            SELECT u.username, u.email, u.created_at,
                   CASE WHEN s.plan_id IS NULL THEN 'Free' ELSE p.name END AS subscription_type
            FROM users u
            LEFT JOIN subscriptions s ON s.user_id = u.id
            LEFT JOIN plans p ON p.id = s.plan_id
            {where_sql}
            ORDER BY u.created_at {sort_dir}
            LIMIT %s OFFSET %s
        """
        cursor.execute(data_query, params + [per_page, offset])
        customer_rows = cursor.fetchall()

        return render_template(
            request,
            "saas-customers.html",
            {
                "customers": customer_rows,
                "current_page": page,
                "total_pages": total_pages,
                "prev_page": prev_page,
                "next_page": next_page,
            }
        )
    finally:
        cursor.close()
        conn.close()


# -----------------------------------------------------------------------------
# Subscriptions Page
# -----------------------------------------------------------------------------

@app.get("/subscriptions", response_class=HTMLResponse)
def subscriptions(request: Request):
    if "username" not in request.session or request.session["username"] != "admin":
        return RedirectResponse(url="/login", status_code=status.HTTP_303_SEE_OTHER)

    search = request.query_params.get("search", "").strip()
    plan_filter = request.query_params.get("plan", "").strip()
    date_start = request.query_params.get("date_start", "").strip()
    date_end = request.query_params.get("date_end", "").strip()

    try:
        page = int(request.query_params.get("page", 1))
        if page < 1:
            page = 1
    except ValueError:
        page = 1

    per_page = 5
    offset = (page - 1) * per_page

    where_clauses = []
    params = []

    if search:
        where_clauses.append("(u.username LIKE %s OR u.email LIKE %s OR p.name LIKE %s)")
        params += [f"%{search}%"] * 3

    if plan_filter:
        where_clauses.append("(p.name = %s OR (p.name IS NULL AND %s = 'Free'))")
        params += [plan_filter, plan_filter]

    if date_start:
        where_clauses.append("s.start_date >= %s")
        params.append(date_start)

    if date_end:
        where_clauses.append("s.start_date <= %s")
        params.append(date_end)

    where_sql = " AND ".join(where_clauses)
    if where_sql:
        where_sql = "WHERE " + where_sql

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

        query_params_with_paging = list(params) + [per_page, offset]

        data_query = f"""
            SELECT p.name AS plan_name, u.username, u.email, s.start_date
            FROM subscriptions s
            LEFT JOIN plans p ON p.id = s.plan_id
            LEFT JOIN users u ON u.id = s.user_id
            {where_sql}
            ORDER BY s.start_date DESC
            LIMIT %s OFFSET %s
        """
        cursor.execute(data_query, query_params_with_paging)
        details = cursor.fetchall()

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

        return render_template(
            request,
            "saas-subscriptions.html",
            {
                "current_page": page,
                "total_pages": total_pages,
                "plan_names": plan_names,
                "plan_data": plan_data,
                "months": months,
                "details": details,
            }
        )
    finally:
        cursor.close()
        conn.close()


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)
