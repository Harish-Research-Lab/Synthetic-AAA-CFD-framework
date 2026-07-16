#!/bin/bash --login
#SBATCH -p multicore     # Single-node multicore job
#SBATCH -n 8             # (or --ntasks=8) number of cores - can be 2-40.
#SBATCH -J wssPercentiles # Job name

# Configuration variables
TIMES="0.15 1.1 2.05 3"  # Time points to analyze
PERCENTILES="50 75 90 95 99"  # Multiple percentiles to extract
BLOOD_DENSITY=1060            # Blood density in kg/m³

# Function to extract all specified percentiles
extract_percentiles() {
    local time=$1
    local percentiles=$2
    local time_dir=$(printf "%.6g" $time)  # Format time for directory name
    
    echo "Processing time: $time_dir"
    
    # Check if time directory exists
    if [ ! -d "$time_dir" ]; then
        echo "Directory $time_dir does not exist, trying alternative format..."
        # Try alternative time directory formats
        time_dir=$(ls -d [0-9]* | grep -E "^$time" | head -1)
        if [ -z "$time_dir" ]; then
            echo "Could not find directory for time $time"
            return 1
        fi
    fi
    
    # Path to wallShearStress file
    WSS_FILE="$time_dir/wallShearStress"
    
    if [ ! -f "$WSS_FILE" ]; then
        echo "Wall shear stress file not found at $WSS_FILE"
        return 1
    fi
    
    # Extract magnitude of wallShearStress and calculate all percentiles
    # The format is specific to OpenFOAM wallShearStress files
    echo "Extracting and calculating WSS magnitudes..."
    awk -v percentiles="$percentiles" -v density="$BLOOD_DENSITY" 'BEGIN {
             n=0; 
             capture=0;
             split(percentiles, p_arr, " ");
         } 
         /nonuniform List<vector>/ {capture=1; next}
         /^[0-9]+$/ && capture==1 {num_vectors=$1; next}
         /^\(/ && capture==1 {
             x=$1; y=$2; z=$3;
             gsub(/[()]/, "", x);
             gsub(/[()]/, "", y);
             gsub(/[()]/, "", z);
             mag = sqrt(x*x + y*y + z*z);
             # Convert kinematic stress to dynamic stress (Pa) by multiplying with density
             mag = mag * density;
             values[n++] = mag;
         }
         /^\)/ {capture=0}
         END {
             # Sort values
             asort(values);
             printf "Time: %s, Total points: %d\n", ENVIRON["time_dir"], n;
             # Calculate each percentile
             for (i in p_arr) {
                 percentile = p_arr[i];
                 idx = int(n * percentile/100);
                 if (idx >= n) idx = n-1;
                 printf "%dth percentile WSS: %.6f Pa\n", percentile, values[idx];
             }
         }' $WSS_FILE
}

# Create output directory for results
RESULTS_DIR="postProcessing/wssPercentiles"
mkdir -p $RESULTS_DIR

# Output file for all percentiles
OUTPUT_FILE="$RESULTS_DIR/wss_all_percentiles.txt"
echo "Time $(echo $PERCENTILES | sed 's/ /_/g') (Pa)" > $OUTPUT_FILE

# Create CSV file header
CSV_FILE="$RESULTS_DIR/wss_all_percentiles.csv"
echo -n "Time" > $CSV_FILE
for p in $PERCENTILES; do
    echo -n ",${p}th_Percentile_Pa" >> $CSV_FILE
done
echo "" >> $CSV_FILE

# Process each time
for time in $TIMES; do
    echo "===================================="
    result=$(extract_percentiles $time "$PERCENTILES")
    echo "$result"
    
    # Extract all percentile values
    echo -n "$time" >> $OUTPUT_FILE
    echo -n "$time" >> $CSV_FILE
    
    for p in $PERCENTILES; do
        percentile_value=$(echo "$result" | grep -oP "${p}th percentile WSS: \K[0-9.]+")
        if [ ! -z "$percentile_value" ]; then
            echo -n " $percentile_value" >> $OUTPUT_FILE
            echo -n ",$percentile_value" >> $CSV_FILE
        else
            echo -n " NA" >> $OUTPUT_FILE
            echo -n ",NA" >> $CSV_FILE
        fi
    done
    
    echo "" >> $OUTPUT_FILE
    echo "" >> $CSV_FILE
    echo "===================================="
done

echo "Results saved to $OUTPUT_FILE and $CSV_FILE"