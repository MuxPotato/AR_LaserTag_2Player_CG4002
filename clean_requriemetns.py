# Load the requirements file, remove extra spaces, and save it.
with open("requirements.txt", "r") as file:
    lines = file.readlines()

# Clean up each line by stripping excess whitespace and non-visible characters
cleaned_lines = [line.strip() for line in lines if line.strip()]

# Write cleaned content back to a new file
with open("cleaned_requirements.txt", "w") as file:
    file.write("\n".join(cleaned_lines))

print("Cleaned requirements saved to 'cleaned_requirements.txt'")
