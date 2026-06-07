#!/usr/bin/env python3
"""
Run the Princess Card Game server with `python -m princess`.

Copyright 2026 Mike Huot

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0
"""

import os

import uvicorn

from .logging_config import setup_logging


def main() -> None:
    setup_logging()
    host = os.environ.get("HOST", "127.0.0.1")
    port = int(os.environ.get("PORT", "8000"))
    uvicorn.run("princess.server:app", host=host, port=port, reload=False, log_level="info")


if __name__ == "__main__":
    main()
