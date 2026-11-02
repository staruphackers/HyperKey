#!/usr/bin/env python3
"""HyperKey: generate zh-Hant from zh-Hans in the String Catalogs.

zh-Hans → OpenCC s2twp (Taiwan phrases) → HyperKey glossary.
Re-run after upstream changes; manual zh-Hant overrides go in GLOSSARY or OVERRIDES.
Usage: python3 scripts/gen-zh-hant.py [--check]
"""
import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CATALOGS = [ROOT / 'AhaKey Studio/Localization/Localizable.xcstrings',
            ROOT / 'AhaKey Studio/Localization/InfoPlist.xcstrings']
SEP = '\n@@HKSEP@@\n'

# Applied after s2twp, longest first. Taiwan software terminology.
GLOSSARY = {
    '守護進程': '常駐程式',
    '守護程序': '常駐程式',
    '子程序': '子程式',
    '程序': '程式',
    '後臺': '背景',
    '後台': '背景',
    '許可權': '權限',
    '訪問': '存取',
    '語音識別': '語音辨識',
    '默認': '預設',
    '信息': '訊息',
    '進程': '行程',
    '固件': '韌體',
    '拔桿': '撥桿',
    '撥杆': '撥桿',
    '拔杆': '撥桿',
    '宏步驟': '巨集步驟',
    '宏': '巨集',
    '幀': '影格',
    '屏幕': '螢幕',
    '賬號': '帳號',
    '賬戶': '帳戶',
    '激活': '啟用',
    '鏈接': '連結',
    '調試': '偵錯',
    '菜單': '選單',
    '彈窗': '彈出視窗',
    '回調': '回呼',
    '異步': '非同步',
    '同步到設備': '同步到裝置',
}
# Words that legitimately contain a glossary key and must stay untouched.
PROTECT = ['宏觀', '螢幕']


def convert(texts):
    if not texts:
        return []
    out = subprocess.run(['opencc', '-c', 's2twp'], input=SEP.join(texts),
                         capture_output=True, text=True, check=True).stdout
    parts = out.split(SEP)
    if len(parts) != len(texts):
        raise SystemExit(f'opencc split mismatch: {len(parts)} != {len(texts)}')
    return [apply_glossary(p) for p in parts]


def apply_glossary(text):
    holders = {}
    for i, word in enumerate(PROTECT):
        token = f'\x00{i}\x00'
        if word in text:
            holders[token] = word
            text = text.replace(word, token)
    for src in sorted(GLOSSARY, key=len, reverse=True):
        text = text.replace(src, GLOSSARY[src])
    for token, word in holders.items():
        text = text.replace(token, word)
    return text


def collect(node, sink):
    if isinstance(node, dict):
        unit = node.get('stringUnit')
        if isinstance(unit, dict) and isinstance(unit.get('value'), str):
            sink.append(unit)
        for v in node.values():
            collect(v, sink)
    elif isinstance(node, list):
        for v in node:
            collect(v, sink)


def generate(path, check):
    data = json.loads(path.read_text(encoding='utf-8'))
    units, copies = [], 0
    for entry in data.get('strings', {}).values():
        locs = entry.get('localizations')
        if not locs or 'zh-Hans' not in locs:
            continue
        clone = json.loads(json.dumps(locs['zh-Hans'], ensure_ascii=False))
        found = []
        collect(clone, found)
        units.extend(found)
        locs['zh-Hant'] = clone
        copies += 1
    for unit, value in zip(units, convert([u['value'] for u in units])):
        unit['value'] = value
        unit['state'] = 'translated'
    text = json.dumps(data, ensure_ascii=False, indent=2, separators=(',', ': ')) + '\n'
    if check:
        return copies, path.read_text(encoding='utf-8') == text
    path.write_text(text, encoding='utf-8')
    return copies, True


def main():
    check = '--check' in sys.argv
    ok = True
    for path in CATALOGS:
        copies, same = generate(path, check)
        print(f'{path.name}: {copies} entries' + ('' if same else ' (out of date)'))
        ok = ok and same
    sys.exit(0 if ok else 1)


if __name__ == '__main__':
    main()
