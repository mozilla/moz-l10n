/* eslint-disable @typescript-eslint/no-explicit-any */

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
import type { Pattern } from './model.ts'
import { xliffSerializePattern } from './xliff-serialize.ts'
import { ParseError, SerializeError } from './errors.ts'
import { xliffParsePattern } from './xliff-parse.ts'

describe('success', () => {
  const ok = (name: string, pattern: Pattern, exp: string) =>
    test(name, () => {
      const src = xliffSerializePattern(pattern)
      expect(src).toBe(exp)

      const res = xliffParsePattern(src)
      expect(res).toEqual(pattern)
    })

  ok('plain', ['hello'], 'hello')
  ok('whitespace', [' Hello\nthe\n\n  \tworld\n'], ' Hello\nthe\n\n  \tworld\n')
  ok(
    'inline variable',
    [
      'Hello, ',
      { $: 'str', fn: 'string', attr: { source: '%s' } },
      ' and ',
      { $: 'int2', fn: 'integer', attr: { source: '%2$d' } },
      '!'
    ],
    'Hello, %s and %2$d!'
  )
  ok('html elements', [{ open: 'b' }, 'bold', { close: 'b' }], '<b>bold</b>')
  ok(
    'standalone element',
    [
      { elem: 'x', opt: { id: 'INTERPOLATION', 'equiv-text': '{{minutes}}' } },
      ' minutes ago'
    ],
    '<x id="INTERPOLATION" equiv-text="{{minutes}}"/> minutes ago'
  )
})

describe('parse errors', () => {
  test('invalid xml', () => {
    let error: any
    try {
      xliffParsePattern('Hello <b>')
    } catch (error_) {
      error = error_
    }
    expect(error).toBeInstanceOf(ParseError)
    expect(error.message).toMatch(/^xliff: /)
  })
})

describe('serialize errors', () => {
  const fail = (name: string, pattern: Pattern) =>
    test(name, () => {
      const onError = vi.fn()
      xliffSerializePattern(pattern, onError)
      expect(onError).toHaveBeenCalled()
      const error = onError.mock.calls[0][0]
      expect(error).toBeInstanceOf(SerializeError)
      expect(error.message).toMatch(/^xliff: /)
    })

  fail('missing close', [{ open: 'b' }, 'bold'])
  fail('improper close', [{ open: 'b' }, 'bold', { close: 'a' }])
  fail('unsupported function without source', [{ fn: 'number' }])
})
