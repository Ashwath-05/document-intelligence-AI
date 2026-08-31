"""Data access layer.

The only layer that knows a database exists. All SQL / ORM queries live here,
behind small interfaces so the services above never import a driver.

Empty in Phase 1. Populated in Phase 2 when Postgres arrives.
"""
