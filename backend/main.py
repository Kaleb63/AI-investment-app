from fastapi import FastAPI

app = FastAPI()

@app.get("/")
def home():
    return {"message": "Investment app backend is running"}