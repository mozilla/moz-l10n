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
import { appendText, serialize, setAttributes } from './xml-utils.ts'

export function xliffSerializePattern(
  pattern: Pattern,
  onError?: (error: SerializeError) => void
): string {
  onError ??= (error) => {
    throw error
  }
  const doc = new DOMParser().parseFromString('<target></target>', 'text/xml')
  const root = doc.querySelector('target')!
  let node = root
  for (const part of pattern) {
    if (typeof part === 'string') {
      appendText(node, part)
    } else if (part.open || part.elem) {
      const name = part.open || part.elem!
      const child = doc.createElementNS(null, name)
      for (const error of setAttributes(child, part.opt)) {
        onError(new SerializeError(`xliff: ${error}`))
      }
      node.appendChild(child)
      if (part.open) node = child
    } else if (part.close) {
      if (part.opt && Object.keys(part.opt).length) {
        const error = `xliff: Options on closing markup are not supported: ${JSON.stringify(part)}`
        onError(new SerializeError(error))
      }
      if (node !== root && node.tagName === part.close && node.parentElement) {
        node = node.parentElement
      } else {
        const error = `xliff: Improper element nesting for <${node.tagName}>`
        onError(new SerializeError(error))
      }
    } else if (typeof part.attr?.source === 'string') {
      appendText(node, part.attr.source)
    } else if (part._ || part.$) {
      appendText(node, part._ || part.$!)
    } else {
      const error = `xliff: Unsupported pattern part ${JSON.stringify(part)}`
      onError(new SerializeError(error))
      appendText(node, ERROR_RESULT)
    }
  }
  if (node !== root) {
    const error = `xliff: Missing closing markup for <${node.tagName}>`
    onError(new SerializeError(error))
  }
  try {
    return serialize(root)
  } catch (error) {
    onError(new SerializeError(`xliff: ${error}`))
    return ERROR_RESULT
  }
}
