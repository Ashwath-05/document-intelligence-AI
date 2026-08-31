# python:3.12-slim, not full python:3.12 -- this app has zero need for the
# full image's compilers/build tools; psycopg2-binary and sentence-transformers
# both ship prebuilt wheels, so slim is enough and meaningfully smaller.
FROM python:3.12-slim

WORKDIR /app

# Requirements copied and installed BEFORE the rest of the source. Docker
# caches layers by instruction -- as long as requirements.txt doesn't
# change, this layer is reused on every rebuild instead of reinstalling
# sentence-transformers/torch (the slowest part of this build) every time
# you change one line of application code.
COPY requirements.txt .

# torch's default PyPI wheel on Linux is the CUDA-enabled build -- it pulls
# in several GB of NVIDIA runtime libraries (cuDNN, cuBLAS, NCCL...) that
# are dead weight here: this container has no GPU, and sentence-transformers'
# embedding model runs perfectly fine on CPU. Installing the CPU-only wheel
# FIRST satisfies sentence-transformers' torch requirement before pip ever
# considers the GPU build, so the line below never re-triggers it.
RUN pip install --no-cache-dir torch --index-url https://download.pytorch.org/whl/cpu
RUN pip install --no-cache-dir -r requirements.txt

# Now the actual application.
COPY app/ ./app
COPY alembic/ ./alembic
COPY alembic.ini .

EXPOSE 8000

# Shell form (not the JSON-array/exec form used elsewhere in this file) --
# needed here specifically so ${PORT:-8000} actually gets expanded. Render
# (and most PaaS platforms) inject their own PORT env var and expect the
# app to bind to it dynamically, not to a value baked into the image; the
# :-8000 fallback means `docker run` locally, where PORT is unset, still
# behaves exactly as before.
CMD uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}
