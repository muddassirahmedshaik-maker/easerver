from fastapi import FastAPI, Request
from fastapi.responses import PlainTextResponse, HTMLResponse, JSONResponse
import time
import redis

app = FastAPI()

ADMIN_KEY = "9700774354"

# Connect to your Upstash Redis database using the credentials from your screenshot
db = redis.Redis(
    host='aware-louse-249355.upstash.io',
    port=6379,
    password='gQAAAAAAA84LAAIgcDEyZWYyYzQwMWM3OGU0NzMzOTFmZjU3ZmZmNzc1ODc1OA',
    ssl=True,
    decode_responses=True # Important: Keeps data formatted as text strings
)

@app.get("/api/grant")
def grant_access(admin_key: str, account: str, days: int = 30):
    if admin_key != ADMIN_KEY:
        return PlainTextResponse("ERROR: Invalid Admin Key", status_code=401)
    
    current_time = time.time()
    
    # Read from cloud DB instead of local dictionary
    existing_expiry = db.get(str(account)) 
    existing_expiry = float(existing_expiry) if existing_expiry else current_time
    
    start_point = max(current_time, existing_expiry)
    new_expiry = start_point + (days * 86400)
    
    # Save to cloud DB
    db.set(str(account), new_expiry) 
    
    return JSONResponse({"status": "success", "message": f"Account {account} granted {days} days."})

@app.get("/api/revoke")
def revoke_access(admin_key: str, account: str):
    if admin_key != ADMIN_KEY:
        return PlainTextResponse("ERROR: Invalid Admin Key", status_code=401)
    
    if db.exists(str(account)):
        db.delete(str(account)) # Delete from cloud DB
        return JSONResponse({"status": "success", "message": f"Revoked Account {account}"})
    return JSONResponse({"status": "error", "message": f"Account {account} not found"})

@app.get("/api/users")
def get_users(admin_key: str):
    if admin_key != ADMIN_KEY:
        return PlainTextResponse("ERROR: Invalid Admin Key", status_code=401)
    
    current_time = time.time()
    user_list = []
    
    # Fetch all keys and values from Redis
    all_keys = db.keys()
    for acc in all_keys:
        expiry = db.get(acc)
        if expiry:
            expiry_float = float(expiry)
            days_left = max(0, int((expiry_float - current_time) / 86400))
            status = "Active" if current_time <= expiry_float else "Expired"
            user_list.append({
                "account": acc,
                "days_left": days_left,
                "status": status,
                "expiry_date": time.strftime('%Y-%m-%d %H:%M', time.gmtime(expiry_float))
            })
        
    return JSONResponse({"users": user_list})

@app.get("/api/auth", response_class=PlainTextResponse)
def check_auth(account: str = ""):
    current_time = time.time()
    acc_str = str(account)
    
    expiry = db.get(acc_str)
    
    if not expiry:
        return "AUTH=UNAUTHORIZED|DAYS=0"
        
    expiry_float = float(expiry)
    if current_time > expiry_float:
        return "AUTH=EXPIRED|DAYS=0"
    
    days_left = max(0, int((expiry_float - current_time) / 86400))
    return f"AUTH=OK|DAYS={days_left}"

