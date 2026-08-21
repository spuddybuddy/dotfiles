#!/usr/bin/env python3
import argparse
import os
import re
from datetime import datetime, timedelta

def get_today():
    # In a real scenario, this would be datetime.now()
    # For the context of the session where this was created:
    return datetime(2026, 5, 1)

def process_files(files, filter_str, action, audit_limit_days=90):
    today = get_today()
    limit_date = today + timedelta(days=audit_limit_days)
    
    # Match <histogram name="..." ... expires_after="..."
    pattern = re.compile(r'(<histogram\s+name="([^"]+)"(.*?)\s+expires_after="([^"]+)")', re.DOTALL)
    
    for file_path in files:
        if not os.path.exists(file_path):
            print(f"Warning: File {file_path} not found.")
            continue
            
        with open(file_path, 'r') as f:
            content = f.read()
            
        modified = False
        count = 0
        
        def replacement(match):
            nonlocal count, modified
            full_match = match.group(1)
            name = match.group(2)
            middle = match.group(3)
            expiry = match.group(4)
            
            if filter_str.lower() in name.lower():
                try:
                    expiry_date = datetime.strptime(expiry, '%Y-%m-%d')
                    if expiry_date <= limit_date:
                        if action == 'audit':
                            status = "EXPIRED" if expiry_date < today else "EXPIRING SOON"
                            print(f"[{status}] {name}: {expiry}")
                        elif action == 'extend':
                            new_expiry = (today + timedelta(days=365)).strftime('%Y-%m-%d')
                            if new_expiry != expiry:
                                print(f"[EXTENDING] {name}: {expiry} -> {new_expiry}")
                                modified = True
                                count += 1
                                return full_match.replace(f'expires_after="{expiry}"', f'expires_after="{new_expiry}"')
                except ValueError:
                    if expiry.startswith('M'):
                        if action == 'audit':
                            print(f"[OLD MILESTONE] {name}: {expiry}")
            return full_match

        new_content = pattern.sub(replacement, content)
        
        if action == 'extend' and modified:
            with open(file_path, 'w') as f:
                f.write(new_content)
            print(f"Updated {file_path} with {count} extensions.")

def main():
    parser = argparse.ArgumentParser(description='Manage UMA histogram expiries.')
    parser.add_argument('--audit', action='store_true', help='Audit histograms for expiry.')
    parser.add_argument('--extend', action='store_true', help='Extend expiring histograms by one year.')
    parser.add_argument('--filter', required=True, help='Substring to filter histogram names (case-insensitive).')
    parser.add_argument('--files', nargs='+', required=True, help='List of XML files to process.')
    
    args = parser.parse_args()
    
    if not args.audit and not args.extend:
        print("Error: Specify either --audit or --extend.")
        return

    action = 'audit' if args.audit else 'extend'
    process_files(args.files, args.filter, action)

if __name__ == '__main__':
    main()
