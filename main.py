from fastapi import FastAPI, Request
from fastapi.responses import PlainTextResponse

app = FastAPI()

state = {
    "TP": "4.20",
    "BSL": "50.0",
    "SSL": "50.0",
    "MODE": "0",     # 0=Dual, 1=Buy, 2=Sell
    "PAUSE": "0",    # 1=Paused, 0=Running
    "LOCK": "0",     # 1=Daily Target/SL Hit
    "CMD_CB": "0",   # 1=Force Close Buys
    "CMD_CS": "0"    # 1=Force Close Sells
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
    return "OK"
