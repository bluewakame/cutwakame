import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import aicut


class MacTests(unittest.TestCase):
    def test_bundled_tools_without_path(self):
        with tempfile.TemporaryDirectory() as directory:
            tool = Path(directory) / 'bin' / 'ffmpeg'
            tool.parent.mkdir()
            tool.touch()
            with patch.object(sys, '_MEIPASS', directory, create=True), patch.dict(os.environ, {'PATH': ''}):
                self.assertEqual(aicut.binary('ffmpeg'), str(tool))

    @unittest.skipUnless(sys.platform == 'darwin', 'macOS fonts')
    def test_japanese_font(self):
        from PIL import ImageFont
        font = ImageFont.truetype(str(aicut.title_font()), 52)
        self.assertGreater(font.getlength('カットワカメ'), 100)

    def test_render_and_mcp(self):
        with tempfile.TemporaryDirectory(prefix='カットワカメ test ') as directory:
            root = Path(directory)
            video = root / '素材.mp4'
            subprocess.run([aicut.binary('ffmpeg'), '-v', 'error', '-f', 'lavfi', '-i', 'color=c=blue:s=320x240:d=1', '-f', 'lavfi', '-i', 'sine=frequency=440:duration=1', '-c:v', 'libx264', '-c:a', 'aac', str(video)], check=True)
            silent = root / 'silent.mp4'
            subprocess.run([aicut.binary('ffmpeg'), '-v', 'error', '-i', str(video), '-an', '-c:v', 'copy', str(silent)], check=True)
            project = aicut.Project(root / 'test.aicut.json')
            clip = project.add(video)
            project.trim(clip['id'], .1, .9)
            project.split(clip['id'], .5)
            project.add(silent, end=.4)
            project.add_title('日本語テスト', 0, 1)
            project.set_export(320, 240, 30, 25)
            output = root / '完成.mp4'
            project.export(output)
            self.assertAlmostEqual(aicut.probe(output)[1], 1.2, delta=.15)
            result = subprocess.run([sys.executable, str(Path(aicut.__file__)), '--mcp', '--project', str(project.path)], input=json.dumps({'jsonrpc':'2.0','id':1,'method':'tools/call','params':{'name':'get_project','arguments':{}}})+'\n', text=True, capture_output=True, check=True)
            response = json.loads(result.stdout)
            self.assertEqual(len(json.loads(response['result']['content'][0]['text'])['clips']), 3)


if __name__ == '__main__':
    unittest.main()
