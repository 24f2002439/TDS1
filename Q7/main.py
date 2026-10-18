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

business_notes = ""

# --- 2. FETCH AND STORE DATA ---
def load_data_into_memory():
    global business_notes
    print("1. Fetching API Directory Menu...")
    root_response = requests.get(START_URL).json()
    
    # Save the rules so we can pass them to the AI later
    notes_list = root_response.get("notes", [])
    business_notes = "\n".join(notes_list)
    print(f"Found business rules: {business_notes}")
    
    # The 'export' link is usually a shortcut to get all data at once without pagination!
    export_url = root_response.get("links", {}).get("export")
    
    print(f"2. Fetching all data from {export_url}...")
    export_data = requests.get(export_url).json()
    
    # Handle whatever shape the export data comes in
    all_records = []
    if isinstance(export_data, list):
        all_records = export_data
    elif isinstance(export_data, dict):
        # Try common keys if it's a dictionary
        all_records = export_data.get("data", export_data.get("records", []))
        
    print(f"Downloaded {len(all_records)} records.")
    
    if len(all_records) == 0:
        print("CRITICAL ERROR: No records downloaded. Check the export URL format.")
        return None, []
        
    # Create an invisible SQLite database
    conn = sqlite3.connect(':memory:', check_same_thread=False)
    columns = list(all_records[0].keys())
    
    col_defs = ", ".join([f"{col} TEXT" for col in columns])
    conn.execute(f"CREATE TABLE ledger ({col_defs})")
    
    placeholders = ", ".join(["?" for _ in columns])
    insert_query = f"INSERT INTO ledger VALUES ({placeholders})"
    for record in all_records:
        values = [str(record.get(col, "")) for col in columns]
        conn.execute(insert_query, values)
        
    conn.commit()
    return conn, columns

db_conn, db_columns = load_data_into_memory()

# --- 3. HANDLE THE GRADER'S QUESTIONS ---
@app.route('/', methods=['POST'])
def answer_question():
    user_question = request.json.get("question")
    
    # We now inject the business rules directly into the AI's instructions!
    prompt = f"""
    You are an expert data analyst. I have a SQLite table named 'ledger' with these columns: {db_columns}.
    
    CRITICAL BUSINESS RULES YOU MUST FOLLOW:
    {business_notes}
    
    Write a single SQL query to answer this exact question: "{user_question}".
    Return ONLY the raw SQL query. No markdown formatting, no explanation, no ```sql tags.
    If the answer is money, format it as a plain number rounded to 2 decimal places (e.g. 1500.50), no dollar signs.
    """
    
    ai_response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}]
    )
    
    sql_query = ai_response.choices[0].message.content.strip().replace('```sql', '').replace('```', '')
    print(f"AI generated SQL: {sql_query}")
    
    cursor = db_conn.cursor()
    try:
        cursor.execute(sql_query)
        result = cursor.fetchone()[0]
        # Ensure numbers are formatted nicely before sending back
        if result is not None and not isinstance(result, str):
            result = round(float(result), 2)
    except Exception as e:
        print(f"SQL Error: {e}")
        result = "Error running query"
        
    return jsonify({"answer": result})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 3000)))
