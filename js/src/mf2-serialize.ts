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
  isExpression,
  type Message,
  type Expression,
  type Pattern,
  Markup
} from './model.ts'

export function mf2SerializeMessage(msg: Message) {
  if (Array.isArray(msg)) return mf2SerializePattern(msg, 'auto')

  let res = ''
  for (const [name, expr] of Object.entries(msg.decl)) {
    res += expr.$ === name ? '.input ' : `.local $${name} = `
    res += expression(expr) + '\n'
  }

  if (msg.msg) return res + mf2SerializePattern(msg.msg, true)

  res += '.match'
  for (const sel of msg.sel) res += ' $' + sel
  for (const { keys, pat } of msg.alt) {
    res += '\n'
    for (const key of keys) res += typeof key === 'string' ? key + ' ' : '* '
    res += mf2SerializePattern(pat, true)
  }
  return res
}

/**
 * @param quoted - If `true`, the pattern is always {{quoted}}.
 *   If `'auto'`, the pattern is quoted if it starts with a {{.period}}.
 *   If `false`, the output pattern is never quoted.
 */
export function mf2SerializePattern(
  pattern: Pattern,
  quoted: boolean | 'auto'
): string {
  let str = ''
  for (const part of pattern) {
    if (typeof part === 'string') {
      str += part.replace(/[\\{}]/g, '\\$&')
    } else {
      str += isExpression(part) ? expression(part) : markup(part)
    }
  }
  return quoted === true || (quoted === 'auto' && str.startsWith('.'))
    ? '{{' + str + '}}'
    : str
}

function expression(expr: Expression) {
  let str = '{'
  let hasArg = true
  if (typeof expr._ === 'string') str += literal(expr._)
  else if (expr.$) str += '$' + expr.$
  else hasArg = false
  if (expr.fn) {
    if (hasArg) str += ' '
    str += ':' + expr.fn + options(expr.opt)
  }
  str += attributes(expr.attr) + '}'
  return str
}

function markup(markup: Markup) {
  let str: string
  if (markup.open) str = '{#' + markup.open
  else if (markup.elem) str = '{#' + markup.elem
  else str = '{/' + markup.close
  str += options(markup.opt) + attributes(markup.attr)
  str += markup.elem ? '/}' : '}'
  return str
}

function options(opt: Expression['opt']) {
  let str = ''
  if (opt) {
    for (const [name, val] of Object.entries(opt)) {
      str += ` ${name}=`
      str += typeof val === 'string' ? literal(val) : '$' + val.$
    }
  }
  return str
}

function attributes(attr: Expression['attr']) {
  let str = ''
  if (attr) {
    for (const [name, val] of Object.entries(attr)) {
      str += ' @' + name
      if (typeof val === 'string') str += '=' + literal(val)
    }
  }
  return str
}

const nameStart =
  'a-zA-Z_\\xC0-\\xD6\\xD8-\\xF6\\xF8-\\u02FF\\u0370-\\u037D\\u037F-\\u061B\\u061D-\\u1FFF\\u200C-\\u200D\\u2070-\\u218F\\u2C00-\\u2FEF\\u3001-\\uD7FF\\uF900-\\uFDCF\\uFDF0-\\uFFFC\\u{010000}-\\u{0EFFFF}'
const name = new RegExp(
  // eslint-disable-next-line no-misleading-character-class
  `^[${nameStart}][${nameStart}0-9-.\\xb7\\u0300-\\u036f\\u203f-\\u2040]*$`,
  'u'
)
const number = /^-?(?:0|(?:[1-9]\d*))(?:.\d+)?(?:[eE][-+]?\d+)?$/
function literal(lit: string) {
  return name.test(lit) || number.test(lit)
    ? lit
    : '|' + lit.replace(/[\\|]/g, '\\$&') + '|'
}
