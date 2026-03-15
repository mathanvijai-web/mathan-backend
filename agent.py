import requests

SERVER="http://localhost:8000"

def ping():
try:
r=requests.get(SERVER+"/ping")
print("Agent connected:",r.json())
except:
print("Server not reachable")

ping()