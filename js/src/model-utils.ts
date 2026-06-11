/* Copyright Mozilla Foundation
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *     http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */

import type {
  Expression,
  Message,
  Pattern,
  PatternMessage,
  SelectMessage
} from './model.ts'

/**
 * Determine if a message would format as an empty string.
 *
 * @param anyVariant - If `true`,
 *   having any of the variants of a `SelectMessage` be empty returns `true`.
 */
export function messageIsEmpty(msg: Message, anyVariant = false): boolean {
  const emptyPattern = (pat: Pattern) => pat.every((el) => el === '')
  if (Array.isArray(msg)) {
    return emptyPattern(msg)
  } else if (msg.msg) {
    return emptyPattern(msg.msg)
  } else {
    const patterns = msg.alt.map((a) => a.pat)
    return anyVariant
      ? patterns.some(emptyPattern)
      : patterns.every(emptyPattern)
  }
}

/**
 * Drop unused declarations, join adjacent literal elements, and drop empty literal elements.
 *
 * Does not modify `msg`.
 * Objects and arrays in returned value are clones of objects in `msg`.
 */
export function normalizeMessage(msg: Message): Message {
  if (Array.isArray(msg)) return normalizePattern(msg, null)

  if (msg.msg) {
    const varRefs = new Set<string>()
    const pat = normalizePattern(msg.msg, varRefs)
    const decl = normalizeDeclarations(msg, varRefs)
    return decl ? { decl, msg: pat } : pat
  }

  const varRefs = new Set<string>(msg.sel)
  const alt = msg.alt.map(({ keys, pat }) => ({
    keys: structuredClone(keys),
    pat: normalizePattern(pat, varRefs)
  }))
  const decl = normalizeDeclarations(msg, varRefs)!
  return { decl, sel: [...msg.sel], alt }
}

function normalizePattern(pat: Pattern, varRefs: Set<string> | null): Pattern {
  const res: Pattern = []
  let next: string = ''
  for (const el of pat) {
    if (typeof el === 'string') {
      next = next ? next + el : el
    } else {
      if (next) {
        res.push(next)
        next = ''
      }
      res.push(structuredClone(el))
      if (varRefs) {
        if (typeof el.$ === 'string') varRefs.add(el.$)
        if (el.opt) {
          for (const optVal of Object.values(el.opt)) {
            if (typeof optVal !== 'string') varRefs.add(optVal.$)
          }
        }
      }
    }
  }
  if (next) res.push(next)
  return res
}

function normalizeDeclarations(
  msg: PatternMessage | SelectMessage,
  varRefs: Set<string>
): Record<string, Expression> | null {
  const declRefs: Record<string, Set<string>> = {}
  for (const [name, decl] of Object.entries(msg.decl)) {
    const refs = new Set<string>()
    if (typeof decl.$ === 'string' && decl.$ !== name) refs.add(decl.$)
    if (decl.opt) {
      for (const optVal of Object.values(decl.opt)) {
        if (typeof optVal !== 'string') refs.add(optVal.$)
      }
    }
    if (refs.size) declRefs[name] = refs
  }

  function* varDependencies(name: string): Iterable<string> {
    const drs = declRefs[name]
    if (drs) {
      delete declRefs[name]
      for (const dr of drs) {
        yield dr
        yield* varDependencies(dr)
      }
    }
  }

  for (const ref of varRefs) {
    for (const dr of varDependencies(ref)) varRefs.add(dr)
  }

  let hasDecl = false
  const decl: Record<string, Expression> = {}
  for (const [name, exp] of Object.entries(msg.decl)) {
    if (varRefs.has(name)) {
      decl[name] = structuredClone(exp)
      hasDecl = true
    }
  }
  return hasDecl ? decl : null
}
