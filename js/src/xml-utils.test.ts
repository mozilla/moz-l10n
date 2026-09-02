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

import { describe, expect, test } from 'vitest'
import { escapeNonSyntaxChars } from './xml-utils.ts'

describe('escapeNonSyntaxChars', () => {
  test('standalone angle brackets', () => {
    const res = escapeNonSyntaxChars('< &lt; <<')
    expect(res).toBe('&lt; &lt; &lt;&lt;')
  })

  test('paired angle brackets', () => {
    const res = escapeNonSyntaxChars('< &lt; ><')
    expect(res).toBe('< &lt; >&lt;')
  })

  test('ampersand', () => {
    const res = escapeNonSyntaxChars('& &amp; &&')
    expect(res).toBe('&amp; &amp; &amp;&amp;')
  })

  test('entity references', () => {
    const res = escapeNonSyntaxChars('&foo; &#38;')
    expect(res).toBe('&foo; &#38;')
  })
})
