/**
 * DIRS Phase 6D-B Milestone 4 Gate 1: Frontend API Client Layer
 * Recovery Portfolio Optimization API integration and lossless numerical parser.
 *
 * Implements:
 * 1. Lossless RFC 8259 JSON parser preserving 64-bit integers and monetary decimals.
 * 2. evaluateRecoveryOptimizationScenario() caller with timeout and correlation tracking.
 * 3. normalizeOptimizationError() error normalizer producing typed OptimizationApiError.
 */

import axios, { AxiosError } from 'axios';
import { apiClient } from './client';
import {
  RecoveryOptimizationScenarioRequest,
  RecoveryOptimizationScenarioResponse,
  EvaluatedScenarioResult,
  OptimizationApiError,
  OptimizationErrorDetailDTO,
  OptimizationErrorType,
} from '../types/recoveryOptimization';

// ==============================================================================
// 1. Lossless RFC 8259 JSON Parser
// ==============================================================================

const CATEGORY_1_KEYS = new Set([
  'exact_objective_value',
  'exact_best_bound',
  'conservative_best_bound',
  'total_cost_ccu',
  'cost_ccu',
  'revenue_receipt_ccu',
  'expenditure_ccu',
  'cash_balance_ccu',
]);

const CATEGORY_1_DICT_KEYS = new Set([
  'district_equity_allocation_ccu',
  'periodic_expenditures_ccu',
]);

const MAX_SAFE_INTEGER_BIGINT = BigInt(9007199254740991); // 2^53 - 1
const MIN_SAFE_INTEGER_BIGINT = BigInt(-9007199254740991);

/**
 * Structural RFC 8259 compliant JSON parser that preserves Category 1 64-bit integers
 * and any integer exceeding IEEE-754 safe integer limits as exact decimal strings.
 */
export class LosslessJSONParser {
  private readonly text: string;
  private readonly len: number;
  private pos: number;

  constructor(text: string) {
    this.text = text;
    this.len = text.length;
    this.pos = 0;
  }

  public static parse(text: string): any {
    if (typeof text !== 'string' || text.trim().length === 0) {
      throw new SyntaxError('Unexpected empty or non-string JSON input');
    }
    const parser = new LosslessJSONParser(text);
    const result = parser.parseValue('', null);
    parser.skipWhitespace();
    if (parser.pos < parser.len) {
      throw new SyntaxError(
        `Unexpected token '${parser.text[parser.pos]}' at position ${parser.pos} after root JSON element`
      );
    }
    return result;
  }

  private skipWhitespace(): void {
    while (this.pos < this.len) {
      const ch = this.text.charCodeAt(this.pos);
      if (ch === 0x20 || ch === 0x09 || ch === 0x0a || ch === 0x0d) {
        this.pos++;
      } else {
        break;
      }
    }
  }

  private peek(): string {
    return this.pos < this.len ? this.text[this.pos] : '';
  }

  private parseValue(currentKey: string, parentKey: string | null): any {
    this.skipWhitespace();
    if (this.pos >= this.len) {
      throw new SyntaxError('Unexpected end of JSON input');
    }

    const ch = this.text[this.pos];

    if (ch === '{') return this.parseObject(currentKey);
    if (ch === '[') return this.parseArray(currentKey);
    if (ch === '"') return this.parseString();
    if (ch === 't' || ch === 'f') return this.parseBoolean();
    if (ch === 'n') return this.parseNull();
    if (ch === '-' || (ch >= '0' && ch <= '9')) {
      return this.parseNumber(currentKey, parentKey);
    }

    throw new SyntaxError(
      `Unexpected character '${ch}' at position ${this.pos}`
    );
  }

  private parseObject(objectKey: string): Record<string, any> {
    this.pos++; // Skip '{'
    const obj: Record<string, any> = {};
    this.skipWhitespace();

    if (this.peek() === '}') {
      this.pos++; // Empty object
      return obj;
    }

    while (this.pos < this.len) {
      this.skipWhitespace();
      if (this.peek() !== '"') {
        throw new SyntaxError(
          `Expected string key in object at position ${this.pos}`
        );
      }
      const key = this.parseString();
      this.skipWhitespace();
      if (this.peek() !== ':') {
        throw new SyntaxError(
          `Expected ':' after key at position ${this.pos}`
        );
      }
      this.pos++; // Skip ':'

      const val = this.parseValue(key, objectKey);
      obj[key] = val;

      this.skipWhitespace();
      const next = this.peek();
      if (next === '}') {
        this.pos++; // End of object
        return obj;
      }
      if (next === ',') {
        this.pos++; // Skip ',' and continue
      } else {
        throw new SyntaxError(
          `Expected ',' or '}' in object at position ${this.pos}`
        );
      }
    }

    throw new SyntaxError(`Unterminated object at position ${this.pos}`);
  }

  private parseArray(parentKey: string | null): any[] {
    this.pos++; // Skip '['
    const arr: any[] = [];
    this.skipWhitespace();

    if (this.peek() === ']') {
      this.pos++; // Empty array
      return arr;
    }

    while (this.pos < this.len) {
      const val = this.parseValue('', parentKey);
      arr.push(val);

      this.skipWhitespace();
      const next = this.peek();
      if (next === ']') {
        this.pos++; // End of array
        return arr;
      }
      if (next === ',') {
        this.pos++; // Skip ',' and continue
      } else {
        throw new SyntaxError(
          `Expected ',' or ']' in array at position ${this.pos}`
        );
      }
    }

    throw new SyntaxError(`Unterminated array at position ${this.pos}`);
  }

  private parseString(): string {
    this.pos++; // Skip opening '"'
    let result = '';
    let start = this.pos;

    while (this.pos < this.len) {
      const code = this.text.charCodeAt(this.pos);

      // RFC 8259 §9: Unescaped control characters U+0000 through U+001F are not permitted
      if (code < 0x20) {
        throw new SyntaxError(
          `Unescaped control character (0x${code.toString(16)}) at position ${this.pos}`
        );
      }

      if (code === 0x22) {
        // Closing '"'
        result += this.text.slice(start, this.pos);
        this.pos++;
        return result;
      }

      if (code === 0x5c) {
        // Escape sequence '\'
        result += this.text.slice(start, this.pos);
        this.pos++;
        if (this.pos >= this.len) {
          throw new SyntaxError(
            `Unterminated escape sequence at position ${this.pos}`
          );
        }

        const esc = this.text[this.pos];
        if (esc === '"') result += '"';
        else if (esc === '\\') result += '\\';
        else if (esc === '/') result += '/';
        else if (esc === 'b') result += '\b';
        else if (esc === 'f') result += '\f';
        else if (esc === 'n') result += '\n';
        else if (esc === 'r') result += '\r';
        else if (esc === 't') result += '\t';
        else if (esc === 'u') {
          if (this.pos + 4 >= this.len) {
            throw new SyntaxError(
              `Incomplete unicode escape sequence at position ${this.pos}`
            );
          }
          const hex = this.text.slice(this.pos + 1, this.pos + 5);
          if (!/^[0-9a-fA-F]{4}$/.test(hex)) {
            throw new SyntaxError(
              `Invalid unicode escape sequence '\\u${hex}' at position ${this.pos}`
            );
          }
          result += String.fromCharCode(parseInt(hex, 16));
          this.pos += 4;
        } else {
          throw new SyntaxError(
            `Invalid escape character '\\${esc}' at position ${this.pos}`
          );
        }

        this.pos++;
        start = this.pos;
      } else {
        this.pos++;
      }
    }

    throw new SyntaxError(`Unterminated string starting at position ${start}`);
  }

  private parseBoolean(): boolean {
    if (this.text.startsWith('true', this.pos)) {
      this.pos += 4;
      return true;
    }
    if (this.text.startsWith('false', this.pos)) {
      this.pos += 5;
      return false;
    }
    throw new SyntaxError(
      `Invalid boolean token at position ${this.pos}`
    );
  }

  private parseNull(): null {
    if (this.text.startsWith('null', this.pos)) {
      this.pos += 4;
      return null;
    }
    throw new SyntaxError(
      `Invalid null token at position ${this.pos}`
    );
  }

  private parseNumber(currentKey: string, parentKey: string | null): number | string {
    const start = this.pos;

    // Optional leading minus
    if (this.text[this.pos] === '-') {
      this.pos++;
    }

    if (this.pos >= this.len) {
      throw new SyntaxError(`Invalid number at position ${start}`);
    }

    // Integer component (no leading zero unless number is 0)
    if (this.text[this.pos] === '0') {
      this.pos++;
    } else if (this.text[this.pos] >= '1' && this.text[this.pos] <= '9') {
      while (
        this.pos < this.len &&
        this.text[this.pos] >= '0' &&
        this.text[this.pos] <= '9'
      ) {
        this.pos++;
      }
    } else {
      throw new SyntaxError(
        `Invalid number leading digit at position ${this.pos}`
      );
    }

    let isFloat = false;

    // Optional fractional component
    if (this.pos < this.len && this.text[this.pos] === '.') {
      isFloat = true;
      this.pos++;
      if (
        this.pos >= this.len ||
        !(this.text[this.pos] >= '0' && this.text[this.pos] <= '9')
      ) {
        throw new SyntaxError(
          `Invalid fractional digit at position ${this.pos}`
        );
      }
      while (
        this.pos < this.len &&
        this.text[this.pos] >= '0' &&
        this.text[this.pos] <= '9'
      ) {
        this.pos++;
      }
    }

    // Optional exponent component
    if (
      this.pos < this.len &&
      (this.text[this.pos] === 'e' || this.text[this.pos] === 'E')
    ) {
      isFloat = true;
      this.pos++;
      if (
        this.pos < this.len &&
        (this.text[this.pos] === '+' || this.text[this.pos] === '-')
      ) {
        this.pos++;
      }
      if (
        this.pos >= this.len ||
        !(this.text[this.pos] >= '0' && this.text[this.pos] <= '9')
      ) {
        throw new SyntaxError(
          `Invalid exponent digit at position ${this.pos}`
        );
      }
      while (
        this.pos < this.len &&
        this.text[this.pos] >= '0' &&
        this.text[this.pos] <= '9'
      ) {
        this.pos++;
      }
    }

    const token = this.text.slice(start, this.pos);

    // Determine numerical category
    const isCategory1 =
      CATEGORY_1_KEYS.has(currentKey) ||
      (parentKey !== null && CATEGORY_1_DICT_KEYS.has(parentKey));

    if (!isFloat) {
      try {
        const bi = BigInt(token);
        if (
          isCategory1 ||
          bi > MAX_SAFE_INTEGER_BIGINT ||
          bi < MIN_SAFE_INTEGER_BIGINT
        ) {
          return token;
        }
      } catch {
        return token;
      }
    } else if (isCategory1) {
      // In case Category 1 field was formatted with decimal notation
      return token;
    }

    return Number(token);
  }
}

/**
 * Lossless JSON parsing function for recovery optimization responses.
 */
export function parseLosslessRecoveryResponse(rawJsonText: string): any {
  return LosslessJSONParser.parse(rawJsonText);
}

// ==============================================================================
// 2. Error Normalization
// ==============================================================================

/**
 * Normalizes any error caught during scenario evaluation into a strongly-typed
 * OptimizationApiError contract with correlation tracking.
 */
