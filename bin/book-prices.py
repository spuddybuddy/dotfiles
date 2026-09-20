#!/usr/bin/env python3
import os
import glob
import zipfile
import xml.etree.ElementTree as ET

# Configuration
INPUT_DIR = '/Volumes/AhchTo/Calibre Library'
OUTPUT_HTML = '/Users/mfoltz/tmp/price_checker.html'

def parse_opf_xml(xml_content, metadata):
    try:
        root = ET.fromstring(xml_content)
        namespaces = {
            'dc': 'http://purl.org/dc/elements/1.1/',
            'opf': 'http://www.idpf.org/2007/opf'
        }
        
        # Check for the 'library' tag
        for subject in root.findall('.//dc:subject', namespaces):
            if subject.text and subject.text.strip().lower() == 'library':
                metadata['has_library_tag'] = True
                break

        # Extract Title
        if metadata['title'] == 'Unknown Title':
            title_elem = root.find('.//dc:title', namespaces)
            if title_elem is not None and title_elem.text:
                metadata['title'] = title_elem.text.strip()

        # Extract ISBN
        if not metadata['isbn']:
            for identifier in root.findall('.//dc:identifier', namespaces):
                scheme = identifier.attrib.get('{http://www.idpf.org/2007/opf}scheme', '').lower()
                text = identifier.text or ''
                if scheme == 'isbn' or 'isbn' in text.lower() or text.startswith('978') or text.startswith('979'):
                    digits = ''.join(filter(str.isdigit, text))
                    if len(digits) in (10, 13):
                        metadata['isbn'] = digits
                        break
    except Exception as e:
        print(f"Error parsing OPF XML: {e}")

def extract_metadata(epub_path):
    metadata = {'isbn': None, 'title': 'Unknown Title', 'has_library_tag': False}

    # Check internal EPUB metadata
    try:
        with zipfile.ZipFile(epub_path, 'r') as archive:
            opf_file = next((item for item in archive.namelist() if item.endswith('.opf')), None)
            if opf_file:
                parse_opf_xml(archive.read(opf_file), metadata)
    except Exception as e:
        pass

    # Check external metadata.opf file
    external_opf = os.path.join(os.path.dirname(epub_path), 'metadata.opf')
    if os.path.isfile(external_opf):
        try:
            with open(external_opf, 'rb') as f:
                parse_opf_xml(f.read(), metadata)
        except Exception as e:
            pass

    return metadata

def generate_html(books):
    html_template = """<!DOCTYPE html>
<html>
<head>
    <title>Ebook Price Checker</title>
    <style>
        body {{ font-family: system-ui, sans-serif; margin: 40px; background: #f4f4f5; }}
        h1 {{ color: #18181b; }}
        .warning {{ background: #fef08a; padding: 10px; border-radius: 6px; color: #854d0e; margin-bottom: 20px; }}
        table {{ border-collapse: collapse; width: 100%; background: white; box-shadow: 0 1px 3px rgba(0,0,0,0.1); }}
        th, td {{ padding: 12px 16px; text-align: left; border-bottom: 1px solid #e4e4e7; }}
        th {{ background-color: #f8fafc; font-weight: 600; color: #475569; }}
        tr:hover {{ background-color: #f1f5f9; }}
        button {{ 
            background: #2563eb; color: white; border: none; padding: 8px 16px; 
            border-radius: 4px; cursor: pointer; font-weight: 500;
        }}
        button:hover {{ background: #1d4ed8; }}
        .links a {{ color: #2563eb; text-decoration: none; margin-right: 12px; font-size: 0.9em; }}
        .links a:hover {{ text-decoration: underline; }}
    </style>
    <script>
        function openStores(isbn) {{
            // Construct the search URLs without B&N
            const urls = [
                `https://play.google.com/store/search?q=${{isbn}}&c=books`,
                `https://www.kobo.com/us/en/search?query=${{isbn}}`
            ];
            
            // Open each in a new tab
            urls.forEach(url => window.open(url, '_blank'));
        }}
    </script>
</head>
<body>
    <h1>Ebook Price Checker</h1>
    <div class="warning">
        <strong>Important:</strong> Your browser's pop-up blocker will likely stop the second tab from opening. 
        When you click a button for the first time, look for the pop-up warning in your address bar and click <strong>"Always allow pop-ups from this file."</strong>
    </div>
    <table>
        <thead>
            <tr>
                <th>Title</th>
                <th>ISBN</th>
                <th>Check Prices</th>
                <th>Individual Links</th>
            </tr>
        </thead>
        <tbody>
            {rows}
        </tbody>
    </table>
</body>
</html>"""

    rows = []
    for book in books:
        isbn = book['isbn']
        row = f"""
            <tr>
                <td>{book['title']}</td>
                <td>{isbn}</td>
                <td><button onclick="openStores('{isbn}')">Open Both Stores</button></td>
                <td class="links">
                    <a href="https://play.google.com/store/search?q={isbn}&c=books" target="_blank">Google</a>
                    <a href="https://www.kobo.com/us/en/search?query={isbn}" target="_blank">Kobo</a>
                </td>
            </tr>"""
        rows.append(row)

    with open(OUTPUT_HTML, 'w', encoding='utf-8') as f:
        f.write(html_template.format(rows="\n".join(rows)))

def main():
    epub_files = glob.glob(os.path.join(INPUT_DIR, '**', '*.epub'), recursive=True)
    books_to_check = []
    
    print("Scanning EPUBs...")
    for epub_file in epub_files:
        metadata = extract_metadata(epub_file)
        
        if metadata['has_library_tag'] and metadata['isbn']:
            books_to_check.append(metadata)
            print(f"Found: {metadata['title']} ({metadata['isbn']})")
            
    print(f"\nFound {len(books_to_check)} books matching criteria.")
    
    if books_to_check:
        generate_html(books_to_check)
        print(f"Success! Open {OUTPUT_HTML} in your web browser.")

if __name__ == "__main__":
    main()
