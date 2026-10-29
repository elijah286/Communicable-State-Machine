import json
import os
from pathlib import Path
import subprocess


workspace = Path(os.environ['GITHUB_WORKSPACE'])
mode = os.environ['MODE']
output = workspace / 'diagnostic-output'
output.mkdir()
tooling = workspace / 'tooling'
changed = subprocess.check_output(
    ['git', '-C', str(workspace / 'head'), 'diff', '--name-only',
     os.environ['BASE_SHA'], os.environ['HEAD_SHA'], '--', '*.vi', '*.ctl'], text=True)
targets = [
    'src/user.lib/_NEVSTOP/Communicable State Machine(CSM)/AdvanceAPI/CSM - Generate User Global Log.vi',
    'src/user.lib/_NEVSTOP/Communicable State Machine(CSM)/Parse State Queue++.vi',
    'src/user.lib/_NEVSTOP/Communicable State Machine(CSM)/_Support/GlobalEvent/GEvt-Generate Complete Log.vi',
]
cases = [changed] if mode == 'recovery-full' else targets
results = []
for index, target in enumerate(cases, 1):
    destination = output / str(index)
    destination.mkdir()
    name = f'vidiff-diagnostic-{index}'
    command = [
        'docker', 'run', '--name', name, '--ulimit', 'core=0',
        '-v', f'{workspace / "head"}:/workspace',
        '-v', f'{workspace / "base"}:/workspace-base',
        '-v', f'{tooling / ".github/labview"}:/ops:ro',
        '-v', f'{tooling / ".github/diagnostics/vidiff"}:/diagnostic:ro',
        '-v', f'{destination}:/out', '-e', f'MODE={mode}',
        '-e', f'CHANGED_FILES={target}', os.environ['IMAGE'], 'bash', '/diagnostic/probe.sh',
    ]
    print(f'Running {mode}: {target}', flush=True)
    with (destination / 'console.log').open('w') as log:
        result = subprocess.run(command, stdout=log, stderr=subprocess.STDOUT)
    print((destination / 'console.log').read_text(), flush=True)
    with (destination / 'container-changes.txt').open('w') as log:
        subprocess.run(['docker', 'diff', name], stdout=log, stderr=subprocess.STDOUT)
    subprocess.run(['docker', 'rm', '-f', name], check=True)
    manifest = destination / 'report/changes.json'
    html = destination / 'report/index.html'
    reports = len(json.loads(manifest.read_text())['files']) if manifest.exists() else int(
        html.exists() and html.stat().st_size > 0)
    results.append({'mode': mode, 'case': index, 'exit': result.returncode,
                    'reports': reports, 'target': target})
(output / 'results.json').write_text(json.dumps(results, indent=2))
print(json.dumps(results, indent=2))
with open(os.environ['GITHUB_STEP_SUMMARY'], 'a') as summary:
    summary.write('```json\n' + json.dumps(results, indent=2) + '\n```\n')
