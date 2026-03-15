import requests
import time

SERVER="http://localhost:8000"

def check_server():
try:
r=requests.get(SERVER+"/ping")
print("Server:",r.json())
except:
print("Server not reachable")

while True:
check_server()
time.sleep(5)