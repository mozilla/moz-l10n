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

import { describe, expect, test } from 'vitest'

import { ParseError } from './errors.ts'
import type { Message, Pattern } from './model.ts'
import { mf2SerializeMessage, mf2SerializePattern } from './mf2-serialize.ts'
import { mf2ParseMessage, mf2ParsePattern } from './mf2-parse.ts'

describe('pattern success', () => {
  const ok = (name: string, pattern: Pattern, exp: string) =>
    test(name, () => {
      const src = mf2SerializePattern(pattern, false)
      expect(src).toBe(exp)

      const res = mf2ParsePattern(src)
      expect(res).toEqual(pattern)

      const msgSrc = mf2SerializeMessage(pattern)
      expect(msgSrc).toBe(exp)

      const msgRes = mf2ParseMessage(msgSrc)
      expect(msgRes).toEqual(pattern)
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

describe('pattern parse errors', () => {
  const fail = (name: string, src: string) =>
    test(name, () => {
      let error: any
      try {
        mf2ParsePattern(src)
      } catch (error_) {
        error = error_
      }
      expect(error).toBeInstanceOf(ParseError)
      expect(error.message).toMatch(/^mf2: /)
    })

  fail('extra brace', 'extra }')
  fail('empty placeholder', '{ }')
  fail('bad placeholder', '{::func}')
})

describe('message success', () => {
  const ok = (name: string, msg: Message, exp: string) =>
    test(name, () => {
      const src = mf2SerializeMessage(msg)
      expect(src).toBe(exp)

      const res = mf2ParseMessage(src)
      expect(res).toEqual(msg)
    })

  ok('quoted pattern', ['.hello'], '{{.hello}}')

  ok(
    'pattern with declarations',
    { decl: { a: { $: 'a', fn: 'func' }, b: { _: 'B' } }, msg: ['foo'] },
    `\
.input {$a :func}
.local $b = {B}
{{foo}}`
  )

  ok(
    'select',
    {
      decl: { num: { $: 'num', fn: 'number' } },
      sel: ['num'],
      alt: [
        { keys: ['0'], pat: ['Thanos has no Stones'] },
        { keys: ['1'], pat: ['Thanos has 1 Stone'] },
        { keys: ['6'], pat: ['Thanos has all the Stones'] },
        { keys: [{ '*': '' }], pat: ['Thanos has ', { $: 'num' }, ' Stones'] }
      ]
    },
    `\
.input {$num :number}
.match $num
0 {{Thanos has no Stones}}
1 {{Thanos has 1 Stone}}
6 {{Thanos has all the Stones}}
* {{Thanos has {$num} Stones}}`
  )
})
