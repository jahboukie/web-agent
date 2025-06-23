#!/usr/bin/env python3
"""
Final fix for syntax errors in Python security files.
Replaces all literal \\n sequences with actual newlines and fixes any other syntax issues.
"""

import re

def fix_file_syntax(file_path):
    """Fix syntax issues in a Python file."""
    print(f"Fixing syntax in {file_path}")
    
    try:
        # Read the file
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Replace literal \n with actual newlines
        # Handle cases where \n appears as literal string
        content = content.replace('\\n', '\n')
        
        # Fix any remaining issues with escaped characters
        content = re.sub(r'\\t', '\t', content)
        content = re.sub(r'\\"', '"', content)
        
        # Fix any line continuation issues
        # Replace patterns like: }\\n        \\n        #
        content = re.sub(r'}\s*\\\s*\n\s*\\\s*\n\s*#', '}\n        \n        #', content)
        
        # Fix any orphaned line continuation characters
        content = re.sub(r'\\\s*\n\s*\\\s*\n', '\n        \n', content)
        
        # Remove any remaining standalone backslashes at end of lines that aren't needed
        lines = content.split('\n')
        fixed_lines = []
        
        for i, line in enumerate(lines):
            # If line ends with just a backslash and the next line doesn't continue a statement
            if (line.strip().endswith('\\') and 
                i + 1 < len(lines) and
                lines[i + 1].strip() and
                not lines[i + 1].strip().startswith(('and ', 'or ', '+', '-', '*', '/', '.'))):
                # Remove the backslash
                line = line.rstrip('\\').rstrip()
            
            fixed_lines.append(line)
        
        content = '\n'.join(fixed_lines)
        
        # Write the fixed content back
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
        
        print(f"✅ Fixed syntax in {file_path}")
        return True
        
    except Exception as e:
        print(f"❌ Error fixing {file_path}: {e}")
        return False

def main():
    """Fix syntax in all affected files."""
    files_to_fix = [
        '/mnt/c/Users/scorp/web_agent/app/security/incident_response.py',
        '/mnt/c/Users/scorp/web_agent/app/security/cloud_security.py',
        '/mnt/c/Users/scorp/web_agent/app/compliance/soc2_framework.py'
    ]
    
    success_count = 0
    for file_path in files_to_fix:
        if fix_file_syntax(file_path):
            success_count += 1
    
    print(f"\n🎯 Fixed {success_count}/{len(files_to_fix)} files")
    
    if success_count == len(files_to_fix):
        print("🎉 All syntax errors should now be resolved!")
    else:
        print("⚠️  Some files may still have issues.")

if __name__ == '__main__':
    main()