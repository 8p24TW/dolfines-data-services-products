#!/bin/bash
# Install WeasyPrint system dependencies
apt-get update -y
apt-get install -y \
    libcairo2 \
    libpango-1.0-0 \
    libpangocairo-1.0-0 \
    libgdk-pixbuf-2.0-0 \
    shared-mime-info \
    libfontconfig1 \
    libfreetype6 \
    libharfbuzz0b \
    fonts-liberation \
    fonts-noto-core \
    fonts-dejavu-core
