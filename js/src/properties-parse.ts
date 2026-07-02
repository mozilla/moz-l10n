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

import type { Pattern } from './model.ts'

export function propertiesParsePattern(src: string): Pattern {
  const value = src.replace(/\\(u[0-9A-Fa-f]{1,4}|.)/g, decodeEscape)
  return value ? [value] : []
}

function decodeEscape(_: unknown, esc: string): string {
  switch (esc) {
    case 'f':
      return '\f'
    case 'n':
      return '\n'
    case 'r':
      return '\r'
    case 't':
      return '\t'
    default:
      if (esc.startsWith('u')) {
        const n = parseInt(esc.substring(1), 16)
        if (!Number.isNaN(n)) return String.fromCharCode(n)
      }
      return esc
  }
}
