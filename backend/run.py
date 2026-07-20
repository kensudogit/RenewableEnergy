"""Local development entrypoint."""
import uvicorn

if __name__ == "__main__":
    import os

    port = int(os.getenv("PORT", "8020"))
    uvicorn.run("src.main:app", host="0.0.0.0", port=port, reload=True)
