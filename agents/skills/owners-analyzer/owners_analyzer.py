#!/usr/bin/env python3
import os
import re
import sys
import argparse
import subprocess

def get_git_email(repo_root):
    try:
        res = subprocess.run(["git", "config", "user.email"], cwd=repo_root, capture_output=True, text=True, check=True)
        return res.stdout.strip()
    except Exception as e:
        print(f"Error getting git email: {e}", file=sys.stderr)
        return None

def find_git_root():
    try:
        res = subprocess.run(["git", "rev-parse", "--show-toplevel"], capture_output=True, text=True, check=True)
        return res.stdout.strip()
    except Exception as e:
        return os.getcwd()

def find_owners_files(repo_root, email):
    try:
        res = subprocess.run(
            ["git", "grep", "-l", "-i", email, "--", "**/OWNERS", "OWNERS"],
            cwd=repo_root, capture_output=True, text=True, check=True
        )
        return [line.strip() for line in res.stdout.splitlines() if line.strip()]
    except subprocess.CalledProcessError:
        return []
    except Exception as e:
        print(f"Error running git grep: {e}", file=sys.stderr)
        owners_files = []
        email_lower = email.lower()
        for root, dirs, files in os.walk(repo_root):
            dirs[:] = [d for d in dirs if d not in (".git", "out", "third_party")]
            for file in files:
                if file == "OWNERS":
                    path = os.path.join(root, file)
                    try:
                        with open(path, 'r', encoding='utf-8', errors='ignore') as f:
                            content = f.read()
                        if email_lower in content.lower():
                            owners_files.append(os.path.relpath(path, repo_root))
                    except Exception:
                        pass
        return owners_files

def analyze_owners_files(repo_root, files, email, inclusion_target):
    email_regex = re.compile(r'[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+')
    
    inc_target_clean = inclusion_target.lstrip("/").strip()
    inc_target_dir = os.path.dirname(inc_target_clean) + "/" if os.path.dirname(inc_target_clean) else ""
    
    no_inclusion_outside = []
    no_inclusion_inside_noparent = []
    no_inclusion_inside_inherits = []
    includes_target = []
    
    email_lower = email.lower()
    
    for rel_path in files:
        abs_path = os.path.join(repo_root, rel_path)
        if not os.path.exists(abs_path):
            continue
        
        with open(abs_path, 'r', encoding='utf-8', errors='ignore') as f:
            lines = f.readlines()
        
        content = "".join(lines)
        has_explicit = inc_target_clean in content
        has_noparent = "set noparent" in content
        is_inside_target_dir = inc_target_dir and rel_path.startswith(inc_target_dir)
        is_target_itself = rel_path == inc_target_clean
        
        owners = set()
        includes = []
        
        for line in lines:
            if '#' in line:
                line = line.split('#')[0]
            line = line.strip()
            if not line:
                continue
            
            if "file://" in line:
                match_inc = re.search(r'file://\S+', line)
                if match_inc:
                    includes.append(match_inc.group(0))
            
            emails = email_regex.findall(line)
            for em in emails:
                owners.add(em.lower())
                
        if email_lower in owners:
            owners.remove(email_lower)
            
        num_other_owners = len(owners)
        owners_list_str = ", ".join(sorted(list(owners))) if owners else "*None*"
        includes_str = ", ".join(includes) if includes else "*None*"
        
        file_info = {
            "path": rel_path,
            "other_owners_count": num_other_owners,
            "other_owners_list": owners_list_str,
            "includes": includes_str
        }
        
        if has_explicit:
            includes_target.append((file_info, f"Explicitly includes `file://{inc_target_clean}`"))
        elif is_target_itself:
            no_inclusion_inside_noparent.append((file_info, f"The `{inc_target_clean}` file itself"))
        elif is_inside_target_dir:
            if has_noparent:
                no_inclusion_inside_noparent.append((file_info, f"Inside `{inc_target_dir}` but has `set noparent` (No inheritance)"))
            else:
                no_inclusion_inside_inherits.append((file_info, f"Inside `{inc_target_dir}` (Inherits from `{inc_target_clean}` automatically)"))
        else:
            no_inclusion_outside.append((file_info, f"Outside `{inc_target_dir}` and does not include `//{inc_target_clean}`"))
            
    return no_inclusion_outside, no_inclusion_inside_noparent, no_inclusion_inside_inherits, includes_target

