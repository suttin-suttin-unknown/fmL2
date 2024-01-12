#!/bin/bash

mongo_uri="mongodb://localhost:27017"
dump_dir="db_dump"
utc_timestamp=$(date -u +%s)

mongodump --uri="$mongo_uri" --out="$dump_dir"

# Check if mongodump was successful
if [ $? -ne 0 ]; then
    echo "MongoDB dump failed."
    exit 1
fi

zip_file="backup_${utc_timestamp}.zip"
zip -r "$zip_file" "$dump_dir"

# Check if zip was successful
if [ $? -ne 0 ]; then
    echo "Zip operation failed."
    exit 1
fi

echo "Created archive: $zip_file"