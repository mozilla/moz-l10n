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
  Markup,
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

/**
 * Are the messages `a` and `b` deeply equal?
 *
 * Messages are not normalised for this comparison.
 * All catchall keys are considered equal with each other,
 * and declaration order is ignored.
 */
export function messagesEqual(a: Message, b: Message): boolean {
  if (a === b) return true
  if (Array.isArray(a)) {
    if (Array.isArray(b)) return patternsEqual(a, b)
    if (b.msg && !Object.keys(b.decl).length) return patternsEqual(a, b.msg)
    return false
  }
  if (Array.isArray(b)) {
    if (a.msg && !Object.keys(a.decl).length) return patternsEqual(a.msg, b)
    return false
  }
  if (a.msg) {
    // PatternMessage
    if (!b.msg || !patternsEqual(a.msg, b.msg)) return false
  } else {
    // SelectMessage
    if (b.msg || a.sel.length !== b.sel.length || a.alt.length !== b.alt.length)
      return false
    for (let i = 0; i < a.sel.length; ++i) {
      if (a.sel[i] !== b.sel[i]) return false
    }
    for (let i = 0; i < a.alt.length; ++i) {
      const av = a.alt[i]
      const bv = b.alt[i]
      for (let j = 0; j < av.keys.length; ++j) {
        const ak = av.keys[j]
        const bk = bv.keys[j]
        if (typeof ak === 'string') {
          if (ak !== bk) return false
        } else {
          if (typeof bk === 'string') return false
          // All catchall keys are considered equal with each other
        }
      }
      if (!patternsEqual(av.pat, bv.pat)) return false
    }
  }
  const ad = Object.entries(a.decl)
  if (ad.length !== Object.keys(b.decl).length) return false
  for (const [name, ax] of ad) {
    // Declaration order is ignored
    const bx = b.decl[name]
    if (!bx || !placeholdersEqual(ax, bx)) return false
  }
  return true
}

function patternsEqual(a: Pattern, b: Pattern) {
  if (a.length !== b.length) return false
  for (let i = 0; i < a.length; ++i) {
    const ai = a[i]
    const bi = b[i]
    if (typeof ai === 'string') {
      if (ai !== bi) return false
    } else if (typeof bi === 'string' || !placeholdersEqual(ai, bi)) {
      return false
    }
  }
  return true
}

/** Are the placeholders `a` and `b` deeply equal?  */
function placeholdersEqual(
  a: Expression | Markup,
  b: Expression | Markup
): boolean {
  if (
    a._ !== b._ ||
    a.$ !== b.$ ||
    a.fn !== b.fn ||
    a.open !== b.open ||
    a.close !== b.close ||
    a.elem !== b.elem
  )
    return false

  if (a.opt || b.opt) {
    const ao = a.opt ? Object.entries(a.opt) : []
    const bol = b.opt ? Object.keys(b.opt).length : 0
    if (ao.length !== bol) return false
    for (const [key, av] of ao) {
      const bv = b.opt![key]
      if (typeof av === 'string') {
        if (bv !== av) return false
      } else {
        if (typeof bv !== 'object' || bv.$ !== av.$) return false
      }
    }
  }

  if (a.attr || b.attr) {
    const aa = a.attr ? Object.entries(a.attr) : []
    const bal = b.attr ? Object.keys(b.attr).length : 0
    if (aa.length !== bal) return false
    for (const [key, av] of aa) if (b.attr![key] !== av) return false
  }

  return true
}
