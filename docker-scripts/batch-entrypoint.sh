#!/bin/bash

# default verbosity
VERBOSE="-v"

#!/bin/bash
PARAMS=""
while (( "$#" )); do
  case "$1" in
    -v|--verbose)
      VERBOSE="-vv"
      shift 1
      ;;
    --) # end argument parsing
      shift
      break
      ;;
    -*|--*=) # unsupported flags
      echo "Error: Unsupported flag $1" >&2
      exit 1
      ;;
    *) # preserve positional arguments
      PARAMS="$PARAMS $1"
      shift
      ;;
  esac
done
# set positional arguments in their proper place
eval set -- "$PARAMS"

echo "Processing all .yml and .yaml files in /config"
for config in $(ls /config/*) ; do
    filename=$(basename -- "$config")

    extension="${filename##*.}"
    filename="${filename%.*}"
    output="/data/${filename}"

    extension="$(echo ${extension} | tr '[:upper:]' '[:lower:]')"

    if [ "${extension}" == "yml" ] || [ "${extension}" == "yaml" ] ; then
        mkdir -p ${output}
        rm ${output}/*
        jira-agile-metrics $VERBOSE --output-directory ${output} $@ ${config} 2>&1 | tee ${output}/metrics.log
    fi
done