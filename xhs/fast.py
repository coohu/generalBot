from fastapi import FastAPI
from pydantic import BaseModel
import asyncio

app = FastAPI()
async def save_to_db():
    await asyncio.sleep(20)
    print(f"Data saved to database")

@app.get("/")
async def index():
	asyncio.create_task(save_to_db())
	await asyncio.sleep(5)
	return {"message": "Item received, processing in background"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)