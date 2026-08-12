"""Uvicorn application runner used by local and container deployments."""
from __future__ import annotations

import os

import uvicorn


def main() -> None:
    """Run the FastAPI application through the declared Uvicorn dependency."""
    uvicorn.run(
        "contractguard.api:app",
        host=os.getenv("HOST", "0.0.0.0"),
        port=int(os.getenv("PORT", "8000")),
        reload=False,
    )


if __name__ == "__main__":
    main()
