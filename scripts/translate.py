#!/usr/bin/env python3
"""Translate new official Spanish headlines locally; no paid or remote inference API."""
import argparse
import copy
import hashlib
import json
import re
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from update import atomic_json

ROOT = Path(__file__).resolve().parents[1]
MODEL = 'facebook/nllb-200-distilled-600M'
MODEL_REVISION = 'f8d333a098d19b4fd9a8b18f94170487ad3f821d'
ENGINE = 'nllb-es-zh-football-v1'



def glossary_key(glossary):
    return hashlib.sha256(json.dumps(glossary['entries'], sort_keys=True, ensure_ascii=False).encode()).hexdigest()[:16]


def current(item, key):
    if not item.get('titleZh'):
        return False
    meta = item.get('translation')
    # Existing Chinese titles without machine metadata are editorial content.
    if not meta:
        return True
    return (meta.get('sourceTitle') == item['title'] and meta.get('engine') == ENGINE
            and meta.get('glossaryRevision') == key)


def protect(text, glossary):
    """One longest-first regex avoids partial names and matching inside other words."""
    aliases = {a.casefold(): e['zh'] for e in glossary['entries'] for a in e['aliases']}
    pattern = re.compile(r'(?<!\w)(?:' + '|'.join(re.escape(a) for a in sorted(aliases, key=len, reverse=True)) + r')(?!\w)', re.IGNORECASE)
    saved = []
    def replace(match):
        token = 'ZXQ' + chr(65 + len(saved))
        saved.append((token, aliases[match.group().casefold()]))
        return token
    return pattern.sub(replace, text), saved


def restore(text, saved):
    # Never publish untranslated or corrupted entity markers as if successful.
    for token, zh in saved:
        if text.count(token) != 1:
            raise ValueError('译名标记未完整保留')
        text = text.replace(token, zh)
    if 'ZXQ' in text:
        raise ValueError('译名标记未完整还原')
    return text


def clean(text):
    text = re.sub(r'\s+', ' ', text).strip()
    text = re.sub(r'([\u3400-\u9fff]) +(?=[\u3400-\u9fff，。！？：；、])', r'\1', text)
    return text


def validate(source, translated):
    if not translated or len(translated) > 600 or not re.search(r'[\u3400-\u9fff]', translated):
        raise ValueError('未生成有效中文标题')
    # Preserve scores, years and age-group numbers. Do not silently publish invented numbers.
    if Counter(re.findall(r'\d+', source)) != Counter(re.findall(r'\d+', translated)):
        raise ValueError('标题中的数字未完整保留')


def football_title(title, glossary):
    """Small reusable Spanish football headline grammar, not a list of current articles."""
    def term(value):
        masked, saved = protect(value.strip(), glossary)
        return restore(masked, saved)
    match = re.fullmatch(r'El (.+?) empata en (.+)', title)
    if match:
        return term(match[1]) + '在' + term(match[2]) + '战平'
    match = re.fullmatch(r'El (.+?) se entrenó en (.+)', title)
    if match:
        return term(match[1]) + '在' + term(match[2]) + '完成训练'
    match = re.fullmatch(r'Minuto de silencio antes del (.+)', title)
    if match:
        return term(match[1]) + '赛前默哀一分钟'
    match = re.fullmatch(r'Convocatoria del (.+?) contra (?:el |la )?(.+)', title)
    if match:
        return term(match[1]) + '对阵' + term(match[2]) + '的比赛大名单'
    match = re.fullmatch(r'(.+?): partidazo en la (.+)', title)
    if match:
        return term(match[1]) + '：' + term(match[2]) + '焦点战'
    match = re.fullmatch(r'(.+?) opta al premio a la mejor jugadora joven del Balón de Oro (\d{4})', title)
    if match:
        return term(match[1]) + '角逐' + match[2] + '年金球奖最佳年轻女足球员奖'
    match = re.fullmatch(r'Ya están disponibles las entradas para los partidos contra (.+)', title)
    if match:
        opponents = re.split(r'\s+(?:y|e)\s+', match[1])
        return '对阵' + '、'.join(term(x) for x in opponents) + '的比赛门票现已开售'
    match = re.fullmatch(r'El (.+?) homenajea a las campeonas del Mundial sub-(\d+) y el Europeo sub-(\d+)', title)
    if match:
        return term(match[1]) + '向U' + match[2] + '女足世界杯及U' + match[3] + '女足欧锦赛冠军致敬'
    match = re.fullmatch(r'Remontada en (?:el |la )?(.+)', title)
    if match:
        return '在' + term(match[1]) + '完成逆转'
    return None


