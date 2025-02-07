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

import { ParseError } from './errors.ts'
import type { Pattern } from './model.ts'
import { mf2SerializePattern } from './mf2-serialize.ts'
import { mf2ParsePattern } from './mf2-parse.ts'

describe('success', () => {
  const ok = (name: string, pattern: Pattern, exp: string) =>
    test(name, () => {
      const src = mf2SerializePattern(pattern)
      expect(src).toBe(exp)

      const onError = vi.fn()
      const res = mf2ParsePattern(src, onError)
      expect(onError).not.toHaveBeenCalled()
      expect(res).toEqual(pattern)
    })

  ok('empty pattern', [], '')
  ok('whitespace', ['  \n\t'], '  \n\t')
  ok('empty literal', [{ _: '' }], '{||}')
  ok('literal number', [{ _: '42' }], '{42}')
  ok('quoted literal', [{ _: 'foo bar|baz' }], '{|foo bar\\|baz|}')
  ok(
    'function with options',
    [
      {
        $: 'var',
        fn: 'test:string',
        opt: { 'opt-a': '42', 'opt:b': { $: 'var' } }
      }
    ],
    '{$var :test:string opt-a=42 opt:b=$var}'
  )
  ok(
    'markup',
    [
      'text1 ',
      { $: 'var' },
      ' text2 ',
      { open: 'm:open' },
      'text3',
      { close: 'm:close' },
      { elem: 'm:standalone' }
    ],
    'text1 {$var} text2 {#m:open}text3{/m:close}{#m:standalone/}'
  )
  ok(
    'attributes',
    [{ $: 'var', attr: { foo: true, bar: 'baz' } }],
    '{$var @foo @bar=baz}'
  )
})

describe('parse errors', () => {
  const fail = (name: string, src: string) =>
    test(name, () => {
      const onError = vi.fn()
      mf2ParsePattern(src, onError)
      expect(onError).toHaveBeenCalledOnce()
      const error = onError.mock.calls[0][0]
      expect(error).toBeInstanceOf(ParseError)
      expect(error.message).toMatch(/^mf2: /)
    })

  fail('extra brace', 'extra }')
  fail('empty placeholder', '{ }')
  fail('bad placeholder', '{::func}')
})
