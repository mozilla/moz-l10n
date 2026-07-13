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
import type { Pattern } from './model.ts'

export function propertiesSerializePattern(
  pattern: Pattern,
  onError?: (error: SerializeError) => void
): string {
  onError ??= (error) => {
    throw error
  }
  let str = ''
  for (const part of pattern) {
    if (typeof part === 'string') {
      str += part
    } else {
      const source = part.attr?.source
      if (typeof source === 'string') {
        str += source
      } else {
        const error = `properties: Unsupported pattern part ${JSON.stringify(part)}`
        onError(new SerializeError(error, str.length))
        str += ERROR_RESULT
      }
    }
  }

  // eslint-disable-next-line no-control-regex
  str = str.replace(/[\x00-\x19\x5C\x7F-\x9F]/g, encodeChar)
  if (str.startsWith(' ')) str = '\\' + str
  if (str.endsWith(' ') && !str.endsWith('\\ ')) {
    str = str.slice(0, -1) + '\\u0020'
  }

  return str
}

function encodeChar(ch: string): string {
  switch (ch) {
    case '\\':
      return '\\\\'
    case '\t':
      return '\\t'
    case '\n':
      return '\\n'
    case '\f':
      return '\\f'
    case '\r':
      return '\\r'
    default:
      return `\\u${ch.charCodeAt(0).toString(16).padStart(4, '0')}`
  }
}
