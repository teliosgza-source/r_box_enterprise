find . \( -name "*.py" -o -name "*.ts" -o -name "*.tsx" \) -type f \
-exec sh -c 'echo "===== $1 ====="; cat "$1"; echo' _ {} \; > all_code_dump.txt