from fastapi import FastAPI, Request
from fastapi.responses import PlainTextResponse
import time

app = FastAPI()

state = {
    "SIGNAL": "NONE",
    "SIGNAL_ID": "0",
    "TP_B": "0",
    "TP_S": "0"
}

@app.get("/api/state", response_class=PlainTextResponse)
def get_state():
    return "|".join([f"{k}={v}" for k, v in state.items()])

@app.get("/api/update", response_class=PlainTextResponse)
def update_state(request: Request):
    params = request.query_params
    for k, v in params.items():
        if k in state:
            state[k] = str(v)
    
    # Auto-generate a new unique ID whenever Master sends a trade or close command
    if "SIGNAL" in params and params["SIGNAL"] != "NONE":
        state["SIGNAL_ID"] = str(int(time.time() * 1000))
        
    return "OK"
