import shutil
import os
from pathlib import Path
import zipfile
import re
import time

def safe_rmtree(path: Path):
    max_attempts = 3
    for attempt in range(max_attempts):
        try:
            if path.exists():
                shutil.rmtree(path)
            return True
        except Exception:
            if attempt < max_attempts - 1:
                time.sleep(1)  # Wait before retry
            continue
    return False

def create_zip_archive(source_dir: Path, cases: list, zip_path: Path, temp_dir: Path, move: bool = False) -> bool:
    if not safe_rmtree(temp_dir):
        raise OSError(f"Unable to remove directory: {temp_dir}")
    temp_dir.mkdir(parents=True)

    if zip_path.exists():
        zip_path.unlink()

    processed_cases = []
    for case in cases:
        src = source_dir / case
        dest = temp_dir / case
        if src.exists():
            try:
                if move:
                    shutil.move(str(src), str(dest))
                    print(f"Moved: {case}")
                else:
                    shutil.copytree(src, dest)
                    print(f"Copied: {case}")
                processed_cases.append(case)
            except Exception as e:
                print(f"Error processing {case}: {str(e)}")
                continue

    if processed_cases:
        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for case in processed_cases:
                case_dir = temp_dir / case
                for root, _, files in os.walk(case_dir):
                    for file in files:
                        file_path = Path(root) / file
                        arcname = file_path.relative_to(temp_dir)
                        zipf.write(file_path, arcname)

        if not safe_rmtree(temp_dir):
            print(f"Warning: Unable to remove temporary directory: {temp_dir}")
            return False
            
        print(f"\nCreated zip archive: {zip_path}")
        return True
    return False

def get_matching_cases(source_dir: Path, gender: str, age_group: str, suffix: str) -> list:
    age_group_pattern = age_group.replace('+', r'\+')
    pattern = f"AAA_{gender}_{age_group_pattern}_stat_[0-9]+_{suffix}"
    return sorted([d.name for d in source_dir.iterdir() 
                  if d.is_dir() and re.match(pattern, d.name)])

def copy_and_zip_cases(gender: str, age_group: str, suffix: str):
    source_dir = Path("data/output/ofCases")
    interior_file = Path(f"data/processed/bound_plots/{gender}_{age_group}_{suffix}/universal_interior_manual.txt")
    
    if not interior_file.exists():
        raise FileNotFoundError(f"Interior cases file not found: {interior_file}")
    
    base_name = f"{gender}_{age_group}_{suffix}"
    temp_interior = source_dir / f"{base_name}_interior_cases"
    temp_all = source_dir / f"{base_name}_all_cases"
    
    interior_cases = []
    with open(interior_file, 'r') as f:
        interior_cases = [line.strip('- \n') for line in f if line.startswith('- ')]
    
    if not interior_cases:
        raise ValueError("No interior cases found in the file")
    
    all_cases = get_matching_cases(source_dir, gender, age_group, suffix)
    if not all_cases:
        raise ValueError("No matching cases found")

    interior_success = create_zip_archive(source_dir, interior_cases, 
                                        temp_interior.with_suffix('.zip'), temp_interior)
    
    all_success = create_zip_archive(source_dir, all_cases, 
                                   temp_all.with_suffix('.zip'), temp_all, move=True)
    
    return interior_success and all_success

if __name__ == "__main__":
    try:
        copy_and_zip_cases("F", "70-79", "prob_distribution")
    except Exception as e:
        print(f"Error: {str(e)}")