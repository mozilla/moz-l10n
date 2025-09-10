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

import { ERROR_RESULT, SerializeError } from './errors.ts'
import type {
  CatchallKey,
  Entry,
  Expression,
  Markup,
  Message,
  Pattern,
  SelectMessage
} from './model.ts'

export function fluentSerializeEntry(id: string, entry: Entry): string {
  const isTerm = id.startsWith('-')
  if (!isIdentifier(isTerm ? id.substring(1) : id))
    throw new SerializeError(`Unsupported message identifier: ${id}`)
  let str = `${id} =`
  const msgStr = fluentSerializeMessage(entry['='])
  if (msgStr) {
    str += msgStr.includes('\n')
      ? '\n' + msgStr.replace(/^/gm, '    ')
      : ' ' + msgStr
  } else if (isTerm || !entry['+']) {
    str += ' { "" }'
  }
  str += '\n'
  if (entry['+']) {
    for (const [name, value] of Object.entries(entry['+'])) {
      str += `    .${name} =`
      const attrStr = fluentSerializeMessage(value) || '{ "" }'
      str += attrStr.includes('\n')
        ? `\n${attrStr.replace(/^/gm, '        ')}\n`
        : ` ${attrStr}\n`
    }
  }
  return str
}

function fluentSerializeMessage(message: Message | undefined): string {
  const onError = (error: SerializeError) => {
    throw error
  }
  if (!message) return ''
  if (Array.isArray(message)) return fluentSerializePattern(message, onError)
  if (message.msg) return fluentSerializePattern(message.msg, onError)

  // It gets a bit complicated for SelectMessage. We'll be modifying this list,
  // building select expressions for each selector starting from the last one
  // until this list has only one entry `[[], pattern]`.
  //
  // We rely on the variants being in order, so that a variant with N keys
  // will be next to all other variants for which the first N-1 keys are equal.
  const variants = message.alt.map(
    (v) =>
      [[...v.keys], [fluentSerializePattern(v.pat, onError)]] satisfies [
        unknown[],
        string[]
      ]
  )

  const other = fallbackName(message)
  const keys0 = variants[0][0]
  while (keys0.length) {
    const selName = message.sel[keys0.length - 1]
    const selExpr = message.decl[selName]
    const selector =
      isIdentifier(selExpr.$) &&
      !selExpr.opt &&
      (selExpr.fn === 'number' || selExpr.fn === 'string')
        ? '$' + selExpr.$
        : expression(selExpr, true)
    let baseKeys = ''
    let selPattern: string[] | null = null
    let i = 0
    while (i < variants.length) {
      const [keys, pattern] = variants[i]
      const key = keys.pop()! // Ultimately modifies keys0
      const jsonKeys = JSON.stringify(keys)
      const varBody = variant(key, other, pattern)
      if (selPattern && jsonKeys == baseKeys) {
        selPattern.push(varBody)
        variants.splice(i, 1)
      } else {
        if (selPattern) selPattern.push('}')
        baseKeys = jsonKeys
        selPattern = pattern //ftl.SelectExpression(selector.clone(), [ftl_variant])
        selPattern.splice(0, selPattern.length, `{ ${selector} ->\n${varBody}`)
        i += 1
      }
    }
    if (selPattern) selPattern.push('}')
  }
  if (variants.length !== 1)
    throw new SerializeError(
      `Error resolving select message variants (n=${variants.length})`
    )
  return variants[0][1].join('')
}

function fallbackName(msg: SelectMessage): string {
  // Try `other`, `other1`, `other2`, ... until a free one is found.
  const root = 'other'
  let key = root
  let i = 0
  const keys = msg.alt.flatMap((v) =>
    v.keys.map((k) => (typeof k === 'string' ? k : k['*']))
  )
  while (keys.includes(key)) {
    i += 1
    key = `${root}${i}`
  }
  return key
}

