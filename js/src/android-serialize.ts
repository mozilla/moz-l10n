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

import { resoureRef } from './android-parse.ts'
import { ERROR_RESULT, SerializeError } from './errors.ts'
import { isExpression, type Expression, type Pattern } from './model.ts'
import { appendText, serialize, setAttributes } from './xml-utils.ts'

const xliffNS = 'urn:oasis:names:tc:xliff:document:1.2'

let xmlEntityKey = Math.floor(Math.random() * 1e9)

export function androidSerializePattern(
  pattern: Pattern,
  onError?: (error: SerializeError) => void
): string {
  onError ??= (error) => {
    throw error
  }
  if (
    pattern.length === 1 &&
    isExpression(pattern[0]) &&
    pattern[0].fn === 'reference'
  ) {
    // Android resource reference
    const arg = pattern[0]._ ?? ''
    if (!resoureRef.test(arg)) {
      const error = `android: Invalid reference: ${JSON.stringify(pattern[0])}`
      onError(new SerializeError(error))
    }
    return arg
  }

  const entities: Record<string, string> = {}
  const doc = new DOMParser().parseFromString(
    '<string xmlns:xliff="urn:oasis:names:tc:xliff:document:1.2"></string>',
    'text/xml'
  )
  const root = doc.querySelector('string')!
  let node = root
  for (const part of pattern) {
    if (typeof part === 'string') {
      appendText(node, escape(part))
    } else if (isExpression(part)) {
      if (part.attr?.translate == 'no') {
        const xliffg = doc.createElementNS(xliffNS, 'xliff:g')
        for (const error of setAttributes(xliffg, part.opt)) {
          onError(new SerializeError(`android: ${error}`))
        }
        xliffg.appendChild(new Text(asTextContent(part, entities, onError)))
        node.appendChild(xliffg)
      } else {
        appendText(node, asTextContent(part, entities, onError))
      }
    } else if (part.open) {
      const child = doc.createElementNS(
        part.open.startsWith('xliff:') ? xliffNS : null,
        part.open
      )
      for (const error of setAttributes(child, part.opt)) {
        onError(new SerializeError(`android: ${error}`))
      }
      node.appendChild(child)
      node = child
    } else if (part.close) {
      if (part.opt && Object.keys(part.opt).length) {
        const error = `android: Options on closing markup are not supported: ${JSON.stringify(part)}`
        onError(new SerializeError(error))
      }
      if (node !== root && node.tagName === part.close && node.parentElement) {
        node = node.parentElement
      } else {
        const error = `android: Improper element nesting for <${node.tagName}>`
        onError(new SerializeError(error))
      }
    } else {
      const error = `android: Unsupported markup ${JSON.stringify(part)}`
      onError(new SerializeError(error))
    }
  }
  if (node !== root) {
    const error = `android: Missing closing markup for ${node.tagName}`
    onError(new SerializeError(error))
  }
  quoteAndroidSpaces(root)
  let str: string
  try {
    str = serialize(root)
  } catch (error) {
    onError(new SerializeError(`xliff: ${error}`))
    return ERROR_RESULT
  }
  for (const [key, entity] of Object.entries(entities)) {
    str = str.replace(key, entity)
  }
  return str
}

const escapeChar = (ch: string) =>
  `\\u${ch.charCodeAt(0).toString(16).padStart(4, '0')}`

const escape = (src: string) =>
  src
    // Special Android characters
    .replaceAll('\\', '\\\\')
    .replaceAll('\n', '\\n')
    .replaceAll('\t', '\\t')
    .replaceAll("'", "\\'")
    .replaceAll('"', '\\"')
    // Control codes that are not valid in XML, and nonstandard whitespace
    // eslint-disable-next-line no-control-regex
    .replace(/[\x00-\x19\x7F-\x9F]|[^\S ]|(?<= ) /g, escapeChar)

function asTextContent(
  part: Expression,
  entities: Record<string, string>,
  onError: (error: SerializeError) => void
): string {
  if (part.fn === 'entity') {
    if (!part.$) {
      const error = `android: Invalid entity: ${JSON.stringify(part)}`
      onError(new SerializeError(error))
    }
    if (part.opt) {
      const error = `android: Unsupported options on entity &${part.$};`
      onError(new SerializeError(error))
    }
    const key = `_entity_${++xmlEntityKey}_`
    entities[key] = `&${part.$ ?? ''};`
    return key
  }
  if (typeof part.attr?.source === 'string') return part.attr.source
  if (part.fn && part.fn !== 'html') {
    onError(new SerializeError(`android: Unsupported function ${part.fn}`))
  }
  return part.$ ?? escape(part._ ?? '')
}

function quoteAndroidSpaces(el: Element) {
  const first = el.firstChild
  if (first instanceof Text && /^[ @?]/.test(first.data)) {
    first.data = escapeChar(first.data) + first.data.slice(1)
  }

  const last = el.lastChild
  if (last instanceof Text && last.data.endsWith(' ')) {
    last.data = last.data.slice(0, -1) + escapeChar(' ')
  }
}
