def remove_outer_quotes(input_file_path, output_file_path=None):
    if output_file_path is None:
        output_file_path = input_file_path  # Overwrite the original file if no output file is provided

    try:
        with open(input_file_path, 'r') as infile:
            lines = infile.readlines()

        # Remove outer quotes from each line
        modified_lines = []
        for line in lines:
            # Strip outer double quotes
            modified_line = line.strip()
            if modified_line.startswith('"') and modified_line.endswith('"'):
                modified_line = modified_line[1:-1]
            modified_lines.append(modified_line)

        # Write the modified lines back to the file (or to a new file)
        with open(output_file_path, 'w') as outfile:
            for modified_line in modified_lines:
                outfile.write(modified_line + '\n')

        print(f"Successfully removed outer quotes from {input_file_path} and saved to {output_file_path}")

    except Exception as e:
        print(f"An error occurred: {e}")

# Example usage
input_file = 'packets_from_beetles.log'  # Path to your log file
remove_outer_quotes(input_file)
