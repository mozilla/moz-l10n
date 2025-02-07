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
import type { Expression, Markup, Pattern } from './model.ts'

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
        str += `{ ${expression(part)} }`
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

function expression(expr: Expression | Markup) {
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
          if (id[0] === '-' && isIdentifier(id.substring(1))) {
            return options.length ? `${id}(${options.join(', ')})` : id
          }
          if (isMsgRef(id) && options.length === 0) return id
        }
        const error = 'fluent: Unsupported message or term reference'
        throw new SerializeError(error)
      }
      case 'number':
        if (options.length === 0 && isNumber(expr._)) return expr._
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

const isMsgRef = (value: string): boolean =>
  /^[A-Za-z][-0-9A-Z_a-z]*(\.[A-Za-z][-0-9A-Z_a-z]*)?$/.test(value)

const isNumber = (value: string | undefined): boolean =>
  /^-?\d+(\.\d*)?$/.test(value ?? '')
