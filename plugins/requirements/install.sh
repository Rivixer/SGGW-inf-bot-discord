#!/bin/bash

# This script will install all packages listed
# in the files in the plugins/requirements directory.
# The files should contain a list of packages, one per line.
# The files should be named the same as the plugin
# they are associated with and have a .txt extension.

for file in ./plugins/requirements/*; do

    # Skip this file
    if [ "$file" == "./plugins/requirements/install.sh" ]; then
        continue
    fi

    # Check if the file is a regular file and not a directory
    if [ -f "$file" ]; then
        echo "Installing Python packages for $file"

        # Install the packages listed in the current file using pip
        python -m pip install -r "$file"

        # Check if the pip installation was successful
        if [ $? -eq 0 ]; then
            echo "Packages from $file installed successfully."
        else
            echo "Failed to install packages from $file." >&2
        fi
    else
        echo "$file is not a valid file and will be skipped." >&2
    fi

done
