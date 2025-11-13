#!/usr/bin/env python3
"""檢查 google-genai API 可用的類別"""

from google import genai
from google.genai import types

print("=== google.genai.types 可用的類別 ===")
print([x for x in dir(types) if not x.startswith('_')])

print("\n=== 尋找 FileSearch 相關的類別 ===")
print([x for x in dir(types) if 'file' in x.lower() or 'search' in x.lower()])

print("\n=== 尋找 Tool 相關的類別 ===")
print([x for x in dir(types) if 'tool' in x.lower()])

print("\n=== Tool 類別的屬性 ===")
if hasattr(types, 'Tool'):
    print(dir(types.Tool))
