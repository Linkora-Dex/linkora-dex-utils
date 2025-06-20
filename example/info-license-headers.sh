#!/bin/bash

echo "Checking license headers..."

missing_headers=0

# Проверка Python файлов
find . -name "*.py" -type f | while read file; do
    if ! grep -q "Copyright (C) 2025 Linkora DEX" "$file"; then
        echo "Missing header: $file"
        missing_headers=$((missing_headers + 1))
    fi
done

# Проверка Shell файлов
find . -name "*.sh" -type f | while read file; do
    if ! grep -q "Copyright (C) 2025 Linkora DEX" "$file"; then
        echo "Missing header: $file"
        missing_headers=$((missing_headers + 1))
    fi
done

if [ $missing_headers -eq 0 ]; then
    echo "All files have proper license headers"
else
    echo "Found $missing_headers files without license headers"
    exit 1
fi