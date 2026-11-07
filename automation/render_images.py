"""Offline v2.2 renderer. No network, automatic wrapping, or font scaling."""
import argparse
from collections import Counter
import csv
import hashlib
import json
from pathlib import Path
import re
import unicodedata

from PIL import Image, ImageDraw, ImageFont
from fontTools.ttLib import TTFont

ROOT = Path(__file__).resolve().parents[1]
FONT = ROOT / 'assets/fonts/ZenMaruGothic-Bold.ttf'
FIELDS = ['row', 'design_id', 'status', 'reason', 'columns', 'file']


class Review(ValueError):
    pass


def read_catalog(path):
    # Parse the entire file before rendering: malformed quoting is file-fatal.
    with Path(path).open(encoding='utf-8-sig', newline='') as stream:
        reader = csv.reader(stream, strict=True)
        if next(reader, None) != ['design_id', 'message']:
            raise ValueError('CSV_HEADER: expected design_id,message')
        rows = list(reader)
    if not rows:
        raise ValueError('CSV_EMPTY: no design rows')
    return rows


def validate_row(row, duplicates):
    if len(row) != 2:
        raise ValueError('CSV_FIELDS: expected exactly two fields')
    design_id, message = row
    if not re.fullmatch(r'IC-[0-9]{4,12}', design_id):
        raise ValueError('DESIGN_ID: expected IC- and 4 to 12 digits')
    if design_id in duplicates:
        raise ValueError('DUPLICATE_ID: all occurrences rejected')
    if not message or message != message.strip():
        raise ValueError('MESSAGE_EMPTY_OR_WHITESPACE')
    if any(unicodedata.category(c).startswith('C') for c in message):
        raise ValueError('MESSAGE_CONTROL_CHARACTER')
    columns = message.split('/')
    if not 1 <= len(columns) <= 4 or any(not c.strip() for c in columns):
        raise ValueError('COLUMNS: require 1 to 4 nonempty explicit columns')
    return columns


def load_layout(path):
    cfg = json.loads(Path(path).read_text(encoding='utf-8'))
    if cfg.get('verified') is not True:
        raise Review('LAYOUT_UNVERIFIED: v2.2 reference required')
    for key in ('width', 'height', 'font_size', 'column_pitch', 'text_top', 'center_x', 'margin', 'max_chars'):
        if type(cfg.get(key)) is not int or not 0 < cfg[key] <= 10000:
            raise ValueError('LAYOUT_INVALID: ' + key)
    if type(cfg.get('character_gap')) is not int or not 0 <= cfg['character_gap'] <= 1000:
        raise ValueError('LAYOUT_INVALID: character_gap')
    if cfg['column_pitch'] < cfg['font_size']:
        raise ValueError('LAYOUT_INVALID: columns overlap')
    if cfg['width'] * cfg['height'] > 40000000:
        raise ValueError('LAYOUT_INVALID: canvas too large')
    points = cfg.get('arrow_points')
    if not isinstance(points, list) or len(points) < 3:
        raise ValueError('LAYOUT_INVALID: arrow polygon required')
    for point in points:
        if not isinstance(point, list) or len(point) != 2 or any(type(n) is not int for n in point):
            raise ValueError('LAYOUT_INVALID: arrow coordinates')
        x, y = point
        if not cfg['margin'] <= x < cfg['width'] - cfg['margin'] or not cfg['margin'] <= y < cfg['text_top']:
            raise ValueError('LAYOUT_INVALID: arrow outside canvas or above-text area')
    line = cfg.get('arrow_line')
    if line is not None:
        width = cfg.get('arrow_line_width')
        if type(width) is not int or not 0 < width <= 100 or not isinstance(line, list) or len(line) != 2:
            raise ValueError('LAYOUT_INVALID: arrow line')
        for point in line:
            if not isinstance(point, list) or len(point) != 2 or any(type(n) is not int for n in point):
                raise ValueError('LAYOUT_INVALID: arrow line coordinates')
            x, y = point
            if not cfg['margin'] + width <= x < cfg['width'] - cfg['margin'] - width or not cfg['margin'] + width <= y < cfg['text_top'] - width:
                raise ValueError('LAYOUT_INVALID: arrow line outside safe area')
    return cfg


def load_font(size):
    manifest = json.loads((FONT.parent / 'manifest.json').read_text(encoding='utf-8'))
    for name in ('ZenMaruGothic-Bold.ttf', 'OFL.txt'):
        if hashlib.sha256((FONT.parent / name).read_bytes()).hexdigest() != manifest['sha256'][name]:
            raise ValueError('FONT_INTEGRITY: ' + name)
    with TTFont(FONT) as font:
        if font['OS/2'].usWeightClass != 700 or font['name'].getDebugName(1) != 'Zen Maru Gothic':
            raise ValueError('FONT_METADATA: expected Zen Maru Gothic Bold 700')
        cmap = font.getBestCmap()
    # v2.2 places each upright glyph by its ink bounding box. BASIC avoids
    # an unnecessary platform-specific RAQM dependency for this supported set.
    return ImageFont.truetype(str(FONT), size, layout_engine=ImageFont.Layout.BASIC), cmap


