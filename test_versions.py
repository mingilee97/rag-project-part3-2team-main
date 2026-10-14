"""포함된 원본·네 실제 엔트리포인트·Main 독립 복사본을 오프라인으로 검사한다."""
import ast
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import unittest

from version_runtime import verify

ROOT=Path(__file__).resolve().parent

class VersionsTest(unittest.TestCase):
    def test_fixed_source_hashes_and_ast(self):
        for version in ('v1','v2','v3','v4'):
            provenance=verify(version)
            folder=ROOT/f'Version_{version[1:]}'
            for record in provenance['files']:
                path=folder/Path(record['module']).name
                definitions={n.name:n for n in ast.parse(path.read_text(encoding='utf-8')).body if isinstance(n,(ast.FunctionDef,ast.ClassDef))}
                for original in record.get('source_definitions',[]):
                    digest=hashlib.sha256(ast.dump(definitions[original['name']],include_attributes=False).encode()).hexdigest()
                    self.assertEqual(digest,original['ast_sha256'])
        folder=ROOT/'Version_3/components'
        record=json.loads((folder/'provenance.json').read_text(encoding='utf-8'))
        for name,digest in record['files'].items():
            self.assertEqual(hashlib.sha256((folder/name).read_bytes().replace(b'\r\n',b'\n')).hexdigest(),digest)
    def test_four_real_entrypoints(self):
        for i in range(1,5):
            result=subprocess.check_output([sys.executable,'-B',str(ROOT/f'Version_{i}/run.py'),'--smoke'],cwd=ROOT,text=True,encoding='utf-8',env={**__import__('os').environ,'PYTHONUTF8':'1'})
            record=json.loads(result.strip().splitlines()[-1])
            self.assertEqual(record['status'],'passed')
            self.assertEqual(record['api_calls'],0)
            self.assertTrue(record['real_chunking'])
            self.assertTrue(record['real_bm25_rrf'])
    def test_main_is_independent_identical_copy(self):
        record=json.loads((ROOT/'baseline-main-snapshot.json').read_text(encoding='utf-8'))
        self.assertEqual(record['file_count'],35)
        for item in record['files']:
            base=ROOT/'Baseline'/item['file']; main=ROOT/'Main'/item['file']
            self.assertEqual(base.read_bytes(),main.read_bytes())
            self.assertFalse(base.samefile(main))
            self.assertFalse(main.is_symlink())

if __name__=='__main__': unittest.main()
