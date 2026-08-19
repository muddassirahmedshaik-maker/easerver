from fastapi import FastAPI, Request
from fastapi.responses import PlainTextResponse

app = FastAPI()

# In-memory cloud state
state = {
    "TP": "4.20",
    "BSL": "50.0",
    "SSL": "50.0",
    "MODE": "0",
    "PAUSE": "0",
    "LOCK": "0",
    "CMD_CBUY": "0",
    "CMD_CSELL": "0"
}

@app.get("/api/state", response_class=PlainTextResponse)
def get_state():
    # Returns a simple string for MQL5 to easily parse: "TP=4.20|BSL=50.0|MODE=0..."
    return "|".join([f"{k}={v}" for k, v in state.items()])

@app.get("/api/update", response_class=PlainTextResponse)
def update_state(request: Request):
    # Updates the state using URL parameters (e.g., /api/update?TP=5.50&MODE=1)
    params = request.query_params
    for k, v in params.items():
        if k in state:
            state[k] = str(v)
    return "OK"