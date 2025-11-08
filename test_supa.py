from supabase import create_client, Client

url = "https://xsxjxnvbrasrrcpozdcw.supabase.co"
key = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InhzeGp4bnZicmFzcnJjcG96ZGN3Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3NTcxMjEyMDgsImV4cCI6MjA3MjY5NzIwOH0.gDZhWZFT2jBLQnrJHlzOKFl7QF7lN4Mq9uaNNPrj7LI"

supabase: Client = create_client(url, key)
# Example: Select all from a table
response = supabase.table("peptides").select("*").execute()
print(response.data)
