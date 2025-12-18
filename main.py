
from fastapi import FastAPI, Depends, HTTPException, status, Body, APIRouter
from fastapi.security import OAuth2PasswordRequestForm
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import List, Optional
from datetime import datetime, timedelta, date
import pytz
from pydantic import BaseModel
import os

from . import models
from .database import engine, get_db
from . import auth

# Create tables if not exist (handled by seed, but good safety)
models.Base.metadata.create_all(bind=engine)
# 18. satırdan sonra buraya yapıştır:
app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
api_router = APIRouter(prefix="/api")

ISTANBUL_TZ = pytz.timezone("Europe/Istanbul")

# --- Pydantic Models ---

class EmployeeCreate(BaseModel):
    username: str
    password: str
    full_name: str
    role: str = "employee"

class InstagramAccountCreate(BaseModel):
    username: str
    password: str

class QuotaRequest(BaseModel):
    employee_id: int
    amount: int

class BulkAccountCreate(BaseModel):
    accounts: List[InstagramAccountCreate]

class AssignRequest(BaseModel):
    employee_id: int
    limit: Optional[int] = 10

class ReportCreate(BaseModel):
    instagram_account_id: int
    follower_count: int

class Token(BaseModel):
    access_token: str
    token_type: str
    role: str

class AccountOut(BaseModel):
    id: int
    username: str
    
    class Config:
        orm_mode = True

class AccountWithPasswordOut(BaseModel):
    id: int
    username: str
    password: str
    
    class Config:
        orm_mode = True

class EmployeeDashboardData(BaseModel):
    quota: int
    assigned_accounts: List[AccountWithPasswordOut]

class EmployeeOut(BaseModel):
    id: int
    full_name: str
    user_name: str
    visible_password: Optional[str] = None
    account_quota: int = 0
    assigned_count: int = 0

class EmployeeDetailOut(BaseModel):
    id: int
    full_name: str
    user_name: str
    assigned_accounts: List[AccountWithPasswordOut]

class ReportOut(BaseModel):
    id: int
    employee_id: int
    instagram_account_id: int
    date: str
    follower_count: int
    locked: bool
    account_username: str
    employee_name: str

# --- Helpers ---

def get_today_date():
    return datetime.now(ISTANBUL_TZ).date()

def lock_past_reports(db: Session):
    """Locks any unlocked report that is not from today."""
    today = get_today_date()
    # Find records where date < today and locked=False
    db.query(models.DailyReport).filter(
        models.DailyReport.date < today,
        models.DailyReport.locked == False
    ).update({models.DailyReport.locked: True}, synchronize_session=False)
    db.commit()

# --- Auth ---

from fastapi import Request

def create_audit_log(db: Session, user_id: int, action: str, details: str, ip: str):
    try:
        log = models.AuditLog(user_id=user_id, action=action, details=details, ip_address=ip)
        db.add(log)
        db.commit()
    except Exception as e:
        print(f"Audit log error: {e}")

