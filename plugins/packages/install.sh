#!/bin/bash

# This script will install all packages listed
# in the files in the plugins/packages directory.
# The files should contain a list of packages, one per line.
# The files should be named the same as the plugin
# they are associated with and have a .txt extension.

apt-get update

for file in ./plugins/packages/*; do

    # Skip this file
    if [ "$file" == "./plugins/packages/install.sh" ]; then
        continue
    fi

    # Check if the file is a regular file and not a directory
    if [ -f "$file" ]; then
        # Ensure the file has LF line endings
        sed -i 's/\r$//' "$file"

        echo "Installing packages for $file"
        apt-get --no-install-recommends install -y $(cat "$file")

        if [ $? -eq 0 ]; then
            echo "Packages from $file installed successfully."
        else
            echo "Failed to install packages from $file." >&2
        fi
    else
        echo "$file is not a valid file and will be skipped." >&2
    fi
    
done