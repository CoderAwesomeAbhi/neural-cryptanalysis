# -*- coding: utf-8 -*-
"""Fix unicode characters in all Python files for Windows compatibility."""
import os
import re

REPLACEMENTS = {
    '✓': '[OK]',
    '✗': '[X]',
    '≤': '<=',
    '≥': '>=',
    '≈': '~=',
    '→': '->',
    '⟹': '=>',
    '∈': 'in',
    '∀': 'forall',
    '∃': 'exists',
    '≪': '<<',
    'χ²': 'chi^2',
    'γ': 'gamma',
    '−': '-',
    '…': '...',
    '─': '-',
    '│': '|',
    '┌': '+',
    '┐': '+',
    '└': '+',
    '┘': '+',
    '├': '+',
    '┤': '+',
    '┬': '+',
    '┴': '+',
    '┼': '+',
    '∝': 'proportional to',
    '∞': 'infinity',
}

def fix_unicode_in_file(filepath):
    """Replace unicode characters with ASCII equivalents."""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
        
        original = content
        for unicode_char, ascii_equiv in REPLACEMENTS.items():
            content = content.replace(unicode_char, ascii_equiv)
        
        if content != original:
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(content)
            return True
        return False
    except Exception as e:
        print(f"Error processing {filepath}: {e}")
        return False

def main():
    code_dir = os.path.dirname(__file__)
    fixed_count = 0
    
    for filename in os.listdir(code_dir):
        if filename.endswith('.py') and filename != 'fix_unicode.py':
            filepath = os.path.join(code_dir, filename)
            if fix_unicode_in_file(filepath):
                print(f"Fixed: {filename}")
                fixed_count += 1
    
    print(f"\nTotal files fixed: {fixed_count}")

if __name__ == '__main__':
    main()
