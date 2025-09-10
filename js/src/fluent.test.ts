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
import ftl from '@fluent/dedent'

import { ERROR_RESULT, ParseError, SerializeError } from './errors.ts'
import { fluentParseEntry, fluentParsePattern } from './fluent-parse.ts'
import { fluentSerializePattern } from './fluent-serialize.ts'
import type { Entry, Pattern } from './model.ts'

describe('pattern success', () => {
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

describe('pattern parse errors', () => {
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

describe('pattern serialize errors', () => {
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

describe('entry parse', () => {
  const ok = (name: string, src: string, exp: Entry) =>
    test(name, () => {
      const res = fluentParseEntry(src)
      expect(res).toEqual([name, exp])
    })

  const fail = (name: string, src: string, code: string | null) =>
    test(name, () => {
      try {
        fluentParseEntry(src)
        throw Error('Expectred an error')
        // @ts-expect-error yes, we check this.
      } catch (error: ParseError) {
        expect(error).toBeInstanceOf(ParseError)
        if (code) {
          expect(error.message).toMatch(
            new RegExp(`^fluent(\\(\\w+\\))?: .*\\(${code}\\)$`)
          )
        } else {
          expect(error.message).toMatch(/^fluent/)
        }
      }
    })

  ok('plain', 'plain = Progress: { NUMBER($num, style: "percent") }.', {
    '=': [
      'Progress: ',
      { $: 'num', fn: 'number', opt: { style: 'percent' } },
      '.'
    ]
  })

  ok(
    'num-no-placeholder',
    ftl`
    num-no-placeholder =
        { $num ->
            [one] One
           *[other] Other
        }
    `,
    {
      '=': {
        decl: { num: { $: 'num', fn: 'number' } },
        sel: ['num'],
        alt: [
          { keys: ['one'], pat: ['One'] },
          { keys: [{ '*': 'other' }], pat: ['Other'] }
        ]
      }
    }
  )

  ok(
    'num-has-placeholder',
    ftl`
    num-has-placeholder =
        { $num ->
            [one] One { $num }
           *[other] Other
        }
    `,
    {
      '=': {
        decl: { num_1: { $: 'num', fn: 'number' } },
        sel: ['num_1'],
        alt: [
          { keys: ['one'], pat: ['One ', { $: 'num' }] },
          { keys: [{ '*': 'other' }], pat: ['Other'] }
        ]
      }
    }
  )

  ok('-term-with-attr', '-term-with-attr = body\n  .attr = value\n', {
    '=': ['body'],
    '+': { attr: ['value'] }
  })

  ok(
    'two-sels',
    ftl`
    two-sels =
        pre { $a ->
            [1] One
           *[2] Two
        } mid { $b ->
           *[bb] BB
            [cc] CC
        } post
    `,
    {
      '=': {
        decl: {
          a: { $: 'a', fn: 'number' },
          b: { $: 'b', fn: 'string' }
        },
        sel: ['a', 'b'],
        alt: [
          { keys: ['1', { '*': 'bb' }], pat: ['pre One mid BB post'] },
          { keys: ['1', 'cc'], pat: ['pre One mid CC post'] },
          { keys: [{ '*': '2' }, { '*': 'bb' }], pat: ['pre Two mid BB post'] },
          { keys: [{ '*': '2' }, 'cc'], pat: ['pre Two mid CC post'] }
        ]
      }
    }
  )

  ok(
    'deep-sels',
    ftl`
    deep-sels =
      { $a ->
          [0]
            { $b ->
                [one] {""}
               *[other] 0,x
            }
          [one]
            { $b ->
                [one] {"1,1"}
               *[other] 1,x
            }
         *[other]
            { $b ->
                [0] x,0
                [one] x,1
               *[other] x,x
            }
      }
    `,
    {
      '=': {
        decl: {
          a: { $: 'a', fn: 'number' },
          b: { $: 'b', fn: 'number' }
        },
        sel: ['a', 'b'],
        alt: [
          { keys: ['0', 'one'], pat: [{ _: '' }] },
          { keys: ['0', { '*': 'other' }], pat: ['0,x'] },
          { keys: ['one', 'one'], pat: [{ _: '1,1' }] },
          { keys: ['one', { '*': 'other' }], pat: ['1,x'] },
          { keys: [{ '*': 'other' }, 'one'], pat: ['x,1'] },
          { keys: [{ '*': 'other' }, { '*': 'other' }], pat: ['x,x'] },
          { keys: [{ '*': 'other' }, '0'], pat: ['x,0'] }
        ]
      }
    }
  )

  ok(
    'term-attr-sel',
    ftl`
    term-attr-sel =
      { -term.attr ->
         [foo] Foo
        *[other] Other
      }
    `,
    {
      '=': {
        decl: { _1: { _: '-term.attr', fn: 'message' } },
        sel: ['_1'],
        alt: [
          { keys: ['foo'], pat: ['Foo'] },
          { keys: [{ '*': 'other' }], pat: ['Other'] }
        ]
      }
    }
  )

  fail(
    'term-sel',
    ftl`
    term-sel =
      { -term ->
         [foo] Foo
        *[other] Other
      }
    `,
    'E0017'
  )

  ok('comment', '# comment\ncomment = value', { '=': ['value'] })
  ok('skip-comment', '# comment\n\n\n\nskip-comment = value', {
    '=': ['value']
  })
  fail('standalone comment', '# comment\n', 'E0002')

  fail('missing key', 'value\n', 'E0003')
  fail('missing expression end', 'key = missing {', 'E0028')
  fail('missing expression body', 'key = missing {}\n', 'E0028')
})
