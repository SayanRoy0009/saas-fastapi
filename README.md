# SaaS Admin Portal (FastAPI Edition)

FastAPI conversion of the SaaS Admin & Subscription Management system.

---

## 🚀 Features
- **FastAPI Backend**: High-performance asynchronous REST and HTML routes.
- **Dedicated Database**: `saas_fastapi` schema with automatic migrations & seeding.
- **REST APIs**: Full JSON API endpoints under `/api/...` with auto-generated Swagger UI docs.
- **Session Authentication**: Role-based access control with secure cookie sessions.
- **Admin Dashboard**: Live metrics for customers, subscriptions, and plans with Chart.js visualizations.
- **Plan Management**: Create, edit, and delete subscription tiers with custom quotas.
- **Customer Directory**: Search, filter by plan, date-range filters, and pagination.
- **Subscription Analytics**: Filterable subscription listings and 12-month visual growth trend charts.
- **Docker Ready**: 1-command startup including automated MySQL container provisioning.

---

## 🐳 Option A: 1-Command Startup with Docker (Recommended for Anyone Pulling This Repo)

If you have Docker installed, you don't need Python or MySQL installed on your machine!

```bash
# Clone the repository
git clone https://github.com/SayanRoy0009/saas-fastapi.git
cd saas-fastapi

# Build and start both FastAPI and MySQL containers
docker compose up --build
```

Docker will:
1. Start the MySQL 8.0 container.
2. Automatically run `sql.txt` to initialize tables, tiers, and default admin.
3. Build and launch the FastAPI web app container.
4. Expose the app at **http://localhost:8000**.

To stop the containers:
```bash
docker compose down
```

---

## 🛠️ Option B: Local Setup (Without Docker)

### 1. Open the project in VS Code
```powershell
cd saas-fastapi
```

### 2. Set Up a Virtual Environment & Install Dependencies
```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

### 3. Initialize the Database
Make sure your local MySQL server is running, then run:
```powershell
python init_db.py
```
*(Optional) Seed 50 mock customers and subscriptions for testing:*
```powershell
python seed_data.py
```

### 4. Run the Server
```powershell
python run.py
```
*(Or press **F5** in VS Code to run in debug mode).*

---

## 🌐 Accessing the Application

- **Web App**: [http://127.0.0.1:8000](http://127.0.0.1:8000)
- **Admin Login**:
  - **Username**: `admin`
  - **Password**: `admin123`
- **Interactive Swagger API Docs**: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)
- **ReDoc Documentation**: [http://127.0.0.1:8000/redoc](http://127.0.0.1:8000/redoc)

---

## 📄 License
This project is licensed under the [MIT License](LICENSE).
