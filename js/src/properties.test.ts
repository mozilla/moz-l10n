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

import { SerializeError } from './errors.ts'
import { propertiesParsePattern } from './properties-parse.ts'
import { propertiesSerializePattern } from './properties-serialize.ts'

test('multiple parts', () => {
  const src = propertiesSerializePattern(['foo', ' ', 'bar'])
  expect(src).toBe('foo bar')
  const res = propertiesParsePattern(src)
  expect(res).toEqual(['foo bar'])
})

test('special characters', () => {
  const src = propertiesSerializePattern(['foo\n\tbar'])
  expect(src).toBe('foo\\n\\tbar')
  const res = propertiesParsePattern(src)
  expect(res).toEqual(['foo\n\tbar'])
})

test('outer whitespace', () => {
  const src = propertiesSerializePattern(['  foo  '])
  expect(src).toBe('\\  foo \\u0020')
  const res = propertiesParsePattern(src)
  expect(res).toEqual(['  foo  '])
})

test('placeholder', () => {
  const src = propertiesSerializePattern([
    'Hello ',
    { $: 'world', attr: { source: '%s' } }
  ])
  expect(src).toBe('Hello %s')
  const res = propertiesParsePattern(src)
  expect(res).toEqual(['Hello %s'])
})

test('unsupported pattern part', () => {
  const onError = vi.fn()
  const src = propertiesSerializePattern(
    ['Hello ', { _: 'world' }, '?'],
    onError
  )
  expect(onError).toHaveBeenCalled()
  const error = onError.mock.calls[0][0]
  expect(error).toBeInstanceOf(SerializeError)
  expect(error.message).toBe(
    'properties: Unsupported pattern part {"_":"world"}'
  )
  expect(error.pos).toBe(6)
  expect(src).toBe('Hello {�}?')
})
