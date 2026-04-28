import os, re
from pathlib import Path

ROOT = Path('C:/Users/eltmsah/Desktop/Github/Q-Vault')
EXCLUDE_DIRS = {'.venv', '__pycache__', '.git', '.kilo', 'tests', 'docs'}

data = {
    'hex_colors': [],
    'time_sleep': [],
    'broad_except': [],
    'subprocess': [],
    'eval_exec': [],
}

events_emitted = set()
events_subscribed = set()
declared_events = set()

for f in ROOT.rglob('*.py'):
    if any(x in str(f) for x in EXCLUDE_DIRS):
        continue
    try:
        text = f.read_text(encoding='utf-8', errors='ignore')
        
        if 'assets' not in str(f) and 'design_tokens' not in str(f):
            for m in re.finditer(r'(#[0-9a-fA-F]{3,8})\b', text):
                data['hex_colors'].append(f'{f.name}:{m.group(1)}')
                
        if 'time.sleep' in text:
            data['time_sleep'].append(f.name)
            
        if 'subprocess' in text: data['subprocess'].append(f.name)
        if re.search(r'\b(eval|exec)\(', text): data['eval_exec'].append(f.name)
        if re.search(r'except\s+Exception\s*(?:as\s+\w+)?\s*:', text):
            data['broad_except'].append(f.name)
            
        if 'SystemEvent' in text:
            emits = re.findall(r'\bemit\s*\(\s*(?:SystemEvent\.)?([A-Z_0-9]+)', text)
            subs = re.findall(r'\bsubscribe\s*\(\s*(?:SystemEvent\.)?([A-Z_0-9]+)', text)
            events_emitted.update(emits)
            events_subscribed.update(subs)
            
        if f.name == 'event_bus.py':
            declared_events.update(re.findall(r'\b([A-Z_0-9]+)\s*=\s*[\'\"].*?[\'\"]', text))
            
    except Exception as e: 
        print(f"Error on {f}: {e}")

print("=== UI/THEME ===")
print(f"Raw Hex Colors Found: {len(data['hex_colors'])}")
print(f"Files with hex colors: {list(set(x.split(':')[0] for x in data['hex_colors']))[:10]}")

print("\n=== THREADING & SECURITY ===")
print(f"time.sleep usage: {len(set(data['time_sleep']))} files: {list(set(data['time_sleep']))[:5]}")
print(f"broad excepts: {len(set(data['broad_except']))} files")
print(f"subprocess usage: {len(set(data['subprocess']))} files: {list(set(data['subprocess']))[:5]}")
print(f"eval/exec: {len(set(data['eval_exec']))} files")

print("\n=== EVENT BUS ===")
print(f"Declared Events: {len(declared_events)}")
print(f"Emitted: {len(events_emitted)}")
print(f"Subscribed: {len(events_subscribed)}")

emit_no_sub = events_emitted - events_subscribed
sub_no_emit = events_subscribed - events_emitted

print(f"Emit but no sub ({len(emit_no_sub)}): {emit_no_sub}")
print(f"Sub but no emit ({len(sub_no_emit)}): {sub_no_emit}")
