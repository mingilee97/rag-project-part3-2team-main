// 공개한 원본 TS에서 순수 함수만 브라우저 모듈로 변환한다. npm 설치는 실행하지 않는다.
import fs from 'node:fs';
import path from 'node:path';
import { createRequire } from 'node:module';
import { fileURLToPath } from 'node:url';
const require = createRequire(import.meta.url);
const root = path.dirname(fileURLToPath(import.meta.url));
const compilerPath = process.argv[2];
if (!compilerPath) throw new Error('설치된 TypeScript의 typescript.js 경로를 인자로 지정하세요');
const ts = require(path.resolve(compilerPath));
for (const version of ['calendar-unified-20261008', 'roadmap-readable-20261008']) {
  const destination = path.join(root, 'example', 'modules', version);
  fs.mkdirSync(destination, { recursive: true });
  for (const file of ['calendarDate', 'processRoadmapLayout']) {
    const source = fs.readFileSync(path.join(root, 'versions', version, 'components', file + '.ts'), 'utf8');
    const tree = ts.createSourceFile(file + '.ts', source, ts.ScriptTarget.Latest, true);
    const nodes = tree.statements.filter(node => !ts.isImportDeclaration(node) &&
      !(ts.isFunctionDeclaration(node) && node.name?.text === 'useSeoulToday'));
    const subset = ts.factory.updateSourceFile(tree, nodes);
    const printed = ts.createPrinter().printFile(subset);
    const compiled = ts.transpileModule(printed, { compilerOptions: {
      target: ts.ScriptTarget.ES2022, module: ts.ModuleKind.ES2022, newLine: ts.NewLineKind.LineFeed,
    }}).outputText;
    fs.writeFileSync(path.join(destination, file + '.mjs'), '// 원본 순수 함수에서 생성. React hook 제외. dashboard/build-example.mjs 참조.\n' + compiled);
  }
}
console.log('두 UI 버전의 순수 함수 모듈을 생성했습니다.');
