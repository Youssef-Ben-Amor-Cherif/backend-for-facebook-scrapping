#!/usr/bin/env bash
# exit on error
set -o errexit

STORAGE_DIR=/opt/render/project/.render

if [[ ! -d $STORAGE_DIR/chrome ]]; then
  echo "...Downloading Chrome"
  mkdir -p $STORAGE_DIR/chrome
  cd $STORAGE_DIR/chrome
  wget -P ./ https://dl.google.com/linux/direct/google-chrome-stable_current_amd64.deb
  dpkg -x ./google-chrome-stable_current_amd64.deb $STORAGE_DIR/chrome
  rm ./google-chrome-stable_current_amd64.deb
  cd $HOME/project/src # Make sure we return to where we were
else
  echo "...Using Chrome from cache"
fi

# Upgrade pip, setuptools, and wheel
pip3 install --upgrade pip setuptools wheel

# Install system dependencies for building numpy and other packages
apt-get update && apt-get install -y build-essential libatlas-base-dev gfortran

# Install Python dependencies
pip3 install -r requirements.txt

# Ensure Chrome is added to the PATH
export PATH="${PATH}:/opt/render/project/.render/chrome/opt/google/chrome"

# Additional build steps
