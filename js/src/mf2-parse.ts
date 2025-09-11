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

import { MessageSyntaxError, Model, parseMessage } from 'messageformat'
import { ParseError } from './errors.ts'
import type { Expression, Markup, Message, Pattern } from './model.ts'

export function mf2ParseMessage(src: string): Message {
  let msg: Model.Message
  try {
    msg = parseMessage(src)
  } catch (error) {
    if (error instanceof MessageSyntaxError) {
      const err = `mf2: ${error.message}`
      throw new ParseError(err, error.start, error.end)
    } else {
      throw new ParseError(`mf2: ${error}`, 0, src.length)
    }
  }

  const decl = msg.declarations.length
    ? Object.fromEntries(
        msg.declarations.map((d) => [d.name, expression(d.value)])
      )
    : null
  if (msg.type === 'message') {
    const pattern = msg.pattern.map(patternPart)
    return decl ? { decl, msg: pattern } : pattern
  } else {
    const sel = msg.selectors.map((s) => s.name)
    const alt = msg.variants.map((v) => {
      const keys = v.keys.map((k) =>
        k.type === 'literal' ? k.value : { '*': k.value ?? '' }
      )
      return { keys, pat: v.value.map(patternPart) }
    })
    return { decl: decl!, sel, alt }
  }
}

/**
 * Will wrap the `src` with {{...}} before parsing.
 */
export function mf2ParsePattern(src: string): Pattern {
  let msg: Model.Message
  try {
    msg = parseMessage(`{{${src}}}`)
  } catch (error) {
    if (error instanceof MessageSyntaxError) {
      const err = `mf2: ${error.message}`
      throw new ParseError(err, error.start - 2, error.end - 2)
    } else {
      throw new ParseError(`mf2: ${error}`, 0, src.length)
    }
  }
  if (msg.type !== 'message' || msg.declarations.length) {
    throw new ParseError(`mf2: Parse error`, 0, src.length)
  }
  return msg.pattern.map(patternPart)
}

function patternPart(part: string | Model.Expression | Model.Markup) {
  if (typeof part === 'string') return part
  return part.type === 'expression' ? expression(part) : markup(part)
}

function expression(part: Model.Expression): Expression {
  const expr = {} as Expression
  if (part.arg) {
    if (part.arg.type === 'literal') expr._ = part.arg.value
    else expr.$ = part.arg.name
  }
  if (part.functionRef) {
    expr.fn = part.functionRef.name
    expr.opt = options(part.functionRef.options)
  }
  expr.attr = attributes(part.attributes)
  return expr
}

function markup(part: Model.Markup): Markup {
  const opt = options(part.options)
  const attr = attributes(part.attributes)
  switch (part.kind) {
    case 'open':
      return { open: part.name, opt, attr }
    case 'close':
      return { close: part.name, opt, attr }
    default:
      return { elem: part.name, opt, attr }
  }
}

function options(opt: Model.Options | undefined) {
  const entries = opt ? Object.entries(opt) : null
  if (!entries?.length) return undefined
  const res: Record<string, string | { $: string }> = Object.create(null)
  for (const [name, value] of entries) {
    res[name] = value.type === 'literal' ? value.value : { $: value.name }
  }
  return res
}

function attributes(attr: Model.Attributes | undefined) {
  const entries = attr ? Object.entries(attr) : null
  if (!entries?.length) return undefined
  const res: Record<string, string | true> = Object.create(null)
  for (const [name, value] of entries) {
    res[name] = value === true ? true : value.value
  }
  return res
}
