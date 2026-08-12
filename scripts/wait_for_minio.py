#!/usr/bin/env python3
"""Optional helper used by container deployments to wait for MinIO readiness."""
from __future__ import annotations

import os
import time
import urllib.request

endpoint = os.getenv("MINIO_HEALTH_URL", "http://minio:9000/minio/health/live")
for _ in range(60):
    try:
        with urllib.request.urlopen(endpoint, timeout=2) as response:
            if response.status == 200:
                raise SystemExit(0)
    except Exception:
        time.sleep(2)
raise SystemExit("MinIO did not become ready")
