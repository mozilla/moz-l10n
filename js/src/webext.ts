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

import { ERROR_RESULT, ParseError, SerializeError } from './errors.ts'
import type { Message, Pattern } from './model.ts'

export function webextParsePattern(
  msg: Message,
  src: string,
  onError: (error: ParseError) => void
): Pattern {
  const decl = Array.isArray(msg) ? {} : msg.decl
  const pattern: Pattern = []
  const addText = (text: string) => {
    if (typeof pattern.at(-1) == 'string') pattern[pattern.length - 1] += text
    else pattern.push(text)
  }
  let pos = 0
  for (const m of src.matchAll(/\$([a-zA-Z0-9_@]+)\$|(\$[1-9])|\$(\$+)/dg)) {
    if (m.index > pos) addText(src.substring(pos, m.index))
    const matchSrc = m[0]
    pos = m.index + matchSrc.length
    if (m[1]) {
      // Named placeholder
      const name = m[1].toLowerCase()
      const attr = Object.assign(Object.create(null), { source: matchSrc })
      pattern.push({ $: name, attr })
      if (!decl[name]) {
        const error = `webext: Unresolved Variable ${matchSrc}`
        onError(new ParseError(error, m.index, pos))
      }
    } else if (m[2]) {
      // Indexed placeholder
      const attr = Object.assign(Object.create(null), { source: matchSrc })
      pattern.push({ $: `arg${m[2][1]}`, attr })
    } else {
      // Escaped literal dollar sign
      addText(m[3])
    }
  }
  if (pos < src.length) addText(src.substring(pos))
  return pattern
}

export function webextSerializePattern(
  pattern: Pattern,
  onError: (error: SerializeError) => void
): string {
  let str = ''
  for (const part of pattern) {
    if (typeof part === 'string') {
      str += part.replace(/\$+/g, '$$$&')
    } else if ('$' in part) {
      str += part.attr?.source ?? `$${part.$}$`
    } else {
      const error = `webext: Unsupported pattern part ${JSON.stringify(part)}`
      onError(new SerializeError(error, str.length))
      str += ERROR_RESULT
    }
  }
  return str
}
