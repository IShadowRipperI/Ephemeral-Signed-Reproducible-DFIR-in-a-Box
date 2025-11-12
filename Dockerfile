# keep amd64 since plaso image is amd64
FROM --platform=linux/amd64 log2timeline/plaso:latest

USER root
ENV DFIRBOX_HOME=/app PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1

# deps + build tools for yara-python
RUN rm -rf /var/lib/apt/lists/* && mkdir -p /var/lib/apt/lists/partial && \
    apt-get update && apt-get install -y --no-install-recommends \
      python3-venv python3-dev build-essential pkg-config \
      python3-pip jq findutils file yara libyara-dev tini \
    && rm -rf /var/lib/apt/lists/*

# create and use virtualenv to bypass PEP 668
ENV VIRTUAL_ENV=/opt/venv
RUN python3 -m venv "$VIRTUAL_ENV"
ENV PATH="$VIRTUAL_ENV/bin:$PATH"

COPY requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir -r /tmp/requirements.txt

WORKDIR /app
COPY src/ /app/src/
COPY profiles/ /app/profiles/
COPY rules/ /app/rules/
COPY LICENSE README.md /app/

COPY entrypoint.sh /usr/local/bin/entrypoint.sh
RUN chmod +x /usr/local/bin/entrypoint.sh


ENTRYPOINT ["/usr/bin/tini","--","/usr/local/bin/entrypoint.sh"]
CMD ["dfirbox","--help"]