export function normalizeOptimizationError(error: unknown): OptimizationApiError {
  if (axios.isAxiosError(error)) {
    const axiosErr = error as AxiosError<any>;
    const status = axiosErr.response?.status || 0;
    const headers = axiosErr.response?.headers;
    const correlationId =
      headers?.['x-correlation-id'] ||
      headers?.['X-Correlation-ID'] ||
      null;

    let responseData = axiosErr.response?.data;

    // If response body is unparsed string, attempt lossless parse
    if (typeof responseData === 'string' && responseData.trim().length > 0) {
      try {
        responseData = parseLosslessRecoveryResponse(responseData);
      } catch {
        // Fallback to raw string if not JSON
      }
    }

    if (responseData && typeof responseData === 'object') {
      const detail = responseData.detail;

      if (detail && typeof detail === 'object' && !Array.isArray(detail)) {
        // Structured OptimizationErrorDetailDTO from backend
        return {
          isOptimizationError: true,
          status,
          correlationId: correlationId ? String(correlationId) : null,
          detail: {
            error_type:
              detail.error_type ||
              (status === 422 ? 'INVALID_REQUEST' : 'INTERNAL_EXECUTION_FAILURE'),
            message: detail.message || axiosErr.message || 'Optimization request failed',
            diagnostic_code:
              detail.diagnostic_code || (correlationId ? String(correlationId) : null),
            validation_failures: Array.isArray(detail.validation_failures)
              ? detail.validation_failures
              : [],
            input_fingerprint_sha256: detail.input_fingerprint_sha256 || null,
            infeasibility_diagnostics: detail.infeasibility_diagnostics || null,
          },
        };
      }

      if (typeof detail === 'string') {
        // Standard FastAPI HTTPException with string detail
        return {
          isOptimizationError: true,
          status,
          correlationId: correlationId ? String(correlationId) : null,
          detail: {
            error_type:
              status === 422 || status === 400
                ? 'INVALID_REQUEST'
                : 'INTERNAL_EXECUTION_FAILURE',
            message: detail,
            diagnostic_code: correlationId ? String(correlationId) : null,
            validation_failures: [],
            input_fingerprint_sha256: null,
            infeasibility_diagnostics: null,
          },
        };
      }

      if (Array.isArray(detail)) {
        // Standard FastAPI 422 RequestValidationError
        const validationFailures = detail.map((d: any) =>
          d.loc ? `${d.loc.join('.')}: ${d.msg || ''}` : JSON.stringify(d)
        );
        return {
          isOptimizationError: true,
          status,
          correlationId: correlationId ? String(correlationId) : null,
          detail: {
            error_type: 'INVALID_REQUEST',
            message: detail.map((d: any) => d.msg || JSON.stringify(d)).join('; '),
            diagnostic_code: correlationId ? String(correlationId) : null,
            validation_failures: validationFailures,
            input_fingerprint_sha256: null,
            infeasibility_diagnostics: null,
          },
        };
      }
    }

    // Network timeout or connectivity failure
    const isTimeout =
      axiosErr.code === 'ECONNABORTED' ||
      axiosErr.message?.toLowerCase().includes('timeout');

    return {
      isOptimizationError: true,
      status,
      correlationId: correlationId ? String(correlationId) : null,
      detail: {
        error_type: isTimeout ? 'SOLVER_TIMEOUT' : 'INTERNAL_EXECUTION_FAILURE',
        message: isTimeout
          ? 'Optimization evaluation request timed out'
          : axiosErr.message || 'Network error or service unavailable',
        diagnostic_code: correlationId ? String(correlationId) : null,
        validation_failures: [],
        input_fingerprint_sha256: null,
        infeasibility_diagnostics: null,
      },
    };
  }

  // Non-Axios generic error
  const genericMessage =
    error instanceof Error ? error.message : String(error);

  return {
    isOptimizationError: true,
    status: 500,
    correlationId: null,
    detail: {
      error_type: 'INTERNAL_EXECUTION_FAILURE',
      message: genericMessage,
      diagnostic_code: null,
      validation_failures: [],
      input_fingerprint_sha256: null,
      infeasibility_diagnostics: null,
    },
  };
}

// ==============================================================================
// 3. API Caller Function
// ==============================================================================

/**
 * Evaluates a recovery portfolio optimization scenario via the accepted Gate 2 backend API.
 * Uses lossless JSON parsing for IEEE-754 64-bit integer preservation and extracts correlation IDs.
 *
 * @param request Complete recovery optimization scenario request payload.
 * @returns Evaluated scenario result containing the response payload and correlation ID.
 * @throws OptimizationApiError on any request, network, or server error.
 */
export async function evaluateRecoveryOptimizationScenario(
  request: RecoveryOptimizationScenarioRequest
): Promise<EvaluatedScenarioResult> {
  try {
    const response = await apiClient.post<RecoveryOptimizationScenarioResponse>(
      '/recovery/optimization/evaluate',
      request,
      {
        timeout: 130000, // 130s client timeout (> 120s server cap)
        headers: {
          'Content-Type': 'application/json',
          Accept: 'application/json',
        },
        responseType: 'text',
        transformResponse: [
          (data: any) => {
            if (typeof data === 'string' && data.trim().length > 0) {
              return parseLosslessRecoveryResponse(data);
            }
            return data;
          },
        ],
      }
    );

    const headers = response.headers;
    const correlationId =
      headers?.['x-correlation-id'] ||
      headers?.['X-Correlation-ID'] ||
      null;

    return {
      data: response.data,
      correlationId: correlationId ? String(correlationId) : null,
    };
  } catch (err: unknown) {
    throw normalizeOptimizationError(err);
  }
}
