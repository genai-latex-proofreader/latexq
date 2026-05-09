FROM python:3.12.6-bookworm

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        build-essential \
        curl \
        entr \
        git \
        less \
        ripgrep \
        tmux \
    && rm -rf /var/lib/apt/lists/*

# Install uv following
# https://docs.astral.sh/uv/guides/integration/docker/#available-images
COPY --from=ghcr.io/astral-sh/uv:0.11.6 /uv /uvx /bin/

# Python setup
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PYTHON_DOWNLOADS=never

ENV UV_PROJECT_ENVIRONMENT=/opt/venv
ENV PATH="/opt/venv/bin:$PATH"

WORKDIR /uv-help-dir
COPY pyproject.toml uv.lock ./
RUN uv sync \
    --no-install-project \
    --all-extras

# terminal installation following https://starship.rs/
ENV TERM=xterm-256color
RUN curl -sS https://starship.rs/install.sh | sh -s -- -y \
    && echo 'eval "$(starship init bash)"' >> ~/.bashrc \
    && echo "alias ls='ls --color=auto'" >> ~/.bashrc

WORKDIR /workspaces/latexq
