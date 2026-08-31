"""Business logic layer.

Services own the *what* -- "summarize a document", "answer a question about a
document". They are deliberately ignorant of HTTP (no FastAPI imports here)
and of concrete vendors (they depend on provider *interfaces*, never on
GroqProvider directly).

Empty in Phase 1. Populated from Phase 3 onward.

Test for whether a service is real: could you call it from a plain CLI script
with no web server running? If not, logic has leaked into the router layer.
"""
