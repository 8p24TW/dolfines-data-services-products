#!/bin/bash
# Run after packages.txt is installed by Streamlit Cloud.
# ldconfig refreshes the dynamic linker cache so WeasyPrint (cffi) can find
# libpango, libcairo etc. even in containerised environments where apt-get
# does not always trigger ldconfig automatically.
ldconfig 2>/dev/null || true

# Install Playwright Chromium browser for PDF generation.
python3 -m playwright install chromium
