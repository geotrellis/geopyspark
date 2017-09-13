#!/bin/bash

testpath="geopyspark/tests/"
notebookpath="notebook-demos/"

testpattern="*_test.py"

for f in $notebookpath/*.ipynb
do
  jupyter nbconvert --to notebook --ExecutePreprocessor.startup_timeout=1200 --ExecutePreprocessor.iopub_timeout=1200 --ExecutePreprocessor.timeout=-1 --execute --stdout $f > /dev/null
done

for f in $testpath$testpattern $testpath/**/$testpattern;
do
  pytest $f || { exit 1; }
done
