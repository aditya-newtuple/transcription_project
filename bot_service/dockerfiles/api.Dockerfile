FROM python:3.11.5-slim
ENV VIRTUAL_ENV=/opt/venv
RUN python3 -m venv $VIRTUAL_ENV
ENV PATH="$VIRTUAL_ENV/bin:$PATH"
COPY ./src/backend/requirements.in /app/requirements.in
RUN pip install --disable-pip-version-check --no-cache-dir --no-input uv &&  uv pip install --no-cache -r /app/requirements.in
RUN apt-get update -y \
    && apt-get install curl -y \
    && apt-get install curl unixodbc -y \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

COPY ./src/backend /app/backend
WORKDIR /app/backend
# RUN echo "Applying database migrations ..." && alembic upgrade head

CMD ["/bin/bash", "-c", "python3 main.py"]
