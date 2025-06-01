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

import { ParseError } from './errors.ts'
import {
  isMarkup,
  type Expression,
  type Markup,
  type Pattern
} from './model.ts'

export const resoureRef = /^@(?:\w+:)?\w+\/\w+|\?(?:\w+:)?(\w+\/)?\w+$/

const _xmlEntities = new Set(['amp', 'lt', 'gt', 'apos', 'quot'])
let _xmlEntityKey = Math.floor(Math.random() * 1e9)

/** Matches `parse_pattern()` in `moz.l10n.formats.android.parse`. */
export function androidParsePattern(
  src: string,
  onError: (error: ParseError) => void
): Pattern {
  const entities: Record<string, string> = {}
  const safe = src.replace(/&([a-z][a-z0-9_]*);/gi, (match, name) => {
    if (_xmlEntities.has(name)) return match
    const key = `_entity_${++_xmlEntityKey}_`
    entities[key] = name
    return key
  })
  const doc = new DOMParser().parseFromString(
    `<string xmlns:xliff="urn:oasis:names:tc:xliff:document:1.2">${safe}</string>`,
    'text/xml'
  )
  const root = doc.querySelector('string')
  const error = doc.querySelector('parsererror')
  if (!root || error) {
    const errMsg = 'android: ' + (error?.textContent ?? 'XML parser error')
    onError(new ParseError(errMsg))
    return []
  }

  if (root.childElementCount === 0 && resoureRef.test(root.textContent ?? '')) {
    // https://developer.android.com/guide/topics/resources/providing-resources#ResourcesFromXml
    return [{ _: root.textContent!, fn: 'reference' }]
  }

  const pattern = Array.from(flattenElements(root))
  if (pattern.length > 0) {
    const part0 = pattern[0]
    if (typeof part0 === 'string') pattern[0] = part0.trimStart()
    const part1 = pattern.at(-1)
    // This will trim trailing spaces at the end of a text segment with an unpaired ".
    // We're presuming that this never happens intentionally.
    if (typeof part1 === 'string') pattern[pattern.length - 1] = part1.trimEnd()
  }
  const spaced = parseQuotes(pattern)
  return Array.from(parseInline(spaced, entities))
}

function* flattenElements(
  root: Element
): Iterable<string | Expression | Markup> {
  // @ts-expect-error No, TS, it _is_ iterable.
  for (const node of root.childNodes as Iterable<ChildNode>) {
    if (node instanceof Text) {
      if (node.textContent) yield node.textContent
      continue
    }
    if (!(node instanceof Element)) {
      throw Error(`Unsupported node type ${node.nodeType}`)
    }

    let opt: Record<string, string> | undefined = undefined
    if (node.hasAttributes()) {
      opt = Object.create(null) as Record<string, string>
      // @ts-expect-error No, TS, it _is_ iterable.
      for (const attr of node.attributes as Iterable<Attr>) {
        opt[attr.name] = attr.value
      }
    }
    const body = Array.from(flattenElements(node))
    if (node.tagName === 'xliff:g') {
      if (
        body.some(
          (part) =>
            isMarkup(part) ||
            (typeof part !== 'string' && part.attr?.translate === 'no')
        )
      ) {
        // Any <xliff:g> around elements needs to be rendered explicitly
        yield { open: 'xliff:g', opt, attr: noTranslateAttr() }
        yield* body
        yield { close: 'xliff:g', attr: noTranslateAttr() }
      } else {
        const id = node.getAttribute('id')
        for (const part of body) {
          if (typeof part === 'string') {
            let expr: Expression
            const attr = noTranslateAttr()
            if (id) {
              attr.source = part
              expr = { $: varName(id), attr }
            } else if (part.startsWith('%') || part.startsWith('{')) {
              attr.source = part
              expr = { $: varName(part), attr }
            } else {
              expr = { _: part, attr }
            }
            if (opt) {
              expr.fn = 'xliff:g'
              expr.opt = opt
            }
            yield expr
          } else {
            part.attr = noTranslateAttr(part.attr)
            if (opt) part.opt = Object.assign(Object.create(null), opt)
            yield part
          }
        }
      }
    } else {
      yield { open: node.tagName, opt }
      yield* body
      yield { close: node.tagName }
    }
  }
}

const _noTranslate = { translate: 'no' }
const noTranslateAttr = (attr?: Record<string, string | true>) =>
  Object.assign(attr ?? Object.create(null), _noTranslate)

