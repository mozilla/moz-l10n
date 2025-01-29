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

import { ERROR_RESULT, ParseError, SerializeError } from './errors.ts'
import { fluentParsePattern } from './fluent-parse.ts'
import { fluentSerializePattern } from './fluent-serialize.ts'
import type { Pattern } from './model.ts'

describe('success', () => {
  const ok = (name: string, pattern: Pattern, exp: string) =>
    test(name, () => {
      const onError = vi.fn()

      const src = fluentSerializePattern(pattern, onError)
      expect(onError).not.toHaveBeenCalled()
      expect(src).toBe(exp)

      const res = fluentParsePattern(src, onError)
      expect(onError).not.toHaveBeenCalled()
      expect(res).toEqual(pattern)
    })

  ok('multiple lines', ['Hello\nthe\n\n  \tworld'], 'Hello\nthe\n\n  \tworld')
  ok('empty literal', [{ _: '' }], '{ "" }')
  ok('literal escapes', [{ _: 'one\n"two}' }], '{ "one\\u000a\\"two}" }')
  ok('variable reference', ['Hello ', { $: 'world' }], 'Hello { $world }')
  ok(
    'literals',
    [{ _: 'one' }, ' ', { _: '42', fn: 'number' }],
    '{ "one" } { 42 }'
  )
  ok('function', [{ $: 'x', fn: 'foo' }], '{ FOO($x) }')
  ok(
    'options',
    [
      {
        $: 'x',
        fn: 'number',
        opt: { minimumFractionDigits: '2', notation: 'compact' }
      }
    ],
    '{ NUMBER($x, minimumFractionDigits: 2, notation: "compact") }'
  )
  ok('message reference', [{ _: 'foo.bar', fn: 'message' }], '{ foo.bar }')
  ok('term reference', [{ _: '-foo', fn: 'message' }], '{ -foo }')
  ok(
    'term reference options',
    [{ _: '-foo', fn: 'message', opt: { bar: '42' } }],
    '{ -foo(bar: 42) }'
  )
})

describe('parse errors', () => {
  const fail = (name: string, src: string, code: string) =>
    test(name, () => {
      const onError = vi.fn()
      fluentParsePattern(src, onError)
      expect(onError).toHaveBeenCalledOnce()
      const error = onError.mock.calls[0][0]
      expect(error).toBeInstanceOf(ParseError)
      expect(error.message).toMatch(new RegExp(`^fluent: .*\\(${code}\\)$`))
    })

  fail('extra brace', 'extra }', 'E0027')
  fail('empty placeable', '{ }', 'E0028')
  fail('selector', '{ $x ->\n *[x] X\n }', 'E0028')
  fail('term attribute reference', '{ -foo.bar }', 'E0019')
  fail('lower-case function', '{ foo() }', 'E0008')
  fail('newline in literal', '{ "foo\nbar" }', 'E0020')
})

describe('serialize errors', () => {
  const fail = (name: string, pattern: Pattern) =>
    test(name, () => {
      const onError = vi.fn()
      const src = fluentSerializePattern(pattern, onError)
      expect(onError).toHaveBeenCalledOnce()
      const error = onError.mock.calls[0][0]
      expect(error).toBeInstanceOf(SerializeError)
      expect(error.message).toMatch(/^fluent: /)
      expect(src).toBe(ERROR_RESULT)
    })

  fail('markup', [{ open: 'x' }])
  fail('option with variable value', [
    { _: '42', fn: 'func', opt: { o: { $: 'var' } } }
  ])
  fail('invalid message reference id', [{ _: '42', fn: 'message' }])
  fail('invalid message reference options', [
    { _: 'foo', fn: 'message', opt: { x: 'y' } }
  ])
  fail('invalid term reference', [{ _: '-foo.bar', fn: 'message' }])
})
