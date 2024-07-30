ARG PYTHON_VERSION="3.12"

FROM python:${PYTHON_VERSION}-alpine
WORKDIR /usr/src/app

ENV PYTHONUNBUFFERED=1
RUN apk add --update build-base gcc libffi-dev
RUN pip install poetry

ENV POETRY_VIRTUALENVS_IN_PROJECT=false
COPY ./app/pyproject.toml ./app/poetry.lock /usr/src/app/
RUN poetry install --no-root

ENTRYPOINT ["poetry", "run", "python", "entrypoint.py"]
