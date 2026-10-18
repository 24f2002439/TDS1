from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
import time
import uuid

app = FastAPI()

# --- 1. THE VIP LIST (CORS Middleware) ---
ALLOWED_ORIGINS = [
    "https://app-2kb4gq.example.com",
    "https://exam.sanand.workers.dev/tds-2026-09-ga2" # <--- UPDATE THIS!
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- 2. THE BOUNCER (Rate Limiting Middleware) ---
client_history = {}
MAX_REQUESTS = 15
TIME_WINDOW = 10

@app.middleware("http")
async def rate_limiter(request: Request, call_next):
    client_id = request.headers.get("X-Client-Id")
    
    if client_id:
        now = time.time()
        history = client_history.get(client_id, [])
        history = [t for t in history if now - t < TIME_WINDOW]
        
        if len(history) >= MAX_REQUESTS:
            # Custom responses in middleware bypass the main CORS setup.
            # We must manually stamp the VIP pass on the 429 error, 
            # or the grader's browser will block it!
            headers = {}
            origin = request.headers.get("origin")
            if origin in ALLOWED_ORIGINS:
                headers["Access-Control-Allow-Origin"] = origin
                
            return Response(
                content="Too Many Requests", 
                status_code=429, 
                headers=headers
            )
            
        history.append(now)
        client_history[client_id] = history
        
    return await call_next(request)

# --- 3. THE NAME TAG (Request Context Middleware) ---
@app.middleware("http")
async def request_context(request: Request, call_next):
    # Grab the ID they brought, or generate a fresh one if missing
    req_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
    
    # Save it into the request's "backpack" (state) so /ping can see it
    request.state.request_id = req_id
    
    # Let the request pass through to the /ping endpoint
    response = await call_next(request)
    
    # Stamp the ID on the outgoing response box
    response.headers["X-Request-ID"] = req_id
    return response

# --- THE ENDPOINT ---
@app.get("/ping")
async def ping(request: Request):
    return {
        "email": "24f2002439@ds.study.iitm.ac.in", # <--- UPDATE THIS!
        # Pull the ID right out of the backpack we packed in the middleware
        "request_id": request.state.request_id 
    }