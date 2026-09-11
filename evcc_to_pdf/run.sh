#!/bin/sh
set -e

# /share is bind-mounted by the Supervisor at container start, which hides
# anything created under it at image build time. Create the report output
# directory here so the /app/output symlink (set up in the Dockerfile)
# actually resolves to an existing directory.
mkdir -p /share/evcc_to_pdf

exec python3 /run.py