function* parseQuotes(
  pattern: Iterable<string | Expression | Markup>
): Iterable<string | Expression | Markup> {
  let quoted = false
  for (const part of pattern) {
    if (typeof part === 'string') {
      let pos = 0
      for (const m of part.matchAll(/(?<!\\)"/g)) {
        if (pos === 0 && /<.+>/.test(part)) {
          // Let's presume that double quotes near html-ish contents are intentional.
          break
        }
        const prev = part.substring(pos, m.index)
        if (prev) yield quoted ? prev : prev.replace(/\s+/g, ' ')
        pos = m.index + m[0].length
        quoted = !quoted
      }
      const last = part.substring(pos)
      if (last) yield quoted ? last : last.replace(/\s+/g, ' ')
    } else {
      if (isMarkup(part) || part.attr?.translate === 'no') {
        quoted = false
      }
      yield part
    }
  }
}

const _inline =
  // 1:esc-unicode     2:esc-char       4:printf
  //                         3:esc-elem                                5:printf-conversion             6:xml-entity
  /\\u([0-9A-Fa-f]{4})|\\(.)|(<[^%>]+>)|(%(?:[1-9]\$)?[-#+ 0,(]?[0-9.]*([a-su-zA-SU-Z%]|[tT][a-zA-Z]))|(_entity_\d+_)/g

function* parseInline(
  pattern: Iterable<string | Expression | Markup>,
  entities: Record<string, string>
): Iterable<string | Expression | Markup> {
  let buffer = ''
  for (const part of pattern) {
    if (typeof part === 'string') {
      let pos = 0
      for (const m of part.matchAll(_inline)) {
        if (m.index > pos) buffer += part.substring(pos, m.index)
        pos = m.index + m[0].length
        if (m[1]) {
          buffer += String.fromCharCode(parseInt(m[1], 16))
        } else if (m[2]) {
          const ch = m[2]
          buffer += ch === 'n' ? '\n' : ch === 't' ? '\t' : ch
        } else {
          if (buffer) {
            yield buffer
            buffer = ''
          }
          if (m[3]) {
            yield { _: m[3], fn: 'html' }
          } else if (m[4]) {
            const attr = Object.create(null)
            attr.source = m[0]
            let fn: string | undefined = undefined
            switch (m[5]) {
              case '%':
                yield { _: '%', attr }
                continue // for
              case 'b':
              case 'B':
                fn = 'boolean'
                break
              case 'c':
              case 'C':
              case 's':
              case 'S':
                fn = 'string'
                break
              case 'd':
              case 'h':
              case 'H':
              case 'o':
              case 'x':
              case 'X':
                fn = 'integer'
                break
              case 'a':
              case 'A':
              case 'e':
              case 'E':
              case 'f':
              case 'g':
              case 'G':
                fn = 'number'
                break
              default:
                if (m[5][0].toLowerCase() === 't') fn = 'datetime'
            }
            yield { $: varName(m[4]), fn, attr }
          } else {
            yield { $: entities[m[6]] ?? 'UNKNOWN', fn: 'entity' }
          }
        }
      }
      if (pos < part.length) buffer += part.substring(pos)
    } else {
      if (buffer) {
        yield buffer
        buffer = ''
      }
      yield part
    }
  }
  if (buffer) yield buffer
}

// Exclude : for compatibility with MF2
const _notNameStart =
  /^[^A-Z_a-z\xC0-\xD6\xD8-\xF6\xF8-\u02FF\u0370-\u037D\u037F-\u1FFF\u200C-\u200D\u2070-\u218F\u2C00-\u2FEF\u3001-\uD7FF\uF900-\uFDCF\uFDF0-\uFFFD\u{010000}-\u{0EFFFF}]/u
const _notNameChar = new RegExp(
  // eslint-disable-next-line no-misleading-character-class
  _notNameStart.source.slice(1, -1) +
    '.0-9\\xB7\\u0300-\\u036F\\u203F-\\u2040]',
  'gu'
)

/** Returns a valid MF2 name */
function varName(src: string): string {
  const printf = src.match(/^%([1-9]\$)?/)
  if (printf) return printf[1] ? `arg${printf[1][0]}` : 'arg'
  let name = src.replace(_notNameChar, '')
  if (_notNameStart.test(name)) name = name.substring(1)
  return name || 'arg'
}
