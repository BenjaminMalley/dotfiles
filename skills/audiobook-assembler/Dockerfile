# Container image for the audiobook-assembler skill: ffmpeg/ffprobe plus
# the assemble.py helper. No host audio tools are required; everything
# runs here via Apple's container CLI.
#
#   container build -t audiobook-assembler <skill dir>
FROM python:3.12-slim-bookworm

RUN apt-get update \
 && apt-get install -y --no-install-recommends ffmpeg \
 && rm -rf /var/lib/apt/lists/*

# Non-root user; uid 1000 matches the common first-user uid on Linux
# hosts. The skill chmods destination dirs so bind-mounted output is
# writable regardless of uid mapping.
RUN useradd --create-home --uid 1000 asm

WORKDIR /opt/asm
COPY assemble.py /opt/asm/

USER asm

# ENTRYPOINT is python3 so assemble.py (or a probe one-liner) is the
# command, e.g.: container run --rm -v "$SRC:/in:ro" -v "$DST:/out" \
#   audiobook-assembler /opt/asm/assemble.py -o /out/book.m4b ...
ENTRYPOINT ["python3"]
