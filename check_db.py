import os
import json
from supabase import create_client, Client

# Use the credentials from your app.py
SUPABASE_URL = "https://qgjrfyvndhusydplqgnp.supabase.co"
SUPABASE_ANON_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InFnanJmeXZuZGh1c3lkcGxxZ25wIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NzAwMTk3MzUsImV4cCI6MjA4NTU5NTczNX0.IagPiWX9NCh90cPzefwab6yd3fOjIybyrbhbuGVBaww"

def check_cvs():
    try:
        # Initialize Supabase client
        supabase: Client = create_client(SUPABASE_URL, SUPABASE_ANON_KEY)
        
        # Fetch all records from the 'cvs' table
        print("--- Fetching all CVs from Supabase ---\n")
        response = supabase.table('cvs').select('id, filename, created_at, resume_data, file_path').execute()
        
        cvs = response.data
        
        if not cvs:
            print("No CVs found in the database.")
            return

        print(f"Found {len(cvs)} CV(s):\n")
        for i, cv in enumerate(cvs, 1):
            print(f"[{i}] ID: {cv['id']}")
            print(f"    Filename: {cv['filename']}")
            print(f"    File Path: {cv.get('file_path', 'None')}")
            print(f"    Uploaded: {cv['created_at']}")

            
            # Print a snippet of the parsed data
            name = cv.get('resume_data', {}).get('name', 'N/A')
            email = cv.get('resume_data', {}).get('email', 'N/A')
            print(f"    Candidate: {name} ({email})")
            print("-" * 40)
            
    except Exception as e:
        print(f"Error connecting to database: {e}")

if __name__ == "__main__":
    check_cvs()
