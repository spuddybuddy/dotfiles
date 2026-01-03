#!/usr/bin/python3

import os

def get_file_map(root_dir):
    """
    Walks through a directory recursively and returns a dictionary
    where keys are filenames and values are the full absolute paths.
    
    Note: If a filename appears multiple times within the same root directory 
    (e.g., in different subfolders), the last one found will be stored.
    """
    file_map = {}
    
    # os.walk yields a 3-tuple (dirpath, dirnames, filenames)
    for dirpath, _, filenames in os.walk(root_dir):
        for filename in filenames:
            # Create the full path
            full_path = os.path.join(dirpath, filename)
            file_map[filename] = full_path
            
    return file_map

def compare_directories(dir_a, dir_b):
    print(f"Scanning Folder A: {dir_a}...")
    files_a = get_file_map(dir_a)
    
    print(f"Scanning Folder B: {dir_b}...")
    files_b = get_file_map(dir_b)

    # Create sets of filenames (keys) for set operations
    set_a = set(files_a.keys())
    set_b = set(files_b.keys())

    # 1. Intersection (Files in both A and B)
    common_files = set_a.intersection(set_b)
    
    # 2. Difference A - B (Files in A but not B)
    only_in_a = set_a.difference(set_b)
    
    # 3. Difference B - A (Files in B but not A)
    only_in_b = set_b.difference(set_a)

    print("\n" + "="*60)
    print(f"SUMMARY")
    print(f"Unique to A: {len(only_in_a)}")
    print(f"Unique to B: {len(only_in_b)}")
    print(f"In Both:     {len(common_files)}")
    print("="*60 + "\n")

    # Helper function to print details
    def print_file_info(category_name, filename_set):
        if not filename_set:
            return

        print(f"--- {category_name} ---")
        for fname in sorted(filename_set):
            path_a = files_a.get(fname, "N/A")
            path_b = files_b.get(fname, "N/A")
            
            print(f"File: {fname}")
            if path_a != "N/A":
                print(f"  Path in A: {path_a}")
            if path_b != "N/A":
                print(f"  Path in B: {path_b}")
            print("-" * 20)
        print("\n")

    # Print the results
    print_file_info("FILES ONLY IN FOLDER A", only_in_a)
    print_file_info("FILES ONLY IN FOLDER B", only_in_b)
    print_file_info("FILES IN BOTH LOCATIONS", common_files)

if __name__ == "__main__":
    # --- CONFIGURATION ---
    # Replace these paths with the actual folders you want to compare
    folder_a = r"C:\Users\YourName\Documents\FolderA"
    folder_b = r"C:\Users\YourName\Documents\FolderB"

    if os.path.exists(folder_a) and os.path.exists(folder_b):
        compare_directories(folder_a, folder_b)
    else:
        print("Error: One or both of the directories provided do not exist.")
