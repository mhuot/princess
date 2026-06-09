#!/usr/bin/env python3
"""
Test-suite setup shared across all test modules.

Disables the per-IP HTTP rate limiter for the default session so existing
smoke tests (which hammer ``POST /api/rooms`` and friends in quick succession)
are not affected by the new quotas. Tests that need to exercise enforcement
clear the env var and rebuild the app under ``importlib.reload``.

Copyright 2026 Mike Huot

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0
"""

import os

# Must be set before any test module imports ``princess.server``.
os.environ.setdefault("PRINCESS_RATE_LIMIT_DISABLED", "1")
