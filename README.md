# SaaS Admin Portal (FastAPI Edition)

FastAPI conversion of the SaaS Admin & Subscription Management system.

---

## 🚀 Features
- **FastAPI Backend**: High-performance asynchronous REST and HTML routes.
- **Dedicated Database**: `saas_fastapi` (completely isolated from the Flask project).
- **Session Authentication**: Role-based access control with secure cookie sessions.
- **Admin Dashboard**: Live metrics for customers, subscriptions, and plans with Chart.js visualizations.
- **Plan Management**: Create, edit, and delete subscription tiers with custom quotas.
- **Customer Directory**: Search, filter by plan, date-range filters, and pagination.
- **Subscription Analytics**: Filterable subscription listings and 12-month visual growth trend charts.
- **100% Password Hash Compatible**: Uses `werkzeug.security` with pre-configured admin account.

---

## 🛠️ Step-by-Step Setup

### 1. Open the Project in VS Code
Open VS Code, choose **File > Open Folder...**, and select:
```
D:\Study\Project\saas-fastapi
```

### 2. Set Up a Virtual Environment & Install Dependencies
In the VS Code terminal (`Ctrl + ~`):
```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

### 3. Initialize the Fresh Database (`saas_fastapi`)

You have two easy ways to initialize the database:

#### Option A: Automated Setup Script (Recommended)
Run:
```powershell
python init_db.py
```
This script will:
1. Connect to your MySQL server (prompting for host/user/password if needed).
2. Create the fresh database: `saas_fastapi`.
3. Create all tables (`users`, `plans`, `subscriptions`).
4. Insert the 4 default subscription tiers (`Free`, `Basic`, `Pro`, `Premium`).
5. Create the default **admin** user account:
   - **Username**: `admin`
   - **Password**: `admin123`
6. Save your database settings into `.env` automatically.

#### Option B: Run SQL Directly in MySQL Workbench or CLI
You can execute the queries inside [`sql.txt`](sql.txt).

---

### 4. (Optional) Populate Mock Customers & Subscriptions
To generate 50 mock customer accounts and subscriptions over the past 6 months to populate the dashboard charts:
```powershell
python seed_data.py
```

---

## ▶️ Running the Application

### Option 1: Python Runner Script
```powershell
python run.py
```

### Option 2: Uvicorn Direct
```powershell
uvicorn main:app --reload
```

### Option 3: VS Code Debugger (F5)
1. Open the Run and Debug tab (`Ctrl + Shift + D`).
2. Select **FastAPI: Run SaaS Project**.
3. Press **F5**.

---

## 🌐 Accessing the Application
- **Main Portal**: [http://127.0.0.1:8000](http://127.0.0.1:8000)
- **Admin Credentials**:
  - **Username**: `admin`
  - **Password**: `admin123`
- **Interactive Swagger Docs**: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)
- **ReDoc Documentation**: [http://127.0.0.1:8000/redoc](http://127.0.0.1:8000/redoc)
