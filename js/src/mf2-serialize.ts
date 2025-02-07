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

import { isExpression, type Expression, type Pattern } from './model.ts'

export function mf2SerializePattern(pattern: Pattern): string {
  let str = ''
  for (const part of pattern) {
    if (typeof part === 'string') {
      str += part.replace(/[\\{}]/g, '\\$&')
    } else if (isExpression(part)) {
      str += '{'
      let hasArg = true
      if (typeof part._ === 'string') str += literal(part._)
      else if (part.$) str += '$' + part.$
      else hasArg = false
      if (part.fn) {
        if (hasArg) str += ' '
        str += ':' + part.fn + options(part.opt)
      }
      str += attributes(part.attr) + '}'
    } else {
      if (part.open) str += '{#' + part.open
      else if (part.elem) str += '{#' + part.elem
      else str += '{/' + part.close
      str += options(part.opt) + attributes(part.attr)
      str += part.elem ? '/}' : '}'
    }
  }
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