def positions(columns, cfg):
    # First CSV column is the rightmost; every glyph uses the same fixed pitch.
    return [(cfg['center_x'] + ((len(columns) - 1) / 2 - i) * cfg['column_pitch'],
             cfg['text_top'] + j * (cfg['font_size'] + cfg['character_gap']), char)
            for i, column in enumerate(columns) for j, char in enumerate(column)]


def render(columns, cfg, font, cmap):
    for column in columns:
        if len(column) > cfg['max_chars']:
            raise Review('TOO_LONG: specify columns with /; no automatic wrapping or shrinking')
        for char in column:
            if ord(char) not in cmap:
                raise ValueError('MISSING_GLYPH')
            if (unicodedata.category(char)[0] in 'MPS' or char.isspace() or ord(char) < 128
                    or char in 'ぁぃぅぇぉっゃゅょゎゕゖァィゥェォッャュョヮヵヶー'):
                raise Review('TYPOGRAPHY_REVIEW: punctuation, small kana, symbols or nonstandard text')
    image = Image.new('RGBA', (cfg['width'], cfg['height']), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)
    for x, y, char in positions(columns, cfg):
        bbox = draw.textbbox((0, 0), char, font=font)
        width, height = bbox[2] - bbox[0], bbox[3] - bbox[1]
        left, top, right, bottom = x - width / 2, y, x + width / 2, y + height
        m = cfg['margin']
        if left < m or top < cfg['text_top'] or right > cfg['width'] - m or bottom > cfg['height'] - m:
            raise Review('OUT_OF_BOUNDS: adjust explicit columns or review approved layout')
        draw.text((left - bbox[0], y - bbox[1]), char, font=font, fill=(0, 0, 0, 255))
    if cfg.get('arrow_line'):
        draw.line([tuple(p) for p in cfg['arrow_line']], fill=(0, 0, 0, 255), width=cfg['arrow_line_width'])
    draw.polygon([tuple(p) for p in cfg['arrow_points']], fill=(0, 0, 0, 255))
    return image


def run(catalog, layout, output):
    output = Path(output)
    # Never silently replace old results or mix stale images with this report.
    output.mkdir(parents=True, exist_ok=True)
    if any(output.iterdir()):
        raise ValueError('OUTPUT_NOT_EMPTY: choose a new output directory')
    results = []
    try:
        rows = read_catalog(catalog)
    except (OSError, UnicodeError, csv.Error, ValueError):
        rows = []
        results.append(dict(row=0, design_id='', status='ERROR', reason='CSV_UNREADABLE_OR_INVALID', columns=0, file=''))
    counts = Counter(row[0] for row in rows if len(row) == 2)
    duplicates = {key for key, count in counts.items() if count > 1}
    cfg = font = cmap = None
    setup_status, setup_reason = '', ''
    try:
        cfg = load_layout(layout)
        font, cmap = load_font(cfg['font_size'])
    except Review as exc:
        setup_status, setup_reason = 'REVIEW', str(exc)
    except Exception:
        setup_status, setup_reason = 'ERROR', 'RENDER_SETUP_INVALID: check layout, font and license'
    for index, row in enumerate(rows, 2):
        result = dict(row=index, design_id=row[0] if row and re.fullmatch(r'IC-[0-9]{4,12}', row[0]) else '',
                      status='ERROR', reason='', columns=0, file='')
        try:
            columns = validate_row(row, duplicates)
            result['columns'] = len(columns)
            if setup_status:
                result.update(status=setup_status, reason=setup_reason)
            else:
                image = render(columns, cfg, font, cmap)
                filename = row[0] + '.png'
                image.save(output / filename)
                result.update(status='OK', reason='', file=filename)
        except Review as exc:
            result.update(status='REVIEW', reason=str(exc))
        except ValueError as exc:
            result.update(status='ERROR', reason=str(exc))
        except Exception:
            result.update(status='ERROR', reason='RENDER_FAILED')
        results.append(result)
    with (output / 'report.csv').open('w', encoding='utf-8-sig', newline='') as stream:
        writer = csv.DictWriter(stream, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(results)
    return 1 if any(r['status'] == 'ERROR' for r in results) else 2 if any(r['status'] == 'REVIEW' for r in results) else 0


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--csv', type=Path, default=ROOT / 'catalog/products.csv')
    parser.add_argument('--layout', type=Path, default=ROOT / 'automation/render-layout.json')
    parser.add_argument('--output', type=Path, default=ROOT / 'output/render-images')
    args = parser.parse_args()
    try:
        return run(args.csv, args.layout, args.output)
    except (OSError, ValueError):
        print('Cannot write results. Use a new, writable output directory.')
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
