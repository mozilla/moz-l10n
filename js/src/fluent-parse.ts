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

import * as AST from '@fluent/syntax/esm/ast.js'
import {
  ParseError as FluentError,
  FluentParser
} from '@fluent/syntax/esm/index.js'
import { FluentParserStream } from '@fluent/syntax/esm/stream.js'

import { ParseError } from './errors.ts'
import type { Expression, Pattern } from './model.ts'

/**
 * Parses a string as a Fluent pattern, without any internal selectors.
 *
 * All whitespace outside placeables is considered significant.
 */
export function fluentParsePattern(
  src: string,
  onError: (error: ParseError) => void
): Pattern {
  const pattern: Pattern = []
  const ps = new FluentParserStream(src)
  let ch
  try {
    while ((ch = ps.currentChar())) {
      switch (ch) {
        case '{': {
          ps.next()
          ps.skipBlank()
          const expr = expression(ps)
          ps.skipBlank()
          if (ps.currentChar() === '-' && ps.peek() === '>') {
            // Not supporting selectors within patterns
            throw new FluentError('E0028')
          }
          ps.expectChar('}')
          pattern.push(expr)
          break
        }
        case '}':
          throw new FluentError('E0027')
        default: {
          let buffer = ''
          let ch
          while ((ch = ps.currentChar())) {
            if (ch === '{' || ch === '}') break
            buffer += ch
            ps.next()
          }
          pattern.push(buffer)
        }
      }
    }
  } catch (error) {
    const msg =
      error instanceof FluentError
        ? `fluent: ${error.message} (${error.code})`
        : `fluent: ${error}`
    onError(new ParseError(msg, ps.index, src.length))
    if (ps.index < src.length) pattern.push(src.substring(ps.index))
  }
  return pattern
}

function expression(ps: FluentParserStream): Expression {
  const fe = new FluentParser().getInlineExpression(ps)
  if (fe instanceof AST.NumberLiteral) return { _: fe.value, fn: 'number' }
  if (fe instanceof AST.StringLiteral) return { _: fe.parse().value }
  if (fe instanceof AST.VariableReference) return { $: fe.id.name }
  if (fe instanceof AST.MessageReference) {
    let name = fe.id.name
    if (fe.attribute) name += '.' + fe.attribute.name
    return { _: name, fn: 'message' }
  }
  if (fe instanceof AST.TermReference) {
    if (fe.attribute) throw new FluentError('E0019')
    const name = '-' + fe.id.name
    const expr: Expression = { _: name, fn: 'message' }
    if (fe.arguments?.named.length) {
      expr.opt = Object.create(null) as Record<string, string>
      for (const arg of fe.arguments.named) {
        expr.opt[arg.name.name] = arg.value.value
      }
    }
    return expr
  }
  if (fe instanceof AST.FunctionReference) {
    const name = fe.id.name.toLowerCase()
    const arg = fe.arguments.positional[0]
    let expr: Expression
    if (arg instanceof AST.BaseLiteral) {
      expr = { _: arg.value, fn: name }
    } else if (arg instanceof AST.VariableReference) {
      expr = { $: arg.id.name, fn: name }
    } else {
      expr = { fn: name }
    }
    if (fe.arguments?.named.length) {
      expr.opt = Object.create(null) as Record<string, string>
      for (const arg of fe.arguments.named) {
        expr.opt[arg.name.name] = arg.value.value
      }
    }
    return expr
  }
  throw new FluentError('E0028')
}
