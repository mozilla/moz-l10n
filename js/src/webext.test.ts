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

import { expect, test, vi } from 'vitest'

import { ParseError, SerializeError } from './errors.ts'
import type { Pattern, PatternMessage } from './model.ts'
import { webextParsePattern, webextSerializePattern } from './webext.ts'

const ok = (name: string, msg: Pattern | PatternMessage, exp: string) =>
  test(name, () => {
    const pattern = Array.isArray(msg) ? msg : msg.msg
    const onError = vi.fn()

    const src = webextSerializePattern(pattern, onError)
    expect(onError).not.toHaveBeenCalled()
    expect(src).toBe(exp)

    const res = webextParsePattern(msg, src, onError)
    expect(onError).not.toHaveBeenCalled()
    expect(res).toEqual(pattern)
  })

ok(
  'unnamed placeholder',
  ['Hello ', { $: 'arg2', attr: { source: '$2' } }],
  'Hello $2'
)

ok(
  'named placeholder',
  {
    decl: { world: { $: 'arg1', attr: { source: '$1' } } },
    msg: ['Hello ', { $: 'world', attr: { source: '$WORLD$' } }]
  },
  'Hello $WORLD$'
)

ok(
  'repeated named placeholder',
  {
    decl: { foo: { $: 'arg1', attr: { source: '$1' } } },
    msg: [
      { $: 'foo', attr: { source: '$FOO$' } },
      { $: 'foo', attr: { source: '$Foo$' } }
    ]
  },
  '$FOO$$Foo$'
)

test('unresolved variable', () => {
  const onError = vi.fn()
  const res = webextParsePattern(
    {
      decl: { foo: { $: 'arg1', attr: { source: '$1' } } },
      msg: []
    },
    'Has $Bar$?',
    onError
  )
  expect(onError).toHaveBeenCalled()
  const error = onError.mock.calls[0][0]
  expect(error).toBeInstanceOf(ParseError)
  expect(error.message).toBe('webext: Unresolved Variable $Bar$')
  expect(res).toEqual(['Has ', { $: 'bar', attr: { source: '$Bar$' } }, '?'])
})

test('unsupported pattern part', () => {
  const onError = vi.fn()
  const src = webextSerializePattern(['Hello ', { _: 'world' }, '?'], onError)
  expect(onError).toHaveBeenCalled()
  const error = onError.mock.calls[0][0]
  expect(error).toBeInstanceOf(SerializeError)
  expect(error.message).toBe('webext: Unsupported pattern part {"_":"world"}')
  expect(error.pos).toBe(6)
  expect(src).toBe('Hello {�}?')
})
