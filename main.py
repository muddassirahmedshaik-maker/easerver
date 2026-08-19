from fastapi import FastAPI, Request
from fastapi.responses import PlainTextResponse

app = FastAPI()

# The Cloud now holds specific execution commands for the Slave
state = {
    "CMD_B": "0",    # Buy Lot Size
    "CMD_S": "0",    # Sell Lot Size
    "CMD_CB": "0",   # Close All Buys (1 or 0)
    "CMD_CS": "0",   # Close All Sells (1 or 0)
    "TP_B": "0",     # New Take Profit for Buys
    "TP_S": "0"      # New Take Profit for Sells
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