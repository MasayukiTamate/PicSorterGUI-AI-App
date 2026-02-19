import re

def convert_md_to_html(md_path, html_path):
    with open(md_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()

    html = ['<!DOCTYPE html>', '<html>', '<head>', '<meta charset="utf-8">', '<title>GazoTools Manual</title>', 
            '<style>body{font-family:"Segoe UI",sans-serif;max-width:800px;margin:2em auto;padding:0 1em;line-height:1.6;color:#333;background-color:#fefefe;}h1,h2,h3{color:#2c3e50;}table{border-collapse:collapse;width:100%;margin:1em 0;}th,td{border:1px solid #ddd;padding:10px;text-align:left;}th{background-color:#f2f2f2;}code{background:#f4f4f4;padding:2px 5px;border-radius:3px;font-family:monospace;}blockquote{border-left:4px solid #ccc;margin:0;padding-left:1em;color:#666;}hr{border:0;height:1px;background:#eee;margin:2em 0;}</style>', 
            '</head>', '<body>']

    in_table = False
    
    for i, line in enumerate(lines):
        line = line.strip()
        
        # Headers
        if line.startswith('# '):
            html.append(f'<h1>{line[2:]}</h1>')
            continue
        elif line.startswith('## '):
            html.append(f'<h2>{line[3:]}</h2>')
            continue
        elif line.startswith('### '):
            html.append(f'<h3>{line[4:]}</h3>')
            continue
        elif line.startswith('#### '):
            html.append(f'<h4>{line[5:]}</h4>')
            continue
            
        # Divider
        if line.startswith('---'):
            html.append('<hr>')
            continue
            
        # Bold
        line = re.sub(r'\*\*(.*?)\*\*', r'<strong>\1</strong>', line)
        
        # Table
        if line.startswith('|'):
            if not in_table:
                html.append('<table>')
                in_table = True
            
            if '---' in line: continue # Skip separator line

            # Determine if header by looking at next line (simple heuristic: if next line is separator, current is header)
            # This logic is fragile but suffices for this specific markdown file
            is_header = False
            if i + 1 < len(lines) and '---' in lines[i+1]:
                is_header = True
            
            cells = [c.strip() for c in line.strip('|').split('|')]
            tag = 'th' if is_header else 'td'
            
            row = '<tr>'
            for c in cells:
                row += f'<{tag}>{c}</{tag}>'
            row += '</tr>'
            html.append(row)
            continue
        else:
            if in_table:
                html.append('</table>')
                in_table = False

        # List
        if line.startswith('- '):
            html.append(f'<ul><li>{line[2:]}</li></ul>')
            continue
        elif line.startswith('1. '): 
            html.append(f'<ol><li>{line[3:]}</li></ol>')
            continue
            
        # Empty line
        if not line:
            continue
            
        # Normal text
        html.append(f'<p>{line}</p>')

    if in_table: html.append('</table>')
    html.append('</body></html>')

    with open(html_path, 'w', encoding='utf-8') as f:
        f.write('\n'.join(html))

convert_md_to_html(r'k:\GitHub\Gazo_tools\docs\GazoTools_Manual.md', r'k:\GitHub\Gazo_tools\docs\GazoTools_Manual.html')
