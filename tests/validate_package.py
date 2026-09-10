"""Portable local checks for the exact manifest and frontmatter subset used here."""
import json
from pathlib import Path
import re

root=Path(__file__).resolve().parents[1]
src=root/'src'
manifest=json.loads((src/'marketplace.json').read_text(encoding='utf-8'))
assert sum(s.get('entrypoint') is True for s in manifest['skills'])==1
assert len({s['id'] for s in manifest['skills']})==len(manifest['skills'])
assert {s['path'] for s in manifest['skills']}=={str(p.relative_to(src)).replace('\\','/') for p in (src/'skills').iterdir() if p.is_dir()}
for skill in manifest['skills']:
    directory=(src/skill['path']).resolve()
    assert directory.is_relative_to(src)

    text=(directory/'SKILL.md').read_text(encoding='utf-8')
    assert text.startswith('---\n')
    frontmatter=text.split('---',2)[1]
    lines=frontmatter.strip().splitlines()
    fields={}
    for line in lines:
        if ': ' in line and not line.startswith(' '):
            key,value=line.split(': ',1)
            fields[key]=value.strip(' >"')
    description_lines=[]
    collecting=False
    for line in lines:
        if line.startswith('description:'):
            collecting=True
            description_lines.append(line.split(':',1)[1].strip(' >"'))
        elif collecting and line.startswith('  '):
            description_lines.append(line.strip())
        elif collecting:
            collecting=False
    fields['description']=' '.join(description_lines).strip()
    assert fields['name']==directory.name==skill['id']
    assert re.fullmatch(r'[a-z0-9]+(?:-[a-z0-9]+)*',fields['name']) and len(fields['name'])<=64
    assert 1<=len(fields['description'])<=1024
    assert len(fields.get('compatibility',''))<=500
    assert 'allowed-tools' in frontmatter
    assert len(text.splitlines())<500
    for target in re.findall(r'\]\(([^)]+)\)',text):
        if '://' not in target:
            assert (directory/target).exists(),(skill['id'],target)
checks=json.loads((src/'skills/audit-orchestrator/references/checks.json').read_text(encoding='utf-8'))
assert len(checks)==len({c['check_id'] for c in checks})==134
valid_skill_ids = {s['id'] for s in manifest['skills']}
for c in checks:
    assert all(c[k] for k in ('detection','activation','solution','solution_level','reference_band','owner'))
    assert c['owner'] in valid_skill_ids, f"Check {c['check_id']} has owner '{c['owner']}' not in marketplace manifest: {valid_skill_ids}"
assert sum(p.stat().st_size for p in root.rglob('*') if p.is_file())<50_000_000
print('Manifest, seven skill frontmatters/links, 134 joined IDs with valid owners, and uncompressed size validated.')
