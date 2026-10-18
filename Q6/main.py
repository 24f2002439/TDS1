from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
import time
import uuid

app = FastAPI()

# --- 1. THE VIP LIST (CORS Middleware) ---
ALLOWED_ORIGINS = [
    "https://app-2kb4gq.example.com",
    "https://exam.sanand.workers.dev" # <--- UPDATE THIS!
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["X-Request-ID"] # <--- THE FIX: Tell the browser it's safe to read this
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
            headers = {}
            origin = request.headers.get("origin")
            if origin in ALLOWED_ORIGINS:
                headers["Access-Control-Allow-Origin"] = origin
                # Safely expose the header on our custom error response too
                headers["Access-Control-Expose-Headers"] = "X-Request-ID"
                
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
@app.get("/llm-stream")
async def get_llm_stream():
    return {
        "A": {
            "text": "Report job-100e057f: café\nReady ✓",
            "complete": True,
            "error": None
        },
        "B": {
            "text": "Partial job-100e057f",
            "complete": False,
            "error": None
        },
        "C": {
            "text": "Draft job-100e057f",
            "complete": False,
            "error": "model unloaded"
        }
    }
@app.get("/docker-cache")
async def get_docker_cache():
    return {
        "A": {"steps": ["L3", "L4", "L5"], "seconds": 47},
        "B": {"steps": ["L1", "L2", "L3", "L4", "L5"], "seconds": 104},
        "C": {"steps": [], "seconds": 0},
        "D": {"steps": [], "seconds": 0},
        "E": {"steps": ["L4", "L5"], "seconds": 47}
    }
