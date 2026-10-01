import uvicorn
import os

if __name__ == "__main__":
    for d in ["input", "assets", "output", "logs", "templates", "static"]:
        os.makedirs(d, exist_ok=True)
    # Bind strictly to localhost for security
    uvicorn.run("src.main:app", host="127.0.0.1", port=8000, reload=False)