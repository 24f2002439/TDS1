import time
import uuid
from fastapi import FastAPI, Request
from fastapi.responses import PlainTextResponse
from prometheus_client import Counter, generate_latest

app = FastAPI()

# 1. Setup Tracking Variables
START_TIME = time.time()
REQUEST_COUNTER = Counter("http_requests_total", "Total HTTP Requests")
logs_storage = []

# 2. The Toll Booth (Middleware)
@app.middleware("http")
async def track_requests_and_logs(request: Request, call_next):
    # Click the Prometheus tally counter
    REQUEST_COUNTER.inc()
    
    # Record the log entry
    log_entry = {
        "level": "INFO",
        "ts": time.time(),
        "path": request.url.path,
        "request_id": str(uuid.uuid4())
    }
    logs_storage.append(log_entry)
    
    # Let the request pass through to its destination
    response = await call_next(request)
    return response

# 3. The Endpoints
@app.get("/work")
def do_work(n: int):
    return {"email": "24f2002439@ds.study.iitm.ac.in", "done": n}

@app.get("/metrics")
def get_metrics():
    # Generate the specific Prometheus text format
    return PlainTextResponse(generate_latest())

@app.get("/healthz")
def health_check():
    uptime = time.time() - START_TIME
    return {"status": "ok", "uptime_s": uptime}

@app.get("/logs/tail")
def get_logs(limit: int = 10):
    # Return the last N items from the end of the list
    return logs_storage[-limit:]