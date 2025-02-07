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

import type { Expression } from './model.ts'

export function appendText(el: Element, str: string) {
  if (el.lastChild instanceof Text) el.lastChild.data += str
  else el.appendChild(new Text(str))
}

export function serialize(root: Element) {
  const name = root.tagName
  const str = new XMLSerializer().serializeToString(root)
  if (str.startsWith(`<${name}`) && str.endsWith(`</${name}>`)) {
    return str.replace(/^<.*?>/, '').slice(0, -1 * (name.length + 3))
  } else {
    throw 'Unexpected XML serialization'
  }
}

export function* setAttributes(
  el: Element,
  opt: Expression['opt']
): Iterable<string> {
  if (opt) {
    for (const [name, value] of Object.entries(opt)) {
      if (typeof value === 'string') el.setAttribute(name, value)
      else yield `Unsupported value for <${el.tagName}> option ${name}`
    }
  }
}
