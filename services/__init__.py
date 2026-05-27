"""Service layer for Axel orchestration.

Services are the boundary between registered actions and lower-level tools.
They keep action modules thin while the older tool modules remain available for
direct tests and backwards compatibility.
"""
