ARG PYTHON_VERSION="3"

FROM python:${PYTHON_VERSION}-alpine
WORKDIR /usr/src/app
ENV PYTHONUNBUFFERED=1

COPY ./app/pyproject.toml ./app/poetry.lock /usr/src/app/

RUN pip install poetry
RUN poetry install --no-root

ENTRYPOINT python3 entrypoint.py
