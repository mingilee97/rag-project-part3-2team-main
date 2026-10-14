"""게시 대상 파일과 현재 브랜치의 전체 Git blob 이력을 값 출력 없이 검사한다."""
from pathlib import Path
import re
import subprocess

ROOT = Path(__file__).resolve().parents[2]
PATTERNS = {
    'credential': re.compile(rb'(?:sk-[A-Za-z0-9_-]{20,}|gh[pousr]_[A-Za-z0-9]{20,}|github_pat_[A-Za-z0-9_]{20,}|AKIA[0-9A-Z]{16})'),
    'private_key': re.compile(rb'-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----'),
    'personal_path': re.compile(rb'(?:[A-Za-z]:[\\/](?:Users|home)[\\/]|/' + rb'home/[^/\s]+/|/' + rb'Users/[^/\s]+/)'),
    'email': re.compile(rb'[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}'),
}


def git(*args):
    return subprocess.check_output(['git', '-C', str(ROOT), *args])


def scan(name, content):
    for kind, pattern in PATTERNS.items():
        if pattern.search(content):
            raise SystemExit(f'공개 검사 실패: {name}, {kind}; 값은 출력하지 않음')


def main():
    paths = set(git('ls-files', '-z', '--cached', '--others', '--exclude-standard').decode().split('\0')) - {''}
    for relative in sorted(paths):
        path = ROOT / relative
        if not path.is_file():
            raise SystemExit(f'공개 검사 실패: 파일 없음 {relative}')
        if path.suffix.lower() in {'.docx', '.ipynb', '.csv', '.sqlite', '.db', '.pem', '.key'}:
            raise SystemExit(f'공개 검사 실패: 허용하지 않은 파일 형식 {relative}')
        if path.suffix.lower() == '.pdf':
            import pymupdf
            with pymupdf.open(path) as doc:
                text = '\n'.join(page.get_text() for page in doc)
                text += '\n' + str(doc.metadata)
                for page in doc:
                    text += '\n' + str(page.get_links())
                scan(relative, text.encode('utf-8'))
        else:
            scan(relative, path.read_bytes())
    blobs = set()
    revisions = git('rev-list', 'HEAD').decode().splitlines()
    for revision in revisions:
        for line in git('ls-tree', '-r', revision).decode().splitlines():
            metadata, _ = line.split('\t', 1)
            _, kind, digest = metadata.split()
            if kind == 'blob':
                blobs.add(digest)
    for digest in blobs:
        scan(f'history blob {digest}', git('cat-file', 'blob', digest))
    print(f'공개 검사 통과: files={len(paths)}, commits={len(revisions)}, unique_history_blobs={len(blobs)}')


if __name__ == '__main__':
    main()
