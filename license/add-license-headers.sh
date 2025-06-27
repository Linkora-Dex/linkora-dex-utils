#!/bin/bash

# Функция для Python файлов
add_python_header() {
    local file="$1"
    local temp_file=$(mktemp)

    cat > "$temp_file" << 'EOF'
#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# Copyright (C) 2025 Linkora DEX
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published
# by the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program. If not, see <https://www.gnu.org/licenses/>.
#
# For commercial licensing, contact: licensing@linkora.info

EOF

    # Добавить существующий контент, пропустив shebang если есть
    if head -n1 "$file" | grep -q "^#!"; then
        tail -n +2 "$file" >> "$temp_file"
    else
        cat "$file" >> "$temp_file"
    fi

    mv "$temp_file" "$file"
}

# Функция для Shell файлов
add_shell_header() {
    local file="$1"
    local temp_file=$(mktemp)

    cat > "$temp_file" << 'EOF'
#!/bin/bash

# Copyright (C) 2025 Linkora DEX
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published
# by the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program. If not, see <https://www.gnu.org/licenses/>.
#
# For commercial licensing, contact: licensing@linkora.info

EOF

    # Добавить существующий контент, пропустив shebang если есть
    if head -n1 "$file" | grep -q "^#!"; then
        tail -n +2 "$file" >> "$temp_file"
    else
        cat "$file" >> "$temp_file"
    fi

    mv "$temp_file" "$file"
    chmod +x "$file"
}

# Обработка всех файлов
find . -name "*.py" -type f | while read file; do
    if ! grep -q "Copyright (C) 2025 Linkora DEX" "$file"; then
        echo "Adding header to $file"
        add_python_header "$file"
    fi
done

find . -name "*.sh" -type f | while read file; do
    if ! grep -q "Copyright (C) 2025 Linkora DEX" "$file"; then
        echo "Adding header to $file"
        add_shell_header "$file"
    fi
done

echo "License headers added successfully"