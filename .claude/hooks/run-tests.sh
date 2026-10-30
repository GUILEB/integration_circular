#!/usr/bin/env bash
# Lance la suite pytest après une modification du code de l'intégration ou des tests.
# Code 2 en cas d'échec : la sortie est renvoyée à Claude pour correction.

file=$(jq -r '.tool_input.file_path // .tool_response.filePath // empty')
case "$file" in
  */custom_components/circular/*.py | */tests/*.py) ;;
  *) exit 0 ;;
esac

cd "$(dirname "$0")/../.." || exit 0
if ! output=$(scripts/test -q 2>&1); then
  echo "Tests en échec après la modification de $file :" >&2
  echo "$output" | tail -40 >&2
  exit 2
fi
