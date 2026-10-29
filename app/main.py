from fastapi import FastAPI


app = FastAPI()

@app.get("/test")
async def test() -> dict | None:
    return {"status":"application running"}
