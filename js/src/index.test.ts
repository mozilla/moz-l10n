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

import { describe, expect, test, vi } from 'vitest'
import {
  FormatKey,
  ParseError,
  parsePattern,
  Pattern,
  SerializeError,
  serializePattern
} from './index.ts'

describe('parsePattern', () => {
  test('plain', () => {
    const pattern = parsePattern('plain', '{foo %s}')
    expect(pattern).toEqual(['{foo %s}'])
  })

  for (const [format, str, exp] of [
    ['unsupported' as FormatKey, 'bar', ['bar']],
    ['android', 'invalid <xml>', []],
    ['fluent', 'invalid }', ['invalid ', '}']]
  ] as [FormatKey, string, Pattern][]) {
    test(`${format} throw`, () => {
      expect(() => parsePattern(format, str)).toThrow(ParseError)
    })

    test(`${format} onError`, () => {
      const onError = vi.fn()
      const pattern = parsePattern(format, str, undefined, onError)
      expect(onError).toHaveBeenCalled()
      const error = onError.mock.calls[0][0]
      expect(error).toBeInstanceOf(ParseError)
      expect(error.message).toMatch(new RegExp(`^${format}: `))
      expect(pattern).toEqual(exp)
    })
  }
})

describe('serializePattern', () => {
  test('plain', () => {
    const str = serializePattern('plain', ['{foo %s}'])
    expect(str).toBe('{foo %s}')
  })

  for (const [format, pattern, exp] of [
    ['unsupported' as FormatKey, ['bar'], 'bar'],
    ['plain', ['hello ', { _: 'lit' }], 'hello {�}'],
    ['android', [{ open: 'x' }, 'not closed'], '<x>not closed</x>'],
    ['fluent', [{ _: undefined }, { $: undefined }], '{�}{�}']
  ] as [FormatKey, Pattern, string][]) {
    test(`${format} throw`, () => {
      expect(() => serializePattern(format, pattern)).toThrow(SerializeError)
    })

    test(`${format} onError`, () => {
      const onError = vi.fn()
      const str = serializePattern(format, pattern, onError)
      expect(onError).toHaveBeenCalled()
      const error = onError.mock.calls[0][0]
      expect(error).toBeInstanceOf(SerializeError)
      expect(error.message).toMatch(new RegExp(`^${format}: `))
      expect(str).toBe(exp)
    })
  }
})
