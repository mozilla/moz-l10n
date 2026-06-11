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
import {
  type Message,
  messageIsEmpty,
  normalizeMessage,
  type SelectMessage
} from './index.ts'

describe('messageIsEmpty', () => {
  test('Pattern', () => {
    expect(messageIsEmpty([])).toBe(true)
    expect(messageIsEmpty(['', ''])).toBe(true)
    expect(messageIsEmpty([' '])).toBe(false)
  })

  test('PatternMessage', () => {
    expect(messageIsEmpty({ decl: {}, msg: [] })).toBe(true)
    expect(messageIsEmpty({ decl: { x: { _: 'X' } }, msg: ['', ''] })).toBe(
      true
    )
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

describe('normalizeMessage', () => {
  test('literals in pattern', () => {
    expect(normalizeMessage([''])).toEqual([])
    expect(normalizeMessage(['', '\n'])).toEqual(['\n'])
    expect(normalizeMessage(['foo', '', ''])).toEqual(['foo'])
    expect(normalizeMessage(['foo', '', 'bar'])).toEqual(['foobar'])
    expect(normalizeMessage(['foo', { _: '' }, 'bar'])).toEqual([
      'foo',
      { _: '' },
      'bar'
    ])
    expect(
      normalizeMessage(['foo', { _: '', attr: undefined }, 'bar'])
    ).toEqual(['foo', { _: '', attr: undefined }, 'bar'])
    expect(normalizeMessage(['foo', { _: '', attr: {} }, 'bar'])).toEqual([
      'foo',
      { _: '', attr: {} },
      'bar'
    ])
  })

  test('unused declarations', () => {
    expect(normalizeMessage({ decl: { x: { _: 'x' } }, msg: ['x'] })).toEqual([
      'x'
    ])
    expect(
      normalizeMessage({
        decl: { x: { $: 'x' }, y: { _: 'y' } },
        msg: ['', { $: 'x' }]
      })
    ).toEqual({ decl: { x: { $: 'x' } }, msg: [{ $: 'x' }] })
  })

  test('variable reference in option value', () => {
    expect(
      normalizeMessage({
        decl: { x: { $: 'x' }, y: { _: 'y' } },
        msg: ['', { _: 'y', fn: 'fn', opt: { o: { $: 'x' } } }]
      })
    ).toEqual({
      decl: { x: { $: 'x' } },
      msg: [{ _: 'y', fn: 'fn', opt: { o: { $: 'x' } } }]
    })
  })

  test('variable dependency chain', () => {
    expect(
      normalizeMessage({
        decl: {
          a: { $: 'a' },
          b: { _: 'b', fn: 'fn', opt: { o: { $: 'a' } } },
          c: { $: 'b' },
          d: { $: 'c' },
          e: { $: 'a' },
          f: { $: 'e' }
        },
        msg: [{ $: 'd' }]
      })
    ).toEqual({
      decl: {
        a: { $: 'a' },
        b: { _: 'b', fn: 'fn', opt: { o: { $: 'a' } } },
        c: { $: 'b' },
        d: { $: 'c' }
      },
      msg: [{ $: 'd' }]
    })
  })

  test('SelectMessage', () => {
    expect(
      normalizeMessage({
        decl: { x: { _: 'x' }, y: { $: 'y' }, z: { $: 'z' } },
        sel: ['x'],
        alt: [
          { keys: ['a'], pat: [''] },
          { keys: [{ '*': '' }], pat: [{ $: 'y' }] }
        ]
      })
    ).toEqual({
      decl: { x: { _: 'x' }, y: { $: 'y' } },
      sel: ['x'],
      alt: [
        { keys: ['a'], pat: [] },
        { keys: [{ '*': '' }], pat: [{ $: 'y' }] }
      ]
    })
  })

  describe('input is not modified', () => {
    for (const msg of [
      ['x'],
      [''],
      { decl: { a: { $: 'a' } }, msg: ['', { $: 'a' }] },
      {
        decl: { x: { _: 'x' }, y: { $: 'y' }, z: { $: 'z' } },
        sel: ['x'],
        alt: [
          { keys: ['a'], pat: [''] },
          { keys: [{ '*': '' }], pat: [{ $: 'y' }] }
        ]
      }
    ] as Message[]) {
      test(JSON.stringify(msg), () => {
        const orig = structuredClone(msg)
        expect(normalizeMessage(msg)).not.toBe(msg)
        expect(msg).toEqual(orig)
      })
    }
  })
})
