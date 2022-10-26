#!/bin/bash

NOTEBOOKS_DIR=$1
EXCLUSION_FILE=$2

# Remove excluded notebooks
if [ ${EXCLUSION_FILE} != "" ]; then
  for f in $(cat ${EXCLUSION_FILE}); do
      rm "${NOTEBOOKS_DIR}/$f";
  done;
fi

# execute notebooks
i=0;
for notebook in $(ls ${NOTEBOOKS_DIR}/*.ipynb); do
    papermill ${notebook} ${notebook%.*}-out.${notebook##*.} -k $kernel || i=$((i+1));
done;

# push error to next level
if [ $i -gt 0 ]; then
    exit 1;
fi;