class OfflineTranslator:
    def batch(self, texts):
        # Lazy imports: a normal no-new-headlines run needs no model dependencies.
        import torch
        from transformers import AutoModelForSeq2SeqLM, AutoTokenizer
        torch.set_num_threads(2)
        tokenizer = AutoTokenizer.from_pretrained(MODEL, revision=MODEL_REVISION, src_lang='spa_Latn')
        model = AutoModelForSeq2SeqLM.from_pretrained(MODEL, revision=MODEL_REVISION,
                                                    low_cpu_mem_usage=True).eval()
        decoded = []
        for start in range(0, len(texts), 4):
            batch = tokenizer(texts[start:start+4], return_tensors='pt', padding=True, truncation=False)
            if batch['input_ids'].shape[1] > 400:
                raise ValueError('标题超出翻译长度限制')
            with torch.inference_mode():
                tokens = model.generate(**batch, forced_bos_token_id=tokenizer.convert_tokens_to_ids('zho_Hans'),
                                        num_beams=4, max_new_tokens=240)
            decoded.extend(tokenizer.batch_decode(tokens, skip_special_tokens=True))
        return decoded


def translate_feed(feed, glossary, translator, now=None):
    result = copy.deepcopy(feed)
    key = glossary_key(glossary)
    items = result.get('news', {}).get('items', [])
    pending = [n for n in items if not current(n, key)]
    if not pending:
        return result, []
    stamp = (now or datetime.now(timezone.utc)).isoformat().replace('+00:00', 'Z')
    errors = []
    for n in pending:
        # A stale machine title must never be presented for an edited source title.
        if n.get('translation'):
            n.pop('titleZh', None)
            n.pop('translation', None)
        n.pop('translationError', None)
    def accept(n, translated, method):
        translated = clean(translated)
        validate(n['title'], translated)
        n['titleZh'] = translated
        n['translation'] = {'kind': 'machine', 'engine': ENGINE, 'sourceTitle': n['title'],
                            'glossaryRevision': key, 'translatedAt': stamp, 'method': method}
    model_pending = []
    for n in pending:
        checked = football_title(n['title'], glossary)
        if checked:
            try:
                accept(n, checked, 'football-rule')
            except ValueError:
                model_pending.append(n)
        else:
            model_pending.append(n)
    if model_pending:
        try:
            protected = [protect(n['title'], glossary) for n in model_pending]
            outputs = translator.batch([p[0] for p in protected])
            if len(outputs) != len(model_pending):
                raise ValueError('翻译返回数量不符')
            for n, (source, saved), out in zip(model_pending, protected, outputs):
                try:
                    accept(n, restore(out, saved), 'neural-model')
                except Exception as exc:
                    n['translationError'] = str(exc)[:160]
                    errors.append(n['url'] + ': ' + str(exc)[:160])
        except Exception as exc:
            for n in model_pending:
                n['translationError'] = '翻译暂不可用，保留官方原题'
            errors.append('翻译模型暂不可用：' + str(exc)[:200])
    result['news']['translationStatus'] = {'attemptedAt': stamp, 'pending': sum(not current(n, key) for n in items),
                                            'error': '部分标题翻译失败，保留原题' if errors else None}
    return result, errors


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--data', type=Path, default=ROOT/'site/data/feed.json')
    parser.add_argument('--glossary', type=Path, default=ROOT/'data/translation-glossary.json')
    parser.add_argument('--check-model', action='store_true')
    parser.add_argument('--check', action='store_true', help='Print true if there is translation work; no model imports/downloads')
    args = parser.parse_args()
    feed = json.loads(args.data.read_text(encoding='utf-8'))
    glossary = json.loads(args.glossary.read_text(encoding='utf-8'))
    if args.check or args.check_model:
        pending = [n for n in feed.get('news', {}).get('items', []) if not current(n, glossary_key(glossary))]
        print(str(any(not football_title(n['title'], glossary) for n in pending) if args.check_model else bool(pending)).lower())
        return 0
    result, errors = translate_feed(feed, glossary, OfflineTranslator())
    atomic_json(args.data, result)
    print('中文标题：', sum(bool(n.get('titleZh')) for n in result['news']['items']), '/', len(result['news']['items']))
    for error in errors:
        print(error, file=sys.stderr)
    return int(bool(errors))

if __name__ == '__main__':
    sys.exit(main())
