from fastapi import FastAPI, Request
from fastapi.responses import PlainTextResponse

app = FastAPI()

# Only holds the live signal from the Master
state = {
    "SIGNAL": "NONE",   # Examples: "BUY_0.01", "SELL_0.02", "CLOSE_BUY", "CLOSE_SELL"
    "TP_B": "0",        # Current Buy Basket TP
    "TP_S": "0"         # Current Sell Basket TP
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