function variant(
  key: string | CatchallKey,
  other: string,
  pattern: string[]
): string {
  const k = typeof key === 'string' ? key : key['*'] || other
  if (isNaN(Number(k)) && !/^[a-zA-Z][\w-]*$/.test(k)) {
    throw new SerializeError(`Unsupported variant key: ${k}`)
  }
  const d = typeof key === 'string' ? ' ' : '*'
  const pre = `   ${d}[${k}]`
  const value = pattern.join('').trimEnd() || '{ "" }'
  return value.includes('\n')
    ? `${pre}\n${value.replace(/^/gm, '        ')}\n`
    : `${pre} ${value}\n`
}

export function fluentSerializePattern(
  pattern: Pattern,
  onError: (error: SerializeError) => void
): string {
  let str = ''
  for (const part of pattern) {
    if (typeof part === 'string') {
      str += part
        .replaceAll('\\', '\\\\')
        .replaceAll('{', '\\u007b')
        .replaceAll('}', '\\u007d')
    } else {
      try {
        str += `{ ${expression(part, false)} }`
      } catch (error) {
        if (error instanceof SerializeError) {
          error.pos = str.length
          onError(error)
        } else {
          onError(new SerializeError(`fluent: ${error}`, str.length))
        }
        str += ERROR_RESULT
      }
    }
  }
  return str
}

function expression(expr: Expression | Markup, isSelector: boolean): string {
  if ('fn' in expr && isIdentifier(expr.fn)) {
    const options: string[] = []
    if (expr.opt) {
      for (const [name, value] of Object.entries(expr.opt)) {
        if (typeof value !== 'string') {
          const error = `fluent: Unsupported option value for ${name}`
          throw new SerializeError(error)
        }
        options.push(`${name}: ${literal(value)}`)
      }
    }
    switch (expr.fn) {
      case 'message': {
        if (expr._ !== undefined) {
          const id = expr._
          const isTerm = id.startsWith('-')
          const idName = isTerm ? id.substring(1) : id
          const validId = isIdentifier(idName)
          const validIdWithAttr = !validId && isIdWithAttr(idName)
          if (isSelector) {
            // E0016: Message references cannot be used as selectors
            // E0017: Terms cannot be used as selectors
            // E0018: Attributes of messages cannot be used as selectors
            if (isTerm && validIdWithAttr)
              return options.length ? `${id}(${options.join(', ')})` : id
          } else if (isTerm) {
            // E0019: Attributes of terms cannot be used as placeables
            if (validId)
              return options.length ? `${id}(${options.join(', ')})` : id
          } else {
            if ((validId || validIdWithAttr) && options.length === 0) return id
          }
        }
        const error = 'fluent: Unsupported message or term reference'
        throw new SerializeError(error)
      }
      case 'number':
        if (options.length === 0 && isNumber(expr._)) return expr._!
      // fallthrough
      default: {
        if ('_' in expr && expr._ !== undefined) {
          options.unshift(literal(expr._))
        } else if ('$' in expr && isIdentifier(expr.$)) {
          options.unshift('$' + expr.$)
        }
        return expr.fn.toUpperCase() + '(' + options.join(', ') + ')'
      }
    }
  }
  if ('_' in expr && expr._ !== undefined) return literal(expr._)
  if ('$' in expr && isIdentifier(expr.$)) return '$' + expr.$
  const error = `fluent: Unsupported pattern part ${JSON.stringify(expr)}`
  throw new SerializeError(error)
}

const literal = (value: string | undefined): string =>
  !value
    ? '""'
    : isNumber(value)
      ? value
      : `"${value.replace(/[\\"]/g, '\\$&').replaceAll('\n', '\\u000a')}"`

const isIdentifier = (value: string | undefined): value is string =>
  /^[A-Za-z][-0-9A-Z_a-z]*$/.test(value ?? '')

const isIdWithAttr = (value: string): boolean =>
  /^[A-Za-z][-0-9A-Z_a-z]*\.[A-Za-z][-0-9A-Z_a-z]*$/.test(value)

const isNumber = (value: string | undefined): boolean =>
  /^-?\d+(\.\d*)?$/.test(value ?? '')
