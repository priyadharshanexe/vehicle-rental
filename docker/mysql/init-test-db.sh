#!/bin/sh
# Validate the identifiers before interpolating them into SQL.
case "$MYSQL_DATABASE:$MYSQL_USER" in
    *[!a-zA-Z0-9_:]*) echo "Use alphanumeric database and user names with optional underscores." >&2; exit 1 ;;
esac
MYSQL_PWD="$MYSQL_ROOT_PASSWORD" mysql --protocol=socket -uroot <<SQL
GRANT ALL PRIVILEGES ON \`test_${MYSQL_DATABASE}\`.* TO '${MYSQL_USER}'@'%';
SQL
