import os
import requests
import sqlite3
from flask import Flask, request, jsonify
from openai import OpenAI

app = Flask(__name__)

# --- 1. CONFIGURATION ---
# Put your exact assignment URL here
START_URL = "https://exam.sanand.workers.dev/questionData?email=24f2002439%40ds.study.iitm.ac.in&quizSign=DyXNx3kwPqTAi7aQf3MWFpwmjQ8tBAiijKVblhOaxI5rlADQfpta5%2FoKfWfeeiFUF6%2FJtcZyr946rjYVWA%2ByRT5P05GTJxi24WyRKNVcHn7m0HrYlbonAihWUtkkReoVutnODFUqhK%2Bp3KsdNGEaNpILga2T2zGVc2B013H2%2FVdTOOHISIiRzXT%2FO0qQhJ7lYynIcWlE1CNzzIE1K2JUMeCHDNNXT7gjD5PLQXWuXkwjMRPgeeSqDAEUDPUaqA2f%2Fp0e9tD7sr6ZtBuf90OByl1XX%2FMGQI%2FisZbAM4rew32YodYlbKxgI34zGrj8TRz%2BMz7b2pd8z%2BBV70kIQ2nRlg%3D%3D&questionId=q-ledger-agent-server&path=/" 

# Initialize the OpenAI client (it automatically looks for the OPENAI_API_KEY environment variable)
client = OpenAI(
  api_key="eyJhbGciOiJIUzI1NiJ9.eyJlbWFpbCI6IjI0ZjIwMDI0MzlAZHMuc3R1ZHkuaWl0bS5hYy5pbiIsImlhdCI6MTc5MjMwMTEyNSwiaXNzIjoiaHR0cHM6Ly9haXBpcGUub3JnIiwiYXVkIjoiYWlwaXBlLWFwaSIsImV4cCI6MTc5MjkwNTkyNX0.38C9uGlHe3sTSkaZIw4acoxDOEXSEfSU3xB0_sfLx7A",
  base_url="https://aipipe.org/openai/v1"
)

# --- 2. FETCH AND STORE DATA ---
def load_data_into_memory():
    print("Fetching data from API...")
    all_records = []
    current_url = START_URL
    
    # Loop to handle pagination
    while current_url:
        response = requests.get(current_url).json()
        
        # IMPORTANT: Change "data" if your API uses a different word (like "records")
        page_data = response.get("data", [])
        all_records.extend(page_data)
        
        # IMPORTANT: Change "next" if your API uses a different word for the next page
        next_path = response.get("next") 
        
        if next_path:
            # If the next path is just '/page/2', we attach it to the base domain
            current_url = "https://exam.sanand.workers.dev" + next_path
        else:
            break # No more pages!
            
    print(f"Downloaded {len(all_records)} records.")
    
    # Create an invisible, temporary SQLite database in the computer's RAM
    conn = sqlite3.connect(':memory:', check_same_thread=False)
    columns = list(all_records[0].keys())
    
    # Create a table dynamically based on the API's columns
    col_defs = ", ".join([f"{col} TEXT" for col in columns])
    conn.execute(f"CREATE TABLE ledger ({col_defs})")
    
    # Insert all the records
    placeholders = ", ".join(["?" for _ in columns])
    insert_query = f"INSERT INTO ledger VALUES ({placeholders})"
    for record in all_records:
        values = [str(record.get(col, "")) for col in columns]
        conn.execute(insert_query, values)
        
    conn.commit()
    return conn, columns

# Run the fetcher when the server starts
db_conn, db_columns = load_data_into_memory()

# --- 3. HANDLE THE GRADER'S QUESTIONS ---
@app.route('/', methods=['POST'])
def answer_question():
    # Get the question from the grader's JSON
    user_question = request.json.get("question")
    
    # Prompt the AI to act as a SQL translator
    prompt = f"""
    You are a data analyst. I have a SQLite table named 'ledger' with these columns: {db_columns}.
    Write a single SQL query to answer this exact question: "{user_question}".
    Return ONLY the raw SQL query. No markdown formatting, no explanation, no ```sql tags.
    If the answer is money, format it as a plain number rounded to 2 decimal places (e.g. 1500.50), no dollar signs.
    """
    
    # Send to OpenAI
    ai_response = client.chat.completions.create(
        model="gpt-4o-mini", # Fast and smart enough for SQL
        messages=[{"role": "user", "content": prompt}]
    )
    
    # Clean up the AI's response to ensure it's just raw SQL
    sql_query = ai_response.choices[0].message.content.strip().replace('```sql', '').replace('```', '')
    print(f"Running SQL: {sql_query}")
    
    # Execute the query on our in-memory database
    cursor = db_conn.cursor()
    cursor.execute(sql_query)
    result = cursor.fetchone()[0] # Get the top answer
    
    # Return the answer in the JSON format the grader expects
    return jsonify({"answer": result})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 3000)))
