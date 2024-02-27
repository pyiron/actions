#!/bin/bash

# This is a helper script for branch-based versioning
# It goes through and updates all of the
# pyiron/actions/write-environment@*
# tags to a new value based on the input (default is git branch name)
# The intent is to check out a new branch, e.g. vX.Y.Z
# then run `update_actions_tag.sh`.
# Actions and workflows on this branch then internally, recursively,
# refer to each other

# Set default value for $1 if not provided
PATTERN=${1:-$(git rev-parse --abbrev-ref HEAD)}

# Recursive search and replace
find .. -type f ! -name 'update_actions_tag.sh' -exec sed -i 's/\(pyiron\/actions\/[^@]*\)@[^*]*/\1@'"$PATTERN"'/g' {} +