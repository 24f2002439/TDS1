from fastapi import FastAPI, Header, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from typing import Optional
import time
import uuid

app = FastAPI()

# Allow the grader's website to talk to your API (CORS)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- 3. RATE LIMITING (The Bouncer) ---
client_history = {}
MAX_REQUESTS = 15
TIME_WINDOW = 10  # seconds

@app.middleware("http")
async def rate_limiter(request: Request, call_next):
    client_id = request.headers.get("X-Client-Id")
    
    if client_id:
        now = time.time()
        # Get the client's past requests, or an empty list if they are new
        history = client_history.get(client_id, [])
        
        # Throw away requests that are older than our 10-second window
        history = [timestamp for timestamp in history if now - timestamp < TIME_WINDOW]
        
        # If they have 15 or more recent requests, block them
        if len(history) >= MAX_REQUESTS:
            retry_after = int(TIME_WINDOW - (now - history[0]))
            return Response(
                content="Too Many Requests", 
                status_code=429, 
                headers={"Retry-After": str(max(1, retry_after))}
            )
        
        # Otherwise, record this new request
        history.append(now)
        client_history[client_id] = history
        
    # Proceed to the actual API endpoint
    response = await call_next(request)
    return response

# --- 1. IDEMPOTENCY (The Elevator Button) ---
saved_orders = {}

@app.post("/orders", status_code=201)
async def create_order(idempotency_key: str = Header(..., alias="Idempotency-Key")):
    # If we already processed this exact request, return the saved answer
    if idempotency_key in saved_orders:
        return saved_orders[idempotency_key]
    
    # Otherwise, create a new fake order ID
    new_order = {"id": str(uuid.uuid4()), "status": "Order created!"}
    
    # Save it to our database using the key as the label
    saved_orders[idempotency_key] = new_order
    
    return new_order

# --- 2. CURSOR PAGINATION (The Bookmark) ---
TOTAL_ORDERS = 51
# Generate exactly 51 fake orders for the catalog
database_of_orders = [{"id": i, "name": f"Product {i}"} for i in range(1, TOTAL_ORDERS + 1)]

@app.get("/orders")
async def get_orders(limit: int = 10, cursor: Optional[str] = None):
    start_index = 0
    
    if cursor:
        # Find where the cursor item is, and start ONE position after it
        for index, order in enumerate(database_of_orders):
            if str(order["id"]) == cursor:
                start_index = index + 1
                break
                
    # Slice the list to get a page of results
    end_index = start_index + limit
    page_of_items = database_of_orders[start_index:end_index]
    
    # Set the next cursor to the ID of the very last item in this chunk
    next_cursor = None
    if page_of_items and end_index < TOTAL_ORDERS:
        next_cursor = str(page_of_items[-1]["id"])
        
    return {
        "items": page_of_items,
        "next_cursor": next_cursor
    }