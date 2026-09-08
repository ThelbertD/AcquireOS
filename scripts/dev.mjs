/**
 * One command to run the whole thing: `npm run dev`.
 *
 * Vercel runs the Python functions in api/ for you in production. Nothing runs them locally, so
 * development needs two processes — the Python handlers and the Next.js dev server, which
 * proxies /api/* to them (see next.config.mjs). This starts both, prefixes their output, and
 * makes sure Ctrl-C stops both rather than orphaning one.
 */

import { spawn } from 'node:child_process'
import { fileURLToPath } from 'node:url'
import { dirname, join } from 'node:path'
import { requirePython } from './find-python.mjs'

const ROOT = join(dirname(fileURLToPath(import.meta.url)), '..')
const API_PORT = process.env.API_PORT || '8787'
const WEB_PORT = process.env.PORT || '3000'

const python = requirePython()

const C = {
  dim: '\x1b[2m',
  reset: '\x1b[0m',
  api: '\x1b[36m', // cyan
  web: '\x1b[35m', // magenta
  ok: '\x1b[32m',
  bad: '\x1b[31m',
}

function prefix(name, color) {
  const tag = `${color}${name.padEnd(4)}${C.reset} ${C.dim}|${C.reset} `
  return (chunk) => {
    const text = chunk.toString()
    for (const line of text.split(/\r?\n/)) {
      if (line.trim()) process.stdout.write(tag + line + '\n')
    }
  }
}

const children = []
let shuttingDown = false

function start(name, color, cmd, args, opts = {}) {
  const child = spawn(cmd, args, {
    cwd: ROOT,
    shell: false,
    stdio: ['ignore', 'pipe', 'pipe'],
    ...opts,
  })
  child.stdout.on('data', prefix(name, color))
  child.stderr.on('data', prefix(name, color))
  child.on('exit', (code) => {
    if (shuttingDown) return
    console.log(
      `\n${C.bad}${name} exited with code ${code}.${C.reset} Stopping everything.\n`,
    )
    shutdown(code ?? 1)
  })
  child.on('error', (err) => {
    console.error(`${C.bad}${name} failed to start:${C.reset} ${err.message}`)
    shutdown(1)
  })
  children.push(child)
  return child
}

function shutdown(code = 0) {
  if (shuttingDown) return
  shuttingDown = true
  for (const child of children) {
    if (!child.killed) {
      try {
        child.kill('SIGTERM')
      } catch {
        /* already gone */
      }
    }
  }
  setTimeout(() => process.exit(code), 300)
}

process.on('SIGINT', () => {
  console.log(`\n${C.dim}stopping…${C.reset}`)
  shutdown(0)
})
process.on('SIGTERM', () => shutdown(0))

console.log(
  [
    '',
    `  ${C.ok}AcquireOS${C.reset}`,
    `  ${C.dim}python  ${python.cmd} (${python.version})${C.reset}`,
    `  ${C.dim}api     http://127.0.0.1:${API_PORT}${C.reset}`,
    `  ${C.dim}web     http://localhost:${WEB_PORT}${C.reset}`,
    '',
    `  ${C.dim}Ctrl-C stops both.${C.reset}`,
    '',
  ].join('\n'),
)

start('api', C.api, python.cmd, [...python.args, join('scripts', 'dev_api.py'), '--port', API_PORT])
start('web', C.web, process.platform === 'win32' ? 'npx.cmd' : 'npx', [
  'next',
  'dev',
  '--port',
  WEB_PORT,
])