def generate_markdown(repo_root, email, inclusion_target, outside, inside_noparent, inside_inherits, includes):
    inc_target_clean = inclusion_target.lstrip("/").strip()
    inc_target_dir = os.path.dirname(inc_target_clean) + "/" if os.path.dirname(inc_target_clean) else ""
    
    md = []
    md.append(f"# OWNERS Files Analysis for {email}")
    md.append("")
    md.append(f"This report lists all `OWNERS` files in the repository where **{email}** is a member, categorized by whether **`//{inc_target_clean}`** is a member (either explicitly included or implicitly inherited).")
    md.append("")
    
    md.append("## Summary Table")
    md.append("| Category | Count of Files | Description |")
    md.append("| :--- | :---: | :--- |")
    md.append(f"| [Strict Matches (No `//{inc_target_clean}`)](#1-strict-matches-no-inclusion) | {len(outside) + len(inside_noparent)} | Outside `{inc_target_dir}` (or inside with `set noparent`), with no explicit inclusion of `//{inc_target_clean}`. |")
    md.append(f"| [Implicit Matches (Inherited `//{inc_target_clean}`)](#2-implicit-matches-via-inheritance) | {len(inside_inherits)} | Inside `{inc_target_dir}` directory and inherits from `//{inc_target_clean}` by default. |")
    md.append(f"| [Explicitly Includes `//{inc_target_clean}`](#3-explicitly-includes-inclusion) | {len(includes)} | Explicitly includes `file://{inc_target_clean}`. |")
    md.append("")
    
    def add_table_section(title, description, items, anchor):
        md.append(f"## {anchor}")
        md.append(description)
        md.append("")
        md.append("| OWNER File Path | Other Owners Count | Other Owners | Included Files | Notes |")
        md.append("| :--- | :---: | :--- | :--- | :--- |")
        for info, note in items:
            path = info["path"]
            count = info["other_owners_count"]
            owners = info["other_owners_list"]
            inc = info["includes"]
            md.append(f"| [{path}](file://{repo_root}/{path}) | **{count}** | {owners} | {inc} | {note} |")
        md.append("")
        
    add_table_section(
        f"1. Strict Matches (No `//{inc_target_clean}`)",
        f"These are the `OWNERS` files where you are a member, and `//{inc_target_clean}` is **not** a member (either explicitly or implicitly).",
        outside + inside_noparent,
        "1. Strict Matches (No inclusion)"
    )
    
    if inc_target_dir:
        add_table_section(
            "2. Implicit Matches (Via Inheritance)",
            f"These are files under the `{inc_target_dir}` directory where you are a member. While they do **not** explicitly include `file://{inc_target_clean}`, they inherit all owners from `//{inc_target_clean}` because they are in a subdirectory and do not specify `set noparent`.",
            inside_inherits,
            "2. Implicit Matches (Via Inheritance)"
        )
    
    add_table_section(
        f"3. Explicitly Includes `//{inc_target_clean}`",
        f"These files explicitly include `file://{inc_target_clean}`, so all members of `//{inc_target_clean}` are owners of these files.",
        includes,
        "3. Explicitly Includes inclusion"
    )
    
    return "\n".join(md)

def main():
    parser = argparse.ArgumentParser(description="Analyze OWNERS files in a repository to find membership and inclusions.")
    parser.add_argument("--email", help="The email address of the owner to search for. Defaults to 'git config user.email'.")
    parser.add_argument("--check-inclusion", default="media/OWNERS", help="The OWNERS file path to check inclusion for (default: 'media/OWNERS').")
    parser.add_argument("--repo-root", help="The path to the repository root (defaults to auto-detecting git root).")
    parser.add_argument("--output", help="Path to write the markdown report (prints to stdout if omitted).")
    
    args = parser.parse_args()
    
    repo_root = args.repo_root or find_git_root()
    repo_root = os.path.abspath(repo_root)
    
    email = args.email or get_git_email(repo_root)
    if not email:
        print("Error: Could not determine email address. Please specify --email.", file=sys.stderr)
        sys.exit(1)
        
    print(f"Analyzing OWNERS files in {repo_root}...", file=sys.stderr)
    print(f"Target Owner: {email}", file=sys.stderr)
    print(f"Inclusion Target: {args.check_inclusion}", file=sys.stderr)
    
    owners_files = find_owners_files(repo_root, email)
    print(f"Found {len(owners_files)} OWNERS files containing {email}.", file=sys.stderr)
    
    outside, inside_noparent, inside_inherits, includes = analyze_owners_files(
        repo_root, owners_files, email, args.check_inclusion
    )
    
    report = generate_markdown(
        repo_root, email, args.check_inclusion, outside, inside_noparent, inside_inherits, includes
    )
    
    if args.output:
        out_abs = os.path.abspath(args.output)
        os.makedirs(os.path.dirname(out_abs), exist_ok=True)
        with open(out_abs, 'w', encoding='utf-8') as f:
            f.write(report)
        print(f"Report generated successfully at: {out_abs}", file=sys.stderr)
    else:
        print(report)

if __name__ == "__main__":
    main()
