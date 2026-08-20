from fastapi import FastAPI, Request
from fastapi.responses import PlainTextResponse
import time

app = FastAPI()

# CHANGE THIS TO YOUR OWN SECRET ADMIN PASSWORD
ADMIN_KEY = "MY_SECRET_ADMIN_123"

# Holds the active signal from Master
state = {
    "SIGNAL": "NONE",
    "SIGNAL_ID": "0",
    "TP_B": "0",
    "TP_S": "0"
}

# In-Memory Account Subscription Database
# Format: { "account_number_str": expiration_timestamp_float }
subscribers = {}

# --- ADMIN ENDPOINT: GRANT OR EXTEND ACCESS ---
@app.get("/api/grant", response_class=PlainTextResponse)
def grant_access(admin_key: str, account: str, days: int = 30):
    if admin_key != ADMIN_KEY:
        return "ERROR: Invalid Admin Key"
    
    current_time = time.time()
    existing_expiry = subscribers.get(str(account), current_time)
    
    start_point = max(current_time, existing_expiry)
    new_expiry = start_point + (days * 86400)
    
    subscribers[str(account)] = new_expiry
    return f"SUCCESS: Account {account} granted {days} days of access until {time.ctime(new_expiry)}"

# --- ADMIN ENDPOINT: REVOKE ACCESS ---
@app.get("/api/revoke", response_class=PlainTextResponse)
def revoke_access(admin_key: str, account: str):
    if admin_key != ADMIN_KEY:
        return "ERROR: Invalid Admin Key"
    
    if str(account) in subscribers:
        del subscribers[str(account)]
        return f"SUCCESS: Revoked access for Account {account}"
    return f"NOTICE: Account {account} was not found"

# --- SLAVE POLL ENDPOINT WITH AUTHENTICATION ---
@app.get("/api/state", response_class=PlainTextResponse)
def get_state(account: str = ""):
    current_time = time.time()
    acc_str = str(account)
    
    # 1. Check if account is authorized
    if acc_str not in subscribers:
        return "AUTH=UNAUTHORIZED|DAYS=0"
    
    expiry = subscribers[acc_str]
    
    # 2. Check if subscription expired
    if current_time > expiry:
        return "AUTH=EXPIRED|DAYS=0"
    
    # 3. Calculate remaining days
    days_left = max(0, int((expiry - current_time) / 86400))
    
    # Return OK auth status and signal data
    signal_data = "|".join([f"{k}={v}" for k, v in state.items()])
    return f"AUTH=OK|DAYS={days_left}|{signal_data}"

# --- MASTER SIGNAL BROADCAST ENDPOINT ---
@app.get("/api/update", response_class=PlainTextResponse)
def update_state(request: Request):
    params = request.query_params
    for k, v in params.items():
        if k in state:
            state[k] = str(v)
    
    if "SIGNAL" in params and params["SIGNAL"] != "NONE":
        state["SIGNAL_ID"] = str(int(time.time() * 1000))
        
    return "OK"
