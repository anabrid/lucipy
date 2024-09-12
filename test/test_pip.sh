#!/bin/bash

set -e

stringContain() { case $2 in *$1* ) return 0;; *) return 1;; esac ;}

workdir=$(mktemp -d)
python -m venv $workdir
cd $workdir

source bin/activate

if not stringContain $(which pip) $workdir; then
  echo "Failed to activate virtualenv at $workdir"
  exit -2
fi

pip install lucipy

pip show lucipy
