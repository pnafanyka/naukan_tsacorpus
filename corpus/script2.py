from pathlib import Path
import json

all_glosses = []

for file in Path('corpus/naukan').iterdir():
    if not file.name.endswith('.json'):
        continue
    doc = json.load(file.open(encoding='utf-8'))
    for sent in doc['sentences']:
        for word in sent['words']:
            if 'ana' in word:
                for ana in word['ana']:
                    all_glosses.extend(ana.get('gloss_index_ru', '').split('-'))

all_glosses = [x[:x.index('{') if '{' in x else len(x)].strip(' {}') for x in all_glosses]

print(json.dumps([{"type": "gloss", "value": gloss, "tooltip": gloss} for gloss in sorted(set(all_glosses))], ensure_ascii=False))