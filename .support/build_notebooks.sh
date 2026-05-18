#!/bin/bash

NOTEBOOKS_DIR=$1
EXCLUSION_FILE=$2
KERNEL=$3
NOTEBOOKS_WORKING_DIRECTORY=$4

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

CWD_ARGS=()
if [ "${NOTEBOOKS_WORKING_DIRECTORY}" != "" ]; then
    CWD_ARGS=(--cwd "${NOTEBOOKS_WORKING_DIRECTORY}")
fi

# execute notebooks
i=0;
for notebook in $(find ${NOTEBOOKS_DIR} -type f -name '*.ipynb'); do
    papermill "${notebook}" "${notebook%.*}-out.${notebook##*.}" -k "${KERNEL}" "${CWD_ARGS[@]}" || i=$((i+1));
done;

# push error to next level
if [ $i -gt 0 ]; then
    exit 1;
fi;
