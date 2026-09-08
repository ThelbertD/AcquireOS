/**
 * Locate a usable Python 3.11+ interpreter.
 *
 * `python` is not a reliable name on Windows: the Microsoft Store ships an alias stub at
 * %LOCALAPPDATA%\Microsoft\WindowsApps\python.exe that prints "Python was not found" and exits
 * non-zero, and it usually sits ahead of a real install on PATH. So candidates are probed by
 * actually running them, not by checking whether the name resolves.
 */

import { execFileSync } from 'node:child_process'
import { existsSync, readdirSync } from 'node:fs'
import { join } from 'node:path'
import { homedir, platform } from 'node:os'

const MIN = [3, 11]

function versionOf(cmd, args = []) {
  try {
    const out = execFileSync(cmd, [...args, '--version'], {
      encoding: 'utf8',
      stdio: ['ignore', 'pipe', 'pipe'],
      timeout: 8000,
    })
    const m = out.match(/Python (\d+)\.(\d+)\.(\d+)/)
    if (!m) return null
    return [Number(m[1]), Number(m[2]), Number(m[3])]
  } catch {
    return null
  }
}

function goodEnough(v) {
  if (!v) return false
  return v[0] > MIN[0] || (v[0] === MIN[0] && v[1] >= MIN[1])
}

function candidates() {
  const list = []

  // The Windows launcher is the most reliable when it exists.
  if (platform() === 'win32') {
    list.push({ cmd: 'py', args: ['-3'] })
  }
  list.push({ cmd: 'python3', args: [] })
  list.push({ cmd: 'python', args: [] })

  // Common per-user install locations, checked directly. These beat PATH on Windows because
  // the Store stub often shadows them.
  if (platform() === 'win32') {
    const base = join(homedir(), 'AppData', 'Local', 'Programs', 'Python')
    if (existsSync(base)) {
      let dirs = []
      try {
        dirs = readdirSync(base).filter((d) => d.startsWith('Python'))
      } catch {
        dirs = []
      }
      // Highest version first.
      dirs.sort().reverse()
      for (const d of dirs) {
        const exe = join(base, d, 'python.exe')
        if (existsSync(exe)) list.push({ cmd: exe, args: [] })
      }
    }
  }

  return list
}

export function findPython() {
  const tried = []
  for (const c of candidates()) {
    const v = versionOf(c.cmd, c.args)
    tried.push(`${c.cmd} ${c.args.join(' ')}`.trim() + (v ? ` -> ${v.join('.')}` : ' -> not found'))
    if (goodEnough(v)) return { ...c, version: v.join('.') }
  }
  return { cmd: null, args: [], version: null, tried }
}

export function requirePython() {
  const found = findPython()
  if (found.cmd) return found

  console.error(
    [
      '',
      'Could not find Python 3.11 or later.',
      '',
      'Tried:',
      ...found.tried.map((t) => `  ${t}`),
      '',
      platform() === 'win32'
        ? [
            'On Windows, `python` often resolves to the Microsoft Store stub, which is not a',
            'real interpreter. Install Python and make sure "Add to PATH" is ticked:',
            '',
            '  winget install Python.Python.3.13',
            '',
            'Then open a NEW terminal so the updated PATH is picked up.',
          ].join('\n')
        : 'Install Python 3.11 or later and make sure it is on PATH.',
      '',
    ].join('\n'),
  )
  process.exit(1)
}
