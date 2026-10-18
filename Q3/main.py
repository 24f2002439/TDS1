from fastapi import FastAPI, HTTPException, Header
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional

app = FastAPI()

# Enable CORS so the grader's browser can access this API directly
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], 
    allow_methods=["*"],
    allow_headers=["*"],
)

# Tell FastAPI exactly what the incoming JSON looks like
class Event(BaseModel):
    user: str
    amount: float
    ts: int

class AnalyticsPayload(BaseModel):
    events: List[Event]

@app.post("/analytics")
def process_analytics(payload: AnalyticsPayload, x_api_key: Optional[str] = Header(None)):
    # 1. Security Check: Reject if the API key is missing or wrong
    if x_api_key != "ak_9xxe5stru3v6ccijv4pjqgwb":
        raise HTTPException(status_code=401, detail="Unauthorized")
    
    # 2. Math Setup: Variables to keep track of our totals
    total_events = len(payload.events)
    unique_users_set = set()
    revenue = 0.0
    user_totals = {}
    
    # 3. Data Crunching: Loop through the batch of events
    for event in payload.events:
        unique_users_set.add(event.user)
        
        # Only count positive amounts for revenue and the top user competition
        if event.amount > 0:
            revenue += event.amount
            # Add this amount to the user's running total
            user_totals[event.user] = user_totals.get(event.user, 0.0) + event.amount
            
    # 4. Find the Top User
    top_user = ""
    highest_sum = -1.0
    for current_user, total_spent in user_totals.items():
        if total_spent > highest_sum:
            highest_sum = total_spent
            top_user = current_user
            
    # 5. Return the final structured JSON (using your institutional email)
    return {
        "email": "24f2002439@ds.study.iitm.ac.in",
        "total_events": total_events,
        "unique_users": len(unique_users_set),
        "revenue": revenue,
        "top_user": top_user
    }