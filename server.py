from fastapi import FastAPI
import uvicorn

app = FastAPI()

@app.get("/")
def root():
return {"status": "Mathan CCS Server Running"}

@app.get("/ping")
def ping():
return {"message": "server alive"}

if name == "main":
uvicorn.run(app, host="0.0.0.0", port=8000)