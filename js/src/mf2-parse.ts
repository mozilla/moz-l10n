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

import {
  Attributes as MF2Attributes,
  Expression as MF2Expression,
  Markup as MF2Markup,
  Message as MF2Message,
  Options as MF2Options,
  MessageSyntaxError,
  parseMessage
} from 'messageformat'
import { ParseError } from './errors.ts'
import type { Expression, Pattern } from './model.ts'

export function mf2ParsePattern(
  src: string,
  onError: (error: ParseError) => void
): Pattern {
  let msg: MF2Message
  try {
    msg = parseMessage(`{{${src}}}`)
  } catch (error) {
    if (error instanceof MessageSyntaxError) {
      const err = `mf2: ${error.message}`
      onError(new ParseError(err, error.start - 2, error.end - 2))
    } else {
      onError(new ParseError(`mf2: ${error}`, 0, src.length))
    }
    return []
  }
  if (msg.type !== 'message' || msg.declarations.length) {
    onError(new ParseError(`mf2: Parse error`, 0, src.length))
    return []
  }
  return msg.pattern.map(patternPart)
}

function patternPart(part: string | MF2Expression | MF2Markup) {
  if (typeof part === 'string') return part
  if (part.type === 'expression') {
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
  } else {
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
}

function options(opt: MF2Options | undefined) {
  if (!opt?.size) return undefined
  const res: Record<string, string | { $: string }> = Object.create(null)
  for (const [name, value] of opt.entries()) {
    res[name] = value.type === 'literal' ? value.value : { $: value.name }
  }
  return res
}

function attributes(attr: MF2Attributes | undefined) {
  if (!attr?.size) return undefined
  const res: Record<string, string | true> = Object.create(null)
  for (const [name, value] of attr.entries()) {
    res[name] = value === true ? true : value.value
  }
  return res
}
