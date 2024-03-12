# Run linter on dockerfile to make sure we are following best practices
FROM hadolint/hadolint:v1.17.5-6-gbc8bab9-alpine

# Copy the dockerfile and linter config from the context
COPY hadolint.yaml /config/
COPY Dockerfile .

# Execute the linting process
RUN echo "### Linting Dockerfile ###" && /bin/hadolint --config /config/hadolint.yaml Dockerfile

# Start build
# ------------------------------
# Three stages: base, test, prod
# ------------------------------

# First Stage - Build base image
FROM python:3.11.6-slim-bookworm as base
# Update packages and install security patches
RUN apt update && apt upgrade -y
# Set working directory
WORKDIR /home/app

# Install poetry
RUN pip install poetry

# Copy in poetry files only - this allows us to cache the layer if no new dependencies were added and install base deps
COPY pyproject.toml poetry.lock ./
RUN poetry config virtualenvs.create false && poetry install --only main --no-root

# Second Stage - Build test image
FROM base as test
# Install dev dependencies
RUN poetry install --with dev
COPY . .
# Set working directory

# Third Stage - Build production image (excludes dev dependencies)
FROM base as prod
COPY . .