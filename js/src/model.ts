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

/** Matches /schemas/message.json and /schemas/entry.json */

export type Entry = {
  /** comment */
  '#'?: string

  /** metadata */
  '@'?: Metadata

  /** message */
  '='?: Message

  /** properties */
  '+'?: Record<string, Message>
} & ({ '=': Message } | { '+': Record<string, Message> })

export type Metadata = [
  [key: string, value: string],
  ...[key: string, value: string][]
]

export type Message = Pattern | PatternMessage | SelectMessage

export type Pattern = (string | Expression | Markup)[]

export type Expression = {
  _?: string
  $?: string
  fn?: string
  opt?: Record<string, string | { $: string }>
  attr?: Record<string, string | true>
  open?: never
  close?: never
  elem?: never
} & (
  | { _: string; $?: never }
  | { _?: never; $: string }
  | { _?: never; $?: never; fn: string }
)

export type Markup = {
  open?: string
  close?: string
  elem?: string
  opt?: Record<string, string | { $: string }>
  attr?: Record<string, string | true>
  _?: never
  $?: never
  fn?: never
} & (
  | { open: string; close?: never; elem?: never }
  | { open?: never; close: string; elem?: never }
  | { open?: never; close?: never; elem: string }
)

export interface PatternMessage {
  decl: Record<string, Expression>
  msg: Pattern
}

export interface SelectMessage {
  decl: Record<string, Expression>
  msg?: never
  sel: string[]
  alt: {
    keys: (string | CatchallKey)[]
    pat: Pattern
  }[]
}

export type CatchallKey = { '*': string }

export const isExpression = (
  x: string | Expression | Markup
): x is Expression =>
  typeof x !== 'string' && ('_' in x || '$' in x || 'fn' in x)

export const isMarkup = (x: string | Expression | Markup): x is Markup =>
  typeof x !== 'string' && ('open' in x || 'close' in x || 'elem' in x)
