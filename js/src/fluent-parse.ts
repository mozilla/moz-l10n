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

import * as FTL from '@fluent/syntax/esm/ast.js'
import {
  ParseError as FluentError,
  FluentParser
} from '@fluent/syntax/esm/index.js'
import { FluentParserStream } from '@fluent/syntax/esm/stream.js'

import { ParseError } from './errors.ts'
import type {
  CatchallKey,
  Expression,
  Message,
  Pattern,
  Entry
} from './model.ts'

const pluralCategories = new Set(['zero', 'one', 'two', 'few', 'many', 'other'])

/**
 * Parses a string as a Fluent entry.
 *
 * Comments are discarded.
 *
 * May throw a {@link ParseError}.
 */
export function fluentParseEntry(src: string): [string, Entry] {
  let id = ''
  let attrId = ''
  const entry = new FluentParser().parseEntry(src)
  if (entry instanceof FTL.Message || entry instanceof FTL.Term) {
    try {
      id = entry.id.name
      if (entry instanceof FTL.Term) id = '-' + id
      const value = entry.value ? message(entry.value) : null
      const attributes: Record<string, Message> = {}
      for (const attr of entry.attributes) {
        attrId = attr.id.name
        attributes[attrId] = message(attr.value)
      }
      return value
        ? [
            id,
            Object.keys(attributes).length
              ? { '=': value, '+': attributes }
              : { '=': value }
          ]
        : [id, { '+': attributes }]
    } catch (error) {
      if (attrId) id += '.' + attrId
      const pre = id ? `fluent(${id})` : 'fluent'
      const msg =
        error instanceof FluentError
          ? `${error.message} (${error.code})`
          : String(error)
      throw new ParseError(`${pre}: ${msg}`, 0, src.length)
    }
  } else if (entry instanceof FTL.Junk && entry.annotations[0]) {
    const annot = entry.annotations[0]
    const msg = `fluent: ${annot.message} (${annot.code})`
    const span = annot?.span ?? entry.span
    throw new ParseError(msg, span?.start ?? 0, span?.end ?? src.length)
  } else {
    throw new ParseError('fluent: Parse error', 0, src.length)
  }
}

type Key = {
  name: string
  isDefault: boolean
  isNumeric: boolean
}

type SelectorResultRow = {
  msgSel: Expression
  ftlSelectors: FTL.InlineExpression[]
  keys: Key[]
}

function message(ftlPattern: FTL.Pattern): Message {
  const selData = findSelectors(ftlPattern, [])
  const selExpressions = selData.map((row) => row.msgSel)
  const keyLists = selData.map(uniqueKeys)
  let msgVariants: [Key[], Pattern][]
  const varNames = new Set<string>()
  switch (keyLists.length) {
    case 0:
      msgVariants = [[[], []]]
      break
    case 1:
      msgVariants = keyLists[0].map((key) => [[key], []])
      break
    default: {
      // With multiple selectors, for each selector,
      // ensure that a row of keys exists with each of its values in its key column,
      // combined with each value of all other selectors.
      // Effectively this involves a cross product of two vectors.
      // @ts-expect-error TS doesn't support this (valid) reduce variant
      const keyMatrix = keyLists.reduce((res: Key[] | Key[][], selKeys) =>
        res.flatMap((prev) => selKeys.map((key) => [prev, key].flat()))
      ) as Key[][]
      msgVariants = keyMatrix.map((keys) => [keys, []])
    }
  }

  const filter: (Set<Key> | undefined)[] = new Array(selExpressions.length)

  function addPattern(ftlPattern: FTL.Pattern) {
    for (const el of unwrapElements(ftlPattern)) {
      if (el instanceof FTL.SelectExpression) {
        const ftlSel = el.selector
        const { msgSel, ftlSelectors } = selData.find((row) =>
          row.ftlSelectors.includes(ftlSel)
        )!
        const idx = selExpressions.indexOf(msgSel)
        const prevFilt = filter[idx]
        const elVariants = el.variants.map(
          (v) => [variantKey(v).name, v] as const
        )
        const selKeys = new Set(elVariants.map(([name]) => name))
        const keyCandidates = prevFilt ?? keyLists[idx]
        for (const [varKey, variant] of elVariants) {
          // A selector may be used by more than one select expression!
          // `keyCandidates` may have keys that this expression doesn't declare.
          // The default variant applies for those, but only expand it to them if
          // it wraps a further select on this selector narrowing them down again.
          // Otherwise we'd duplicate default variant. CatchAll already covers it!
          const isExpandableDefault =
            variant.default &&
            (prevFilt !== undefined ||
              containsSelector(variant.value, ftlSelectors))
          filter[idx] = new Set(
            Array.from(keyCandidates).filter(
              (key) =>
                key.name === varKey ||
                (isExpandableDefault && !selKeys.has(key.name))
            )
          )
          addPattern(variant.value)
        }
        filter[idx] = prevFilt
      } else {
        for (const [keys, pat] of msgVariants) {
          if (
            filter.every(
              (filt, idx) => filt === undefined || filt.has(keys[idx])
            )
          ) {
            if (el instanceof FTL.TextElement) {
              if (typeof pat.at(-1) === 'string')
                pat[pat.length - 1] += el.value
              else pat.push(el.value)
            } else {
              const expr = expression(el, false)
              if (expr.$) varNames.add(expr.$)
              pat.push(expr)
            }
          }
        }
      }
    }
  }
  addPattern(ftlPattern)

  if (selExpressions.length) {
    const decl: Record<string, Expression> = {}
    const sel: string[] = []
    for (const expr of selExpressions) {
      let name = expr.$
      if (!name || expr.attr?.['fluent-fn']) {
        const stem = name || 'sel'
        let i = 0
        do {
          name = `${stem}_${++i}`
        } while (varNames.has(name))
      }
      decl[name] = expr
      sel.push(name)
      varNames.add(name)
    }

    function message_key(key: Key): string | CatchallKey {
      return key.isDefault ? { '*': key.name } : key.name
    }

    const alt = msgVariants
      .filter((mv) => mv[1].length)
      .map(([keys, pat]) => ({ keys: keys.map(message_key), pat }))
    return { decl, sel, alt }
  } else {
    return msgVariants[0][1]
  }
}

function findSelectors(
  pattern: FTL.Pattern,
  result: SelectorResultRow[]
): SelectorResultRow[] {
  for (const el of pattern.elements) {
    if (
      el instanceof FTL.Placeable &&
      el.expression instanceof FTL.SelectExpression
    ) {
      const ftlSel = el.expression.selector
      const keys = el.expression.variants.map(variantKey)
      const msgSel = selectExpression(ftlSel, keys)
      let foundPrev = false
      for (const row of result) {
        if (exprEqual(row.msgSel, msgSel)) {
          row.ftlSelectors.push(ftlSel)
          row.keys.push(...keys)
          foundPrev = true
        }
      }
      if (!foundPrev) {
        result.push({ msgSel, ftlSelectors: [ftlSel], keys })
      }
      for (const v of el.expression.variants) findSelectors(v.value, result)
    }
  }
  return result
}

function uniqueKeys({ keys }: SelectorResultRow): Key[] {
  // Selects sharing a selector may declare overlapping or differing keys,
  // but each key name maps to one variant and only one may be the catch-all.
  // Deduplicate by name, keeping the outermost default as the catch-all.
  const defaultName = keys.find((key) => key.isDefault)?.name
  const byName = new Map<string, Key>()
  for (const { name, isNumeric } of keys) {
    if (!byName.has(name)) {
      byName.set(name, { name, isNumeric, isDefault: name === defaultName })
    }
  }
  return Array.from(byName.values())
}

/** Check if a pattern contains a nested SelectExpression for a given selector. */
function containsSelector(
  pattern: FTL.Pattern,
  selectorExpressions: FTL.InlineExpression[]
): boolean {
  for (const el of unwrapElements(pattern)) {
    if (!(el instanceof FTL.SelectExpression)) continue
    if (selectorExpressions.includes(el.selector)) return true
    for (const v of el.variants) {
      if (containsSelector(v.value, selectorExpressions)) return true
    }
  }
  return false
}

/** Iterate over pattern elements, unwrapping Placeable expressions. */
function* unwrapElements(
  pattern: FTL.Pattern
): Generator<
  FTL.TextElement | FTL.InlineExpression | FTL.SelectExpression,
  void
> {
  for (const element of pattern.elements) {
    let el:
      | FTL.TextElement
      | FTL.Placeable
      | FTL.InlineExpression
      | FTL.SelectExpression = element
    while (el instanceof FTL.Placeable) el = el.expression
    yield el
  }
}

const exprEqual = (a: Expression, b: Expression) =>
  a.$ === b.$ &&
  a._ === b._ &&
  a.fn === b.fn &&
  (a.opt === b.opt || JSON.stringify(a.opt) === JSON.stringify(b.opt))

function variantKey(v: FTL.Variant): Key {
  if (v.key instanceof FTL.Identifier) {
    return { name: v.key.name, isDefault: v.default, isNumeric: false }
  } else {
    return { name: v.key.value, isDefault: v.default, isNumeric: true }
  }
}

function selectExpression(
  ftlSel: FTL.InlineExpression,
  keys: Key[]
): Expression {
  if (ftlSel instanceof FTL.VariableReference) {
    const fn = keys.every((k) => k.isNumeric || pluralCategories.has(k.name))
      ? 'number'
      : 'string'
    return { $: ftlSel.id.name, fn }
  } else if (ftlSel instanceof FTL.StringLiteral) {
    return { _: ftlSel.value, fn: 'string' }
  } else {
    return expression(ftlSel, true)
  }
}

/**
 * Parses a string as a Fluent pattern, without any internal selectors.
 *
 * All whitespace outside placeables is considered significant.
 */
export function fluentParsePattern(
  src: string,
  onError?: (error: ParseError) => void
): Pattern {
  onError ??= (error) => {
    throw error
  }
  const pattern: Pattern = []
  const ps = new FluentParserStream(src)
  let ch
  try {
    while ((ch = ps.currentChar())) {
      switch (ch) {
        case '{': {
          ps.next()
          ps.skipBlank()
          const fe = new FluentParser().getInlineExpression(ps)
          const expr = expression(fe, false)
          ps.skipBlank()
          if (ps.currentChar() === '-' && ps.peek() === '>') {
            // Not supporting selectors within patterns
            throw new FluentError('E0028')
          }
          ps.expectChar('}')
          pattern.push(expr)
          break
        }
        case '}':
          throw new FluentError('E0027')
        default: {
          let buffer = ''
          let ch
          while ((ch = ps.currentChar())) {
            if (ch === '{' || ch === '}') break
            buffer += ch
            ps.next()
          }
          pattern.push(buffer)
        }
      }
    }
  } catch (error) {
    const msg =
      error instanceof FluentError
        ? `fluent: ${error.message} (${error.code})`
        : `fluent: ${error}`
    onError(new ParseError(msg, ps.index, src.length))
    if (ps.index < src.length) pattern.push(src.substring(ps.index))
  }
  return pattern
}

function expression(
  fe: FTL.InlineExpression | FTL.Placeable,
  isSelector: boolean
): Expression {
  if (fe instanceof FTL.NumberLiteral) return { _: fe.value, fn: 'number' }
  if (fe instanceof FTL.StringLiteral) return { _: fe.parse().value }
  if (fe instanceof FTL.VariableReference) return { $: fe.id.name }
  if (fe instanceof FTL.MessageReference) {
    let name = fe.id.name
    if (fe.attribute) name += '.' + fe.attribute.name
    return { _: name, fn: 'message' }
  }
  if (fe instanceof FTL.TermReference) {
    let name = '-' + fe.id.name
    if (fe.attribute) {
      if (isSelector) name += '.' + fe.attribute.name
      else throw new FluentError('E0019')
    }
    const expr: Expression = { _: name, fn: 'message' }
    if (fe.arguments?.named.length) {
      expr.opt = Object.create(null) as Record<string, string>
      for (const arg of fe.arguments.named) {
        expr.opt[arg.name.name] = arg.value.value
      }
    }
    return expr
  }
  if (fe instanceof FTL.FunctionReference) {
    const ftlName = fe.id.name
    const name = ftlName.toLowerCase()
    const arg = fe.arguments.positional[0]
    let expr: Expression
    if (arg instanceof FTL.BaseLiteral) {
      expr = { _: arg.value, fn: name }
    } else if (arg instanceof FTL.VariableReference) {
      expr = { $: arg.id.name, fn: name }
    } else {
      expr = { fn: name }
    }
    if (fe.arguments?.named.length) {
      expr.opt = Object.create(null) as Record<string, string>
      for (const arg of fe.arguments.named) {
        expr.opt[arg.name.name] = arg.value.value
      }
    }
    expr.attr = { 'fluent-fn': ftlName }
    return expr
  }
  throw new FluentError('E0028')
}
