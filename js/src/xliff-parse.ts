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

import { ParseError } from './errors.ts'
import type { Expression, Markup, Pattern } from './model.ts'

export function xliffParsePattern(
  src: string,
  onError: (error: ParseError) => void
): Pattern {
  const doc = new DOMParser().parseFromString(
    `<target>${src}</target>`,
    'text/xml'
  )
  const root = doc.querySelector('target')
  const error = doc.querySelector('parsererror')
  if (!root || error) {
    const errMsg = 'xliff: ' + (error?.textContent ?? 'XML parser error')
    onError(new ParseError(errMsg))
    return []
  }
  return Array.from(parseElement(root))
}

// # https://developer.apple.com/library/archive/documentation/Cocoa/Conceptual/Strings/Articles/formatSpecifiers.html
const printf =
  /%([1-9]\$)?[-#+ 0,]?[0-9.]*(?:(?:hh?|ll?|qztj)[douxX]|L[aAeEfFgG]|[@%aAcCdDeEfFgGoOspSuUxX])/g

function* parseElement(el: Element): Iterable<string | Expression | Markup> {
  // @ts-expect-error No, TS, it _is_ iterable.
  for (const node of el.childNodes as Iterable<ChildNode>) {
    if (node instanceof Text) {
      const src = node.data
      let pos = 0
      for (const m of src.matchAll(printf)) {
        if (m.index > pos) yield src.substring(pos, m.index)
        const ms = m[0]
        pos = m.index + ms.length
        const attr = Object.create(null)
        attr.source = ms
        const n = m[1]?.[0] ?? ''
        switch (ms.at(-1)) {
          case '%':
            yield { _: '%', attr }
            break
          case 'c':
          case 'C':
          case 's':
          case 'S':
            yield { $: `str${n}`, fn: 'string', attr }
            break
          case 'd':
          case 'D':
          case 'o':
          case 'O':
          case 'p':
          case 'u':
          case 'U':
          case 'x':
          case 'X':
            yield { $: `int${n}`, fn: 'integer', attr }
            break
          case 'a':
          case 'A':
          case 'e':
          case 'E':
          case 'f':
          case 'g':
          case 'G':
            yield { $: `num${n}`, fn: 'number', attr }
            break
          default:
            yield { $: `arg${n}`, attr }
        }
      }
      if (pos < src.length) yield src.substring(pos)
    } else if (node instanceof Element) {
      const name = node.tagName
      let opt: Record<string, string> | undefined = undefined
      if (node.hasAttributes()) {
        opt = Object.create(null) as Record<string, string>
        // @ts-expect-error No, TS, it _is_ iterable.
        for (const attr of node.attributes as Iterable<Attr>) {
          opt[attr.name] = attr.value
        }
      }
      if (name === 'x' || name === 'bx' || name === 'ex') {
        yield { elem: name, opt }
      } else {
        yield { open: name, opt }
        yield* parseElement(node)
        yield { close: name }
      }
    }
  }
}
