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

export const ERROR_RESULT = '{�}'

export class ParseError extends Error {
  /** Set for fluent, mf2, and webext errors */
  range?: [number, number]

  constructor(message: string, start?: number, end?: number) {
    super(message)
    if (typeof start === 'number') this.range = [start, end ?? start + 1]
  }
}

export class SerializeError extends Error {
  /** Set for fluent, plain, and webext errors */
  pos?: number

  constructor(message: string, pos?: number) {
    super(message)
    if (typeof pos === 'number') this.pos = pos
  }
}
