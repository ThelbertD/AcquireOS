/** Run only the Python API handlers. `npm run api` */

import { spawn } from 'node:child_process'
import { fileURLToPath } from 'node:url'
import { dirname, join } from 'node:path'
import { requirePython } from './find-python.mjs'

const ROOT = join(dirname(fileURLToPath(import.meta.url)), '..')
const python = requirePython()

const child = spawn(
  python.cmd,
  [...python.args, join('scripts', 'dev_api.py'), '--port', process.env.API_PORT || '8787'],
  { cwd: ROOT, stdio: 'inherit' },
)

child.on('exit', (code) => process.exit(code ?? 0))
