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
import { messageIsEmpty, SelectMessage } from './index.ts'

describe('messageIsEmpty', () => {
  test('Pattern', () => {
    expect(messageIsEmpty([])).toBe(true)
    expect(messageIsEmpty(['', ''])).toBe(true)
    expect(messageIsEmpty([' '])).toBe(false)
  })

  test('PatternMessage', () => {
    expect(messageIsEmpty({ decl: {}, msg: [] })).toBe(true)
    expect(messageIsEmpty({ decl: { x: { _: '' } }, msg: ['', ''] })).toBe(true)
    expect(messageIsEmpty({ decl: {}, msg: [' '] })).toBe(false)
    expect(messageIsEmpty([' '])).toBe(false)
  })

  test('SelectMessage', () => {
    expect(messageIsEmpty({ decl: {}, sel: [], alt: [] })).toBe(true)
    expect(
      messageIsEmpty({ decl: {}, sel: [], alt: [{ keys: ['a'], pat: [''] }] })
    ).toBe(true)
    const sm: SelectMessage = {
      decl: {},
      sel: [],
      alt: [
        { keys: ['a'], pat: ['A'] },
        { keys: ['b'], pat: [''] }
      ]
    }
    expect(messageIsEmpty(sm)).toBe(false)
    expect(messageIsEmpty(sm, true)).toBe(true)
  })
})
