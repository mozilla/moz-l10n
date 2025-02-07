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

import { androidParsePattern } from './android-parse.ts'
import { androidSerializePattern } from './android-serialize.ts'
import { ParseError, SerializeError } from './errors.js'
import { fluentParsePattern } from './fluent-parse.ts'
import { fluentSerializePattern } from './fluent-serialize.ts'
import { mf2ParsePattern } from './mf2-parse.ts'
import { mf2SerializePattern } from './mf2-serialize.ts'
import type { Message, Pattern } from './model.ts'
import { webextParsePattern } from './webext-parse.ts'
import { webextSerializePattern } from './webext-serialize.ts'
import { xliffParsePattern } from './xliff-parse.ts'
import { xliffSerializePattern } from './xliff-serialize.ts'

export {
  isExpression,
  isMarkup,
  type Expression,
  type Markup,
  type Message,
  type Pattern,
  type PatternMessage,
  type SelectMessage
} from './model.ts'

export {
  androidParsePattern,
  androidSerializePattern,
  fluentParsePattern,
  fluentSerializePattern,
  ParseError,
  SerializeError,
  webextParsePattern,
  webextSerializePattern,
  xliffParsePattern,
  xliffSerializePattern
}

export type FormatKey =
  | 'android'
  | 'fluent'
  | 'mf2'
  | 'plain'
  | 'webext'
  | 'xliff'

/**
 * Parse the string representation of a single flat message pattern into a data structure.
 *
 * JSON Schema: https://github.com/mozilla/moz-l10n/blob/main/moz/l10n/message/schema.json
 *
 * @param baseMsg - Required by `webext` for named placeholders.
 * @param onError - If undefined, errors are thrown.
 */
export function parsePattern(
  format: FormatKey,
  src: string,
  baseMsg?: Message,
  onError?: (error: ParseError) => void
): Pattern {
  onError ??= (error) => {
    throw error
  }
  switch (format) {
    case 'android':
      return androidParsePattern(src, onError)
    case 'fluent':
      return fluentParsePattern(src, onError)
    case 'mf2':
      return mf2ParsePattern(src, onError)
    case 'webext':
      return webextParsePattern(baseMsg ?? [], src, onError)
    case 'xliff':
      return xliffParsePattern(src, onError)
    case 'plain':
      return [src]
    default:
      onError(new ParseError(`${format}: Unsupported format`))
      return [src]
  }
}

/**
 * Serialise the data representation of a single flat message pattern into a string.
 *
 * JSON Schema: https://github.com/mozilla/moz-l10n/blob/main/moz/l10n/message/schema.json
 *
 * @param onError - If undefined, errors are thrown.
 */
export function serializePattern(
  format: FormatKey,
  pattern: Pattern,
  onError?: (error: SerializeError) => void
): string {
  onError ??= (error) => {
    throw error
  }
  switch (format) {
    case 'android':
      return androidSerializePattern(pattern, onError)
    case 'fluent':
      return fluentSerializePattern(pattern, onError)
    case 'mf2':
      return mf2SerializePattern(pattern)
    case 'webext':
      return webextSerializePattern(pattern, onError)
    case 'xliff':
      return xliffSerializePattern(pattern, onError)
    case 'plain':
      break
    default:
      onError(new SerializeError(`${format}: Unsupported format`))
  }
  let res = ''
  for (const part of pattern) {
    if (typeof part === 'string') res += part
    else {
      const error = `${format}: Unsupported pattern part: ${JSON.stringify(part)}`
      onError(new SerializeError(error, res.length))
      res += '{�}'
    }
  }
  return res
}
