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