@api_router.post("/login", response_model=Token)
async def login_for_access_token(request: Request, form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = db.query(models.User).filter(models.User.username == form_data.username).first()
    if not user or not auth.verify_password(form_data.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Log Login
    create_audit_log(db, user.id, "LOGIN", "User logged in", request.client.host)

    access_token_expires = timedelta(minutes=auth.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = auth.create_access_token(
        data={"sub": user.username, "role": user.role}, expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer", "role": user.role}

# --- Admin Endpoints ---

@app.post("/admin/create-employee")
def create_employee(emp: EmployeeCreate, db: Session = Depends(get_db), current_user: models.User = Depends(auth.get_current_active_admin)):
    # Check if user exists
    if db.query(models.User).filter(models.User.username == emp.username).first():
        raise HTTPException(status_code=400, detail="Username already registered")
    
    # Create User
    hashed_pwd = auth.get_password_hash(emp.password)
    db_user = models.User(username=emp.username, password_hash=hashed_pwd, role=emp.role)
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    
    if emp.role == "employee":
        db_emp = models.Employee(
            user_id=db_user.id, 
            full_name=emp.full_name, 
            account_quota=0,
            visible_password=emp.password
        )
        db.add(db_emp)
        db.commit()
    
    return {"status": "success", "msg": "User created"}

class ResetPasswordRequest(BaseModel):
    employee_id: int
    new_password: str

@app.post("/admin/reset-password")
def reset_password(req: ResetPasswordRequest, db: Session = Depends(get_db), current_user: models.User = Depends(auth.get_current_active_admin)):
    emp = db.query(models.Employee).filter(models.Employee.id == req.employee_id).first()
    if not emp:
        raise HTTPException(status_code=404, detail="Employee not found")
        
    user = emp.user
    if not user:
        raise HTTPException(status_code=404, detail="User account not found")
        
    user.password_hash = auth.get_password_hash(req.new_password)
    emp.visible_password = req.new_password # Update visible
    db.commit()
    return {"status": "success", "msg": "Password updated"}


@app.delete("/admin/delete-employee/{id}")
def delete_employee(id: int, db: Session = Depends(get_db), current_user: models.User = Depends(auth.get_current_active_admin)):
    params_emp_id = id # rename to avoid shadowing built-in id
    
    emp = db.query(models.Employee).filter(models.Employee.id == params_emp_id).first()
    if not emp:
        raise HTTPException(status_code=404, detail="Employee not found")
    
    # Unassign accounts: set assigned_employee_id to NULL
    db.query(models.InstagramAccount).filter(models.InstagramAccount.assigned_employee_id == params_emp_id).update(
        {models.InstagramAccount.assigned_employee_id: None}, synchronize_session=False
    )
    
    # Delete Employee record
    db.delete(emp)
    
    user = db.query(models.User).filter(models.User.id == emp.user_id).first()
    if user:
         db.delete(user)

    db.commit()
    return {"status": "success"}

@app.get("/admin/employees", response_model=List[EmployeeOut])
def list_employees(db: Session = Depends(get_db), current_user: models.User = Depends(auth.get_current_active_admin)):
    emps = db.query(models.Employee).all()
    res = []
    for e in emps:
        # Safety check for orphaned employee records
        u_name = e.user.username if e.user else "Unknown/Deleted"
        
        res.append({
            "id": e.id,
            "full_name": e.full_name,
            "user_name": u_name,
            "account_quota": e.account_quota or 0,
            "assigned_count": len(e.assigned_accounts) if e.assigned_accounts else 0,
            "visible_password": e.visible_password or "******" # Return visible
        })
    return res

@app.get("/admin/employee/{id}", response_model=EmployeeDetailOut)
def get_employee_details(id: int, db: Session = Depends(get_db), current_user: models.User = Depends(auth.get_current_active_admin)):
    emp = db.query(models.Employee).filter(models.Employee.id == id).first()
    if not emp:
        raise HTTPException(status_code=404, detail="Employee not found")
        
    accounts = []
    for acc in emp.assigned_accounts:
        accounts.append({
            "id": acc.id,
            "username": acc.username,
            "password": acc.password or "" # Handle legacy text
        })
        
    return {
        "id": emp.id,
        "full_name": emp.full_name,
        "user_name": emp.user.username,
        "assigned_accounts": accounts
    }

@app.post("/admin/create-instagram-account")
def create_instagram_account(acc: InstagramAccountCreate, db: Session = Depends(get_db), current_user: models.User = Depends(auth.get_current_active_admin)):
    if db.query(models.InstagramAccount).filter(models.InstagramAccount.username == acc.username).first():
        raise HTTPException(status_code=400, detail="Account already exists")
    
    new_acc = models.InstagramAccount(username=acc.username, password=acc.password)
    db.add(new_acc)
    db.commit()
    return {"status": "success"}

@app.post("/admin/assign-accounts")
def assign_accounts(req: AssignRequest, db: Session = Depends(get_db), current_user: models.User = Depends(auth.get_current_active_admin)):
    # Find unassigned accounts
    unassigned = db.query(models.InstagramAccount).filter(models.InstagramAccount.assigned_employee_id == None).limit(req.limit).all()
    
    if not unassigned:
        return {"status": "info", "msg": "No unassigned accounts found"}
    
    for acc in unassigned:
        acc.assigned_employee_id = req.employee_id
    
    db.commit()
    return {"status": "success", "count": len(unassigned)}

@api_router.post("/admin/add-quota")
def add_quota(req: QuotaRequest, db: Session = Depends(get_db), current_user: models.User = Depends(auth.get_current_active_admin)):
    emp = db.query(models.Employee).filter(models.Employee.id == req.employee_id).first()
    if not emp:
        raise HTTPException(status_code=404, detail="Employee not found")
    
    emp.account_quota += req.amount
    db.commit()
    return {"status": "success", "new_quota": emp.account_quota}

@api_router.post("/admin/update-quota")
def update_quota(req: QuotaRequest, db: Session = Depends(get_db), current_user: models.User = Depends(auth.get_current_active_admin)):
    emp = db.query(models.Employee).filter(models.Employee.id == req.employee_id).first()
    if not emp:
        raise HTTPException(status_code=404, detail="Employee not found")
    
    # Here, 'amount' will be treated as the NEW TOTAL quota
    emp.account_quota = req.amount
    db.commit()
    return {"status": "success", "new_quota": emp.account_quota}

@app.delete("/admin/instagram-account/{id}")
def delete_instagram_account(id: int, db: Session = Depends(get_db), current_user: models.User = Depends(auth.get_current_active_admin)):
    acc = db.query(models.InstagramAccount).filter(models.InstagramAccount.id == id).first()
    if not acc:
        raise HTTPException(status_code=404, detail="Account not found")
    
    db.delete(acc)
    db.commit()
    return {"status": "success"}

class NoteRequest(BaseModel):
    content: str

@app.get("/admin/daily-summary")
def daily_summary(db: Session = Depends(get_db), current_user: models.User = Depends(auth.get_current_active_admin)):
    # Trigger late locking
    lock_past_reports(db)
    
    today = get_today_date()
    
    # Aggregate reports
    # Get all reports
    reports = db.query(models.DailyReport).filter(models.DailyReport.date == today).all()
    
    total_followers = sum(r.follower_count for r in reports)
    
    # Return detailed list + header
    data = []
    for r in reports:
        data.append({
            "employee_name": r.employee.full_name,
            "account": r.account.username,
            "count": r.follower_count,
            "locked": r.locked
        })

    # Calculate download stats for last 7 days
    download_stats = []
    end = today
    start = end - timedelta(days=6)
    
    # Simple query for stats
    recs = db.query(models.DownloadRecord).filter(models.DownloadRecord.start_date >= start).all()
    # Group by date
    d_map = {}
    for r in recs:
        d_str = r.start_date.isoformat()
        d_map[d_str] = d_map.get(d_str, 0) + r.count
    
    # Format for UI
    sorted_dates = sorted(d_map.keys(), reverse=True)
    for d in sorted_dates:
        download_stats.append({"date": d, "count": d_map[d]})
        
    return {
        "date": str(today),
        "total_followers": total_followers,
        "reports": data,
        "downloads_by_date": download_stats
    }

@app.get("/general/note")
def get_admin_note(db: Session = Depends(get_db)):
    note = db.query(models.AdminNote).first()
    return {
        "content": note.content if note else "",
        "author": note.author if note else "",
        "updated_at": note.updated_at if note else None
    }

@app.post("/admin/note")
def update_admin_note(req: NoteRequest, db: Session = Depends(get_db), current_user: models.User = Depends(auth.get_current_active_admin)):
    note = db.query(models.AdminNote).first()
    if not note:
        note = models.AdminNote(content=req.content, author=current_user.username)
        db.add(note)
    else:
        note.content = req.content
        note.author = current_user.username # Update author
        note.updated_at = datetime.now()
    db.commit()
    return {"status": "success"}

@app.get("/admin/logs")
def get_audit_logs(limit: int = 50, db: Session = Depends(get_db), current_user: models.User = Depends(auth.get_current_active_admin)):
    logs = db.query(models.AuditLog).order_by(models.AuditLog.timestamp.desc()).limit(limit).all()
    
    res = []
    for l in logs:
        # Get username safely
        uname = l.user.username if l.user else "Unknown"
        res.append({
            "id": l.id,
            "username": uname,
            "action": l.action,
            "details": l.details,
            "ip_address": l.ip_address,
            "timestamp": l.timestamp.strftime("%Y-%m-%d %H:%M:%S")
        })
    return res

@app.get("/admin/all-reports")
def get_all_reports(
    start_date: Optional[str] = None, 
    end_date: Optional[str] = None,
    db: Session = Depends(get_db), 
    current_user: models.User = Depends(auth.get_current_active_admin)
):
    query = db.query(models.DailyReport)
    
    if start_date:
        query = query.filter(models.DailyReport.date >= start_date)
    if end_date:
        query = query.filter(models.DailyReport.date <= end_date)
        
    # Order by date desc
    reports = query.order_by(models.DailyReport.date.desc()).all()
    
    res = []
    for r in reports:
        res.append({
            "id": r.id,
            "date": str(r.date),
            "employee_name": r.employee.full_name,
            "account_username": r.account.username,
            "count": r.follower_count,
            "locked": r.locked
        })
    return res

# --- Employee Endpoints ---

@api_router.get("/employee/dashboard-data", response_model=EmployeeDashboardData)
def get_employee_dashboard_data(db: Session = Depends(get_db), current_user: models.User = Depends(auth.get_current_active_employee)):
    emp = current_user.employee
    accounts = []
    for acc in emp.assigned_accounts:
        accounts.append({
            "id": acc.id,
            "username": acc.username,
            "password": acc.password or ""
        })
    return {
        "quota": emp.account_quota,
        "assigned_accounts": accounts
    }

@app.post("/employee/bulk-create-accounts")
def bulk_create_accounts(req: BulkAccountCreate, db: Session = Depends(get_db), current_user: models.User = Depends(auth.get_current_active_employee)):
    emp = current_user.employee
    current_count = len(emp.assigned_accounts)
    new_count = len(req.accounts)
    
    if current_count + new_count > emp.account_quota:
        raise HTTPException(status_code=400, detail=f"Quota exceeded. You can add max {emp.account_quota - current_count} more accounts.")
        
    for acc in req.accounts:
        # Check duplicate
        if db.query(models.InstagramAccount).filter(models.InstagramAccount.username == acc.username).first():
             raise HTTPException(status_code=400, detail=f"User {acc.username} already exists")
             
        new_acc = models.InstagramAccount(
            username=acc.username, 
            password=acc.password,
            assigned_employee_id=emp.id
        )
        db.add(new_acc)
        
    db.commit()
    return {"status": "success"}

@api_router.get("/employee/accounts", response_model=List[AccountOut])
def get_my_accounts(db: Session = Depends(get_db), current_user: models.User = Depends(auth.get_current_active_employee)):
    return current_user.employee.assigned_accounts

class AccountUpdate(BaseModel):
    username: str
    password: str

@app.put("/employee/account/{account_id}")
def update_account(
    account_id: int, 
    req: AccountUpdate,
    request: Request, 
    db: Session = Depends(get_db), 
    current_user: models.User = Depends(auth.get_current_active_employee)
):
    # Verify ownership
    account = db.query(models.InstagramAccount).filter(models.InstagramAccount.id == account_id).first()
    if not account:
        raise HTTPException(status_code=404, detail="Account not found")
    
    if account.assigned_employee_id != current_user.employee.id:
        raise HTTPException(status_code=403, detail="Not authorized to edit this account")
    
    account.username = req.username
    account.password = req.password
    db.commit()
    
    # Log
    create_audit_log(db, current_user.id, "UPDATE_ACCOUNT", f"Updated account {account.username}", request.client.host)
    
    return {"status": "success"}

@app.post("/employee/report")
def submit_report(rep: ReportCreate, request: Request, db: Session = Depends(get_db), current_user: models.User = Depends(auth.get_current_active_employee)):
    # Trigger late locking (good practice to ensure state is clean)
    lock_past_reports(db)
    
    today = get_today_date()
    
    # Check if account belongs to employee
    acc = db.query(models.InstagramAccount).filter(models.InstagramAccount.id == rep.instagram_account_id).first()
    if not acc or acc.assigned_employee_id != current_user.employee.id:
        raise HTTPException(status_code=403, detail="Not authorized for this account")

    # Check existing report
    existing = db.query(models.DailyReport).filter(
        models.DailyReport.employee_id == current_user.employee.id,
        models.DailyReport.instagram_account_id == acc.id,
        models.DailyReport.date == today
    ).first()

    if existing:
        if existing.locked:
            raise HTTPException(status_code=400, detail="Report is locked")
        existing.follower_count = rep.follower_count
        db.commit()
        # Log
        create_audit_log(db, current_user.id, "UPDATE_REPORT", f"Updated report for {acc.username}: {rep.follower_count}", request.client.host)
        return {"status": "updated"}
    
    report = models.DailyReport(
        employee_id=current_user.employee.id,
        instagram_account_id=acc.id,
        date=today,
        follower_count=rep.follower_count
    )
    db.add(report)
    db.commit()
    
    # Log
    create_audit_log(db, current_user.id, "SUBMIT_REPORT", f"Report for {acc.username}: {rep.follower_count}", request.client.host)

    return {"status": "success"}

@app.get("/employee/report-status")
def get_today_reports(db: Session = Depends(get_db), current_user: models.User = Depends(auth.get_current_active_employee)):
     today = get_today_date()
     reports = db.query(models.DailyReport).filter(
         models.DailyReport.employee_id == current_user.employee.id,
         models.DailyReport.date == today
     ).all()
     
     # Return list of reports
     res = []
     for r in reports:
         res.append({
             "account_id": r.instagram_account_id,
             "count": r.follower_count,
             "locked": r.locked
         })
     return res



# --- Downloads Endpoints ---

class DownloadRecordCreate(BaseModel):
    employee_id: int
    start_date: date
    end_date: date
    count: int

@app.get("/admin/download-stats")
def get_download_stats(
    start_date: Optional[date] = None, 
    end_date: Optional[date] = None,
    db: Session = Depends(get_db), 
    current_user: models.User = Depends(auth.get_current_active_admin)
):
    emps = db.query(models.Employee).all()
    
    # Calculate totals from records
    emp_stats = []
    grand_total = 0
    grand_range_total = 0
    
    for e in emps:
        # Sum all records
        all_recs = e.download_records if e.download_records else []
        total = sum(r.count for r in all_recs)
        grand_total += total
        
        # Sum range specific records
        range_count = 0
        if start_date and end_date:
            # Filter: Logic = Record's start_date should be within the querying window
            # Or strictly: record is *assigned* to this window.
            # Given the flow, we just check if record.start_date is inside [start_date, end_date]
            range_count = sum(r.count for r in all_recs if r.start_date >= start_date and r.end_date <= end_date)
            grand_range_total += range_count
        
        u_name = e.user.username if e.user else "Unknown"
        emp_stats.append({
            "id": e.id,
            "full_name": e.full_name,
            "user_name": u_name,
            "total_downloads": total,
            "range_downloads": range_count
        })
        
    best = max(emp_stats, key=lambda x: x['total_downloads']) if emp_stats else None
    
    # User requested Sum of Quotas, not count of actual accounts
    total_accounts = sum(e.account_quota for e in emps if e.account_quota)

    return {
        "total_downloads": grand_total,
        "total_accounts": total_accounts,
        "range_total": grand_range_total,
        "best_employee": best['full_name'] if best else "-",
        "employees": sorted(emp_stats, key=lambda x: x['total_downloads'], reverse=True)
    }

@app.post("/admin/add-download-record")
def add_download_record(req: DownloadRecordCreate, db: Session = Depends(get_db), current_user: models.User = Depends(auth.get_current_active_admin)):
    emp = db.query(models.Employee).filter(models.Employee.id == req.employee_id).first()
    if not emp:
        raise HTTPException(status_code=404, detail="Employee not found")
    
    rec = models.DownloadRecord(
        employee_id=req.employee_id,
        start_date=req.start_date,
        end_date=req.end_date,
        count=req.count
    )
    db.add(rec)
    db.commit()
    
    # Return new total for UI update
    new_total = sum(r.count for r in emp.download_records)
    return {"status": "success", "new_total": new_total}

@app.get("/employee/my-downloads")
def get_my_downloads(db: Session = Depends(get_db), current_user: models.User = Depends(auth.get_current_active_employee)):
    emp = db.query(models.Employee).filter(models.Employee.user_id == current_user.id).first()
    if not emp: return {"total_downloads": 0, "recent_activity": []}
    
    total = sum(r.count for r in emp.download_records) if emp.download_records else 0
    
    # Get last 5 records
    recent = db.query(models.DownloadRecord)\
        .filter(models.DownloadRecord.employee_id == emp.id)\
        .order_by(models.DownloadRecord.created_at.desc())\
        .limit(5).all()
        
    recent_activity = [{
        "start_date": r.start_date,
        "end_date": r.end_date,
        "count": r.count
    } for r in recent]

    return {
        "total_downloads": total,
        "recent_activity": recent_activity
    }

@app.get("/admin/chart-data")
def get_admin_chart_data(db: Session = Depends(get_db), current_user: models.User = Depends(auth.get_current_active_admin)):
    records = db.query(models.DownloadRecord).order_by(models.DownloadRecord.start_date).all()
    
    # Group by start date
    data_map = {}
    for r in records:
        d_str = r.start_date.isoformat()
        data_map[d_str] = data_map.get(d_str, 0) + r.count
        
    sorted_dates = sorted(data_map.keys())
    return {
        "labels": sorted_dates,
        "data": [data_map[d] for d in sorted_dates]
    }

@app.get("/employee/chart-data")
def get_employee_chart_data(db: Session = Depends(get_db), current_user: models.User = Depends(auth.get_current_active_employee)):
    emp = db.query(models.Employee).filter(models.Employee.user_id == current_user.id).first()
    if not emp: return {"labels": [], "data": []}
    
    records = db.query(models.DownloadRecord).filter(models.DownloadRecord.employee_id == emp.id).order_by(models.DownloadRecord.start_date).all()
    
    data_map = {}
    for r in records:
        d_str = r.start_date.isoformat()
        data_map[d_str] = data_map.get(d_str, 0) + r.count
        
    sorted_dates = sorted(data_map.keys())
    return {
        "labels": sorted_dates,
        "data": [data_map[d] for d in sorted_dates]
    }


# Include API Router
app.include_router(api_router)

# Redirect root to admin.html
from fastapi.responses import RedirectResponse

@app.get('/')
async def root():
    return RedirectResponse(url='/admin.html')

# Mount Static Files (Frontend)
frontend_path = '../frontend' if os.path.isdir('../frontend') else 'frontend'
if os.path.isdir(frontend_path):
    app.mount('/', StaticFiles(directory=frontend_path, html=True), name='static')
else:
    print(f'Warning: Frontend directory not found at {frontend_path}')

