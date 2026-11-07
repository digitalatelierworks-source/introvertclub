import csv
import hashlib
import json
from pathlib import Path
import tempfile
import unittest

from PIL import Image
import yaml
from automation import render_images as r


def fixture_layout():
    # Synthetic geometry for algorithm tests ONLY; not approved production geometry.
    return dict(verified=True, reference='SYNTHETIC TEST ONLY', width=600, height=900,
                font_size=50, character_gap=8, column_pitch=90, text_top=200,
                center_x=300, margin=20, max_chars=7,
                arrow_points=[[300, 40], [350, 100], [315, 100], [315, 160],
                              [285, 160], [285, 100], [250, 100]])


class RendererTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.cfg = fixture_layout()
        cls.font, cls.cmap = r.load_font(50)

    def batch(self, content, cfg=None, raw=False):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / 'input.csv'
            if raw:
                source.write_bytes(content)
            else:
                source.write_text(content, encoding='utf-8-sig')
            layout = root / 'layout.json'
            layout.write_text(json.dumps(cfg or self.cfg), encoding='utf-8')
            code = r.run(source, layout, root / 'out')
            with (root / 'out/report.csv').open(encoding='utf-8-sig', newline='') as f:
                rows = list(csv.DictReader(f))
            files = sorted(p.name for p in (root / 'out').glob('*.png'))
            return code, rows, files

    def test_1_to_4_columns_and_rtl(self):
        for n in range(1, 5):
            columns = list('友恋話今')[:n]
            positions = r.positions(columns, self.cfg)
            self.assertEqual([p[2] for p in positions], columns)
            self.assertEqual([p[0] for p in positions], sorted([p[0] for p in positions], reverse=True))
            image = r.render(columns, self.cfg, self.font, self.cmap)
            self.assertEqual(image.size, (600, 900))
            self.assertEqual(image.mode, 'RGBA')
            self.assertEqual(image.getpixel((0, 0)), (0, 0, 0, 0))
            self.assertEqual(image.getpixel((300, 70)), (0, 0, 0, 255))
            for x, _, _ in positions:
                self.assertIsNotNone(image.crop((x-30, 200, x+30, 300)).getbbox())
            self.assertIsNone(image.crop((0, 161, 600, 200)).getbbox())
            bbox = image.getbbox()
            self.assertGreaterEqual(bbox[0], 20)
            self.assertLessEqual(bbox[2], 580)

    def test_fixed_pitch(self):
        a = r.positions(['友達募集中です'], self.cfg)
        b = r.positions(['友達募集中です', '恋人'], self.cfg)
        self.assertEqual([p[1] for p in a], [p[1] for p in b[:len(a)]])
        self.assertEqual(a[1][1] - a[0][1], 58)

    def test_no_automatic_split(self):
        cols = r.validate_row(['IC-0001', 'ね'*100], set())
        self.assertEqual(len(cols), 1)
        with self.assertRaises(r.Review):
            r.render(cols, self.cfg, self.font, self.cmap)

    def test_utf8_bom_and_explicit_split(self):
        code, rows, files = self.batch('design_id,message\nIC-0006,話しかけないで/くださいね\n')
        self.assertEqual(code, 0)
        self.assertEqual(rows[0]['columns'], '2')
        self.assertEqual(files, ['IC-0006.png'])

    def test_mixed_results(self):
        code, rows, files = self.batch('design_id,message\nIC-0001,友達\nIC-0002,' + 'ね'*100 + '\nIC-0003,友//達\n')
        self.assertEqual(code, 1)
        self.assertEqual([x['status'] for x in rows], ['OK', 'REVIEW', 'ERROR'])
        self.assertEqual(files, ['IC-0001.png'])

    def test_invalid_rows(self):
        for row in (['../bad', '友'], ['IC-0001', ''], ['IC-0001','友/'],
                    ['IC-0001','友/達/恋/人/募'], ['IC-0001','友\n達'],
                    ['IC-0001',' 友'], ['IC-0001','友','余分']):
            with self.subTest(row=row), self.assertRaises(ValueError):
                r.validate_row(row, set())

    def test_duplicate_ids_reject_all(self):
        _, rows, files = self.batch('design_id,message\nIC-0001,友\nIC-0001,恋\n')
        self.assertEqual([x['status'] for x in rows], ['ERROR','ERROR'])
        self.assertEqual(files, [])

    def test_bad_csv(self):
        for content in (b'design_id,message\n', b'bad,header\na,b\n',
                        b'design_id,message\nIC-0001,"oops', b'\xff\xfe'):
            code, rows, files = self.batch(content, raw=True)
            self.assertEqual(code, 1)
            self.assertEqual(rows[0]['status'], 'ERROR')
            self.assertFalse(files)

    def test_missing_glyph(self):
        with self.assertRaises(ValueError):
            r.render(['\U0010ffff'], self.cfg, self.font, self.cmap)

    def test_special_typography_requires_review(self):
        for text in ['「そう。」', 'ちょっと', 'コーヒー', 'ABC']:
            with self.subTest(text=text), self.assertRaises(r.Review):
                r.render([text], self.cfg, self.font, self.cmap)

    def test_png_roundtrip(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'test.png'
            r.render(['話しかけないで', 'くださいね'], self.cfg, self.font, self.cmap).save(path)
            with Image.open(path) as image:
                self.assertEqual(image.mode, 'RGBA')
                self.assertEqual(image.size, (600, 900))
                self.assertEqual(image.getchannel('A').getextrema(), (0, 255))
                self.assertTrue(all(r == g == b == 0 for r, g, b, a in image.getdata()))

    def test_bad_layout_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'layout.json'
            for override in [dict(font_size=-1), dict(column_pitch=10),
                             dict(arrow_points=[[0,0],[10,10],[20,20]])]:
                path.write_text(json.dumps(dict(self.cfg, **override)))
                with self.assertRaises(ValueError):
                    r.load_layout(path)

    def test_width_overflow(self):
        cfg = dict(self.cfg, center_x=30)
        with self.assertRaises(r.Review):
            r.render(['友','達','恋','人'], cfg, self.font, self.cmap)

    def test_unverified_production(self):
        cfg = json.loads((r.ROOT / 'automation/render-layout.json').read_text())
        cfg['verified'] = False
        code, rows, files = self.batch('design_id,message\nIC-0001,友\n', cfg)
        self.assertEqual(code, 2)
        self.assertEqual(rows[0]['status'], 'REVIEW')
        self.assertFalse(files)

    def test_existing_output_untouched(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / 'keep.png'
            p.write_bytes(b'original')
            with self.assertRaises(ValueError):
                r.run('unused', 'unused', tmp)
            self.assertEqual(p.read_bytes(), b'original')

    def test_workflow_offline_only(self):
        text = (r.ROOT / '.github/workflows/render-images.yml').read_text()
        cfg = yaml.load(text, Loader=yaml.BaseLoader)
        self.assertEqual(list(cfg['on']), ['workflow_dispatch'])
        self.assertEqual(cfg['permissions'], {'contents':'read'})
        self.assertNotIn('secrets.', text)
        self.assertNotIn('suzuri', text.lower())
        self.assertNotIn('git push', text)
        steps = cfg['jobs']['render']['steps']
        upload = [s for s in steps if s.get('uses', '').startswith('actions/upload-artifact@')][0]
        self.assertEqual(upload['if'], 'always()')
        self.assertEqual(upload['with']['path'], 'output/render-images/')

    def test_v22_reference_pixels(self):
        cfg = r.load_layout(r.ROOT / 'automation/render-layout.json')
        font, cmap = r.load_font(cfg['font_size'])
        reference = json.loads((r.ROOT / 'tests/fixtures/v22-reference.json').read_text())
        rows = r.read_catalog(r.ROOT / 'tests/fixtures/v22-products.csv')
        for design_id, message in rows:
            if design_id not in reference['images']:
                continue
            with self.subTest(design_id=design_id):
                image = r.render(message.split('/'), cfg, font, cmap)
                expected = reference['images'][design_id]
                self.assertEqual(image.size, (1706, 2048))
                self.assertEqual(list(image.getbbox()), expected['bbox'])
                self.assertEqual(hashlib.sha256(image.getchannel('A').tobytes()).hexdigest(), expected['alpha_sha256'])

    def test_v22_catalog_results(self):
        cfg = r.load_layout(r.ROOT / 'automation/render-layout.json')
        content = (r.ROOT / 'tests/fixtures/v22-products.csv').read_text(encoding='utf-8-sig')
        code, rows, files = self.batch(content, cfg)
        self.assertEqual(code, 1)  # Intentional invalid fixture, not a test failure.
        self.assertEqual([row['status'] for row in rows], ['OK','OK','OK','OK','REVIEW','OK','ERROR'])
        self.assertEqual(files, ['IC-0001.png','IC-0002.png','IC-0003.png','IC-0004.png','IC-0006.png'])

    def test_v22_seven_eight_character_boundary(self):
        cfg = r.load_layout(r.ROOT / 'automation/render-layout.json')
        font, cmap = r.load_font(cfg['font_size'])
        r.render(['友' * 7], cfg, font, cmap)
        with self.assertRaises(r.Review):
            r.render(['友' * 8], cfg, font, cmap)

    def test_production_catalog_all_ok(self):
        cfg = r.load_layout(r.ROOT / 'automation/render-layout.json')
        content = (r.ROOT / 'catalog/products.csv').read_text(encoding='utf-8-sig')
        code, rows, files = self.batch(content, cfg)
        self.assertEqual(code, 0)
        self.assertTrue(all(row['status'] == 'OK' for row in rows))
        self.assertEqual(len(files), 5)


if __name__ == '__main__':
    unittest.main()