@app.get("/dashboard", response_class=HTMLResponse)
def dashboard():
    html_content = """
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>EA License Manager</title>
        <script src="https://cdn.tailwindcss.com"></script>
    </head>
    <body class="bg-gray-900 text-white font-sans p-8">
        <div class="max-w-4xl mx-auto">
            <h1 class="text-3xl font-bold text-yellow-400 mb-8">Cloud EA License Manager</h1>
            
            <div id="login-section" class="bg-gray-800 p-6 rounded-lg mb-8 border border-gray-700">
                <label class="block mb-2 text-sm text-gray-400">Enter Admin Key to Access Dashboard:</label>
                <div class="flex gap-4">
                    <input type="password" id="admin-key" class="w-full bg-gray-900 border border-gray-600 rounded p-2 text-white" placeholder="MY_SECRET_ADMIN_123">
                    <button onclick="loadUsers()" class="bg-blue-600 hover:bg-blue-500 px-6 py-2 rounded font-bold transition">Login</button>
                </div>
            </div>

            <div id="dashboard-content" class="hidden">
                <div class="bg-gray-800 p-6 rounded-lg mb-8 border border-gray-700">
                    <h2 class="text-xl font-bold mb-4 text-green-400">Grant / Extend Access</h2>
                    <div class="flex gap-4">
                        <input type="text" id="new-account" class="w-1/2 bg-gray-900 border border-gray-600 rounded p-2 text-white" placeholder="MT5 Account Number">
                        <input type="number" id="new-days" class="w-1/4 bg-gray-900 border border-gray-600 rounded p-2 text-white" value="30" placeholder="Days">
                        <button onclick="grantAccess()" class="w-1/4 bg-green-600 hover:bg-green-500 px-4 py-2 rounded font-bold transition">Add/Extend</button>
                    </div>
                </div>

                <div class="bg-gray-800 rounded-lg border border-gray-700 overflow-hidden">
                    <table class="w-full text-left border-collapse">
                        <thead>
                            <tr class="bg-gray-700 text-gray-300">
                                <th class="p-4 border-b border-gray-600">Account Number</th>
                                <th class="p-4 border-b border-gray-600">Status</th>
                                <th class="p-4 border-b border-gray-600">Days Left</th>
                                <th class="p-4 border-b border-gray-600">Expiry Date (UTC)</th>
                                <th class="p-4 border-b border-gray-600">Actions</th>
                            </tr>
                        </thead>
                        <tbody id="user-table-body">
                        </tbody>
                    </table>
                </div>
            </div>
        </div>

        <script>
            let currentKey = "";

            async function loadUsers() {
                const keyInput = document.getElementById('admin-key').value;
                if(!keyInput) return alert("Please enter an admin key.");
                currentKey = keyInput;

                const response = await fetch(`/api/users?admin_key=${currentKey}`);
                if (!response.ok) return alert("Invalid Admin Key!");

                const data = await response.json();
                document.getElementById('login-section').classList.add('hidden');
                document.getElementById('dashboard-content').classList.remove('hidden');

                const tbody = document.getElementById('user-table-body');
                tbody.innerHTML = "";

                if(data.users.length === 0) {
                    tbody.innerHTML = "<tr><td colspan='5' class='p-4 text-center text-gray-500'>No active subscriptions found.</td></tr>";
                    return;
                }

                data.users.forEach(user => {
                    const statusColor = user.status === 'Active' ? 'text-green-400' : 'text-red-400';
                    const row = `
                        <tr class="hover:bg-gray-750 transition">
                            <td class="p-4 border-b border-gray-700 font-bold">${user.account}</td>
                            <td class="p-4 border-b border-gray-700 ${statusColor}">${user.status}</td>
                            <td class="p-4 border-b border-gray-700">${user.days_left} Days</td>
                            <td class="p-4 border-b border-gray-700 text-sm text-gray-400">${user.expiry_date}</td>
                            <td class="p-4 border-b border-gray-700">
                                <button onclick="revokeAccess('${user.account}')" class="text-xs bg-red-600 hover:bg-red-500 px-3 py-1 rounded font-bold">Revoke</button>
                            </td>
                        </tr>
                    `;
                    tbody.innerHTML += row;
                });
            }

            async function grantAccess() {
                const acc = document.getElementById('new-account').value;
                const days = document.getElementById('new-days').value;
                if(!acc || !days) return alert("Enter account and days.");

                const res = await fetch(`/api/grant?admin_key=${currentKey}&account=${acc}&days=${days}`);
                const data = await res.json();
                alert(data.message);
                loadUsers(); 
            }

            async function revokeAccess(acc) {
                if(!confirm(`Are you sure you want to instantly revoke access for ${acc}?`)) return;
                const res = await fetch(`/api/revoke?admin_key=${currentKey}&account=${acc}`);
                const data = await res.json();
                alert(data.message);
                loadUsers(); 
            }
        </script>
    </body>
    </html>
    """
    return HTMLResponse(content=html_content)
