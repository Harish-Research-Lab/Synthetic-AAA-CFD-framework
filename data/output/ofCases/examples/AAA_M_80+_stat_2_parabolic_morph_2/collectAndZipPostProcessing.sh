#!/bin/bash

# Define gender, age group, and prefix for naming
gender="M"  # Change as needed
age_group="70-79"  # Change as needed
prefix="prob_distribution"  # Change as needed

# Create the destination folder based on gender, age group, and prefix
destination="postProcessing_${gender}_${age_group}_${prefix}"
mkdir -p "$destination"

# Loop through all case folders matching the new pattern
for case_folder in AAA_${gender}_${age_group}_stat_[0-9]*_${prefix}_morph_[0-9]*; do
    if [ -d "$case_folder/postProcessing" ]; then
        # Extract the folder name without path
        folder_name=$(basename "$case_folder")

        # Copy and rename the postProcessing folder
        cp -r "$case_folder/postProcessing" "$destination/${folder_name}_postProcessing"
    else
        echo "No postProcessing folder in $case_folder"
    fi
done

# Zip the destination directory with the same naming convention
zip_name="${destination}.zip"
zip -r "$zip_name" "$destination"

echo "All postProcessing folders have been copied, renamed, and the directory has been zipped as $zip_name."
