#!/bin/bash

NOTEBOOKS_DIR=$1
EXCLUSION_FILE=$2
KERNEL=$3

# Remove excluded notebooks
if [ "${EXCLUSION_FILE}" != "" ]; then
  for f in $(cat ${EXCLUSION_FILE}); do
      rm "${NOTEBOOKS_DIR}/$f";
  done;
fi

# Set the kernel to be used by papermill to 'python3' if not specified otherwise
if [ "${KERNEL}" = "" ]; then
    KERNEL=python3;
fi

# execute notebooks
i=0;
for notebook in $(find ${NOTEBOOKS_DIR} -type f -name '*.ipynb'); do
    papermill  ${notebook} ${notebook%.*}-out.${notebook##*.} -k ${KERNEL} || i=$((i+1));
done;

# push error to next level
if [ $i -gt 0 ]; then
    exit 1;
fi;
