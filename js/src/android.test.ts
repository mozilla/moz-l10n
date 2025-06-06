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

import { androidParsePattern } from './android-parse.ts'
import { androidSerializePattern } from './android-serialize.ts'
import { ParseError, SerializeError } from './errors.ts'
import type { Pattern } from './model.ts'

describe('success', () => {
  const ok = (name: string, pattern: Pattern, exp: string) =>
    test(name, () => {
      const onError = vi.fn()

      const src = androidSerializePattern(pattern, onError)
      expect(onError).not.toHaveBeenCalled()
      expect(src).toBe(exp)

      const res = androidParsePattern(src, onError)
      expect(onError).not.toHaveBeenCalled()
      expect(res).toEqual(pattern)
    })

  ok(
    'resource reference',
    [{ _: '@foo:bar/baz', fn: 'reference' }],
    '@foo:bar/baz'
  )
  ok(
    'whitespace',
    ['Hello\nthe\n\n  \tworld'],
    'Hello\\nthe\\n\\n \\u0020\\tworld'
  )
  ok(
    'inline variable',
    ['Hello, ', { $: 'arg1', fn: 'string', attr: { source: '%1$s' } }, '!'],
    'Hello, %1$s!'
  )
  ok('html elements', [{ open: 'b' }, 'bold', { close: 'b' }], '<b>bold</b>')
  ok(
    'escaped html',
    [{ _: '<b>', fn: 'html' }, 'bold', { _: '</b>', fn: 'html' }],
    '&lt;b&gt;bold&lt;/b&gt;'
  )
  ok(
    'protected variable',
    [
      {
        $: 'user',
        fn: 'xliff:g',
        opt: { id: 'user', example: 'Bob' },
        attr: { translate: 'no', source: '%1$s' }
      }
    ],
    '<xliff:g id="user" example="Bob">%1$s</xliff:g>'
  )
  ok(
    'nested protections',
    [
      'Welcome to ',
      { open: 'xliff:g', attr: { translate: 'no' } },
      { open: 'b' },
      { _: 'Foo', attr: { translate: 'no' } },
      { close: 'b' },
      '!',
      { close: 'xliff:g', attr: { translate: 'no' } }
    ],
    'Welcome to <xliff:g><b><xliff:g>Foo</xliff:g></b>!</xliff:g>'
  )
  ok(
    'entity reference',
    [
      'Welcome to ',
      { open: 'b' },
      { $: 'foo', fn: 'entity' },
      { close: 'b' },
      '!'
    ],
    'Welcome to <b>&foo;</b>!'
  )
})

describe('parse errors', () => {
  test('invalid xml', () => {
    const onError = vi.fn()
    androidParsePattern('Hello <b>', onError)
    expect(onError).toHaveBeenCalledOnce()
    const error = onError.mock.calls[0][0]
    expect(error).toBeInstanceOf(ParseError)
    expect(error.message).toMatch(/^android: /)
  })
})

describe('serialize errors', () => {
  const fail = (name: string, pattern: Pattern) =>
    test(name, () => {
      const onError = vi.fn()
      androidSerializePattern(pattern, onError)
      expect(onError).toHaveBeenCalled()
      const error = onError.mock.calls[0][0]
      expect(error).toBeInstanceOf(SerializeError)
      expect(error.message).toMatch(/^android: /)
    })

  fail('invalid resource reference', [{ _: 'foo', fn: 'reference' }])
  fail('missing close', [{ open: 'b' }, 'bold'])
  fail('improper close', [{ open: 'b' }, 'bold', { close: 'a' }])
  fail('invalid entity value', [{ _: 'ent', fn: 'entity' }])
  fail('invalid entity options', [{ $: 'ent', fn: 'entity', opt: { x: 'y' } }])
  fail('unsupported function without source', [{ $: 'key', fn: 'number' }])
})
