#!/bin/bash --login
#SBATCH -p multicore     # Single-node multicore job
#SBATCH -n 16             # (or --ntasks=8) number of cores - can be 2-40.

# Ensure the paraview modulefile is loaded
module  purge
module load paraview/5.11.2

# Set permissions for the script
chmod +x paraTawss.py

# Run pvbatch - you do not control this with the paraview GUI
mpiexec pvbatch --system-mpi paraTawss.py