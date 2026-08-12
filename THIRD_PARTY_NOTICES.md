# Third-Party Notices

## transitions 0.9.3

The project declares `transitions==0.9.3` as its finite-state graph dependency. For the
fully offline executed evidence notebook, a small unmodified copy of the package core,
initializer, version file, and MIT license is vendored under
`src/contractguard/_vendor/transitions/` and used only when the installed package is
unavailable.

Copyright (c) 2024 Tal Yarkoni, Alexander Neumann. Licensed under the MIT License. The
complete license text is retained at `src/contractguard/_vendor/transitions/LICENSE`.

## MinIO container and Python SDK

The Docker Compose simulation references an external MinIO container image and the Python
`minio` SDK. The container image is not redistributed inside this repository. Their use is
subject to the licenses published by their respective upstream projects.

## Other Python dependencies

FastAPI, Uvicorn, Pydantic, Prometheus Client, pypdf, HTTPX, python-dotenv, pytest,
nbformat, nbclient, IPython kernel components, and pandas remain governed by their upstream
licenses. See `pyproject.toml`, `requirements.txt`, and `requirements-dev.txt` for the
version ranges used by this project.
