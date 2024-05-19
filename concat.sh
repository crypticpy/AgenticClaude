#!/bin/bash

# Get the current date and time
current_date=$(date +"%Y-%m-%d_%H-%M-%S")

# Output directory
output_dir="snapshot"

# Create the output directory if it doesn't exist
mkdir -p "$output_dir"

# Output file with timestamp
output_file="$output_dir/python_files_$current_date.txt"

# Initialize the output file
echo "" > "$output_file"

# Variable to keep track of the line number
line_number=0

# Create an index array to store file names and starting line numbers
index=()

# Loop through each Python file in the root directory
for py_file in *.py; do
    if [[ -f "$py_file" ]]; then
        # Add the file name and starting line number to the index array
        index+=("$py_file (starts at line $line_number)")

        # Append the content of the Python file to the output file
        cat "$py_file" >> "$output_file"

        # Update the line number counter
        lines_in_file=$(wc -l < "$py_file")
        line_number=$((line_number + lines_in_file))

        # Add a separator between files
        echo "" >> "$output_file"
        echo "----------------------------------------" >> "$output_file"
        echo "" >> "$output_file"
    fi
done

# Insert the index at the beginning of the output file
sed -i "1i INDEX OF FILES:\n${index[*]}\n" "$output_file"

echo "Python files snapshot has been saved to $output_file"
