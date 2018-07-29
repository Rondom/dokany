#!/bin/sh -eu
if [ $# -eq 1 ]; then
    dokan_version="$1"
else
    dokan_version="$(cut -f 1,2,3 -d . ../dokan_version.txt)"
fi
echo "Generating Doxygen documentation with version: $dokan_version"
( cat Doxyfile ; echo "PROJECT_NUMBER=$dokan_version" ) | doxygen -
