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

import type { Message, Pattern } from './model.ts'

/**
 * Determine if a message would format as an empty string.
 *
 * @param anyVariant - If `true`,
 *   having any of the variants of a `SelectMessage` be empty returns `true`.
 */
export function messageIsEmpty(msg: Message, anyVariant = false): boolean {
  const emptyPattern = (pat: Pattern) => pat.every((el) => el === '')
  if (Array.isArray(msg)) {
    return emptyPattern(msg)
  } else if (msg.msg) {
    return emptyPattern(msg.msg)
  } else {
    const patterns = msg.alt.map((a) => a.pat)
    return anyVariant
      ? patterns.some(emptyPattern)
      : patterns.every(emptyPattern)
  }
}
