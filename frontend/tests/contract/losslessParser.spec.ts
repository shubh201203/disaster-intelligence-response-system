import { test, expect } from '@playwright/test';
import {
  LosslessJSONParser,
  parseLosslessRecoveryResponse,
  normalizeOptimizationError,
} from '../../src/api/recoveryOptimization';
import {
  SolverOutcomeStatus,
  RecoveryOptimizationScenarioResponse,
} from '../../src/types/recoveryOptimization';

test.describe('Lossless JSON Parser & Response Normalization Contract Suite', () => {
  // ============================================================================
  // A. Numeric Precision
  // ============================================================================
  test.describe('A. Numeric Precision', () => {
    test('1. Backend test_12 value: 2^54 + 9999 preserved as exact string', () => {
      const input = '{"exact_objective_value": 18014398509491983}';
      const parsed = parseLosslessRecoveryResponse(input);
      expect(typeof parsed.exact_objective_value).toBe('string');
      expect(parsed.exact_objective_value).toBe('18014398509491983');
    });

    test('2. Positive integer greater than Number.MAX_SAFE_INTEGER preserved as exact string', () => {
      const input = '{"large_int": 9007199254740993}';
      const parsed = parseLosslessRecoveryResponse(input);
      expect(typeof parsed.large_int).toBe('string');
      expect(parsed.large_int).toBe('9007199254740993');
    });

    test('3. Negative integer below Number.MIN_SAFE_INTEGER preserved as exact string', () => {
      const input = '{"large_neg": -9007199254740993, "cash_balance_ccu": -9007199254740995}';
      const parsed = parseLosslessRecoveryResponse(input);
      expect(typeof parsed.large_neg).toBe('string');
      expect(parsed.large_neg).toBe('-9007199254740993');
      expect(typeof parsed.cash_balance_ccu).toBe('string');
      expect(parsed.cash_balance_ccu).toBe('-9007199254740995');
    });

    test('4. Positive safe-integer boundary (2^53 - 1 = 9007199254740991)', () => {
      // In Category 1 property, must be string. In generic property, remains number.
      const input = '{"total_cost_ccu": 9007199254740991, "safe_boundary": 9007199254740991}';
      const parsed = parseLosslessRecoveryResponse(input);
      expect(typeof parsed.total_cost_ccu).toBe('string');
      expect(parsed.total_cost_ccu).toBe('9007199254740991');
      expect(typeof parsed.safe_boundary).toBe('number');
      expect(parsed.safe_boundary).toBe(9007199254740991);
    });

    test('5. Negative safe-integer boundary (-(2^53 - 1) = -9007199254740991)', () => {
      const input = '{"cash_balance_ccu": -9007199254740991, "safe_neg_boundary": -9007199254740991}';
      const parsed = parseLosslessRecoveryResponse(input);
      expect(typeof parsed.cash_balance_ccu).toBe('string');
      expect(parsed.cash_balance_ccu).toBe('-9007199254740991');
      expect(typeof parsed.safe_neg_boundary).toBe('number');
      expect(parsed.safe_neg_boundary).toBe(-9007199254740991);
    });

    test('6. Zero value (0) handling in Category 1 vs generic fields', () => {
      const input = '{"total_cost_ccu": 0, "selected_project_count": 0}';
      const parsed = parseLosslessRecoveryResponse(input);
      expect(typeof parsed.total_cost_ccu).toBe('string');
      expect(parsed.total_cost_ccu).toBe('0');
      expect(typeof parsed.selected_project_count).toBe('number');
      expect(parsed.selected_project_count).toBe(0);
    });

    test('7. Ordinary safe integers parsed as standard JavaScript numbers', () => {
      const input = '{"duration_periods": 3, "selected_project_count": 500, "period": 120}';
      const parsed = parseLosslessRecoveryResponse(input);
      expect(typeof parsed.duration_periods).toBe('number');
      expect(parsed.duration_periods).toBe(3);
      expect(typeof parsed.selected_project_count).toBe('number');
      expect(parsed.selected_project_count).toBe(500);
      expect(typeof parsed.period).toBe('number');
      expect(parsed.period).toBe(120);
    });

    test('8. Decimal numeric tokens parsed or preserved accurately', () => {
      const input = '{"objective_value": 850000.5, "optimality_gap": 0.0001}';
      const parsed = parseLosslessRecoveryResponse(input);
      expect(typeof parsed.objective_value).toBe('number');
      expect(parsed.objective_value).toBe(850000.5);
      expect(typeof parsed.optimality_gap).toBe('number');
      expect(parsed.optimality_gap).toBe(0.0001);
    });

    test('9. Exponent notation parsed accurately', () => {
      const input = '{"scientific_val": 1.5e6, "small_val": 2.5e-3}';
      const parsed = parseLosslessRecoveryResponse(input);
      expect(typeof parsed.scientific_val).toBe('number');
      expect(parsed.scientific_val).toBe(1500000);
      expect(typeof parsed.small_val).toBe('number');
      expect(parsed.small_val).toBe(0.0025);
    });

    test('10. Invalid JSON number grammar throws SyntaxError', () => {
      const invalidNumbers = [
        '{"val": +5}',
        '{"val": 012}',
        '{"val": 1.}',
        '{"val": .5}',
        '{"val": 1e}',
        '{"val": --1}',
      ];
      for (const inv of invalidNumbers) {
        expect(() => parseLosslessRecoveryResponse(inv)).toThrow(SyntaxError);
      }
    });
  });

  // ============================================================================
  // B. JSON Structural Correctness
  // ============================================================================
  test.describe('B. JSON Structural Correctness', () => {
    test('11. Nested objects parsed with full structural fidelity', () => {
      const input = '{"level1": {"level2": {"level3": {"key": "val"}}}}';
      const parsed = parseLosslessRecoveryResponse(input);
      expect(parsed.level1.level2.level3.key).toBe('val');
    });

    test('12. Nested arrays parsed with element order preserved', () => {
      const input = '{"matrix": [[1, 2], [3, 4]], "tags": ["a", "b", "c"]}';
      const parsed = parseLosslessRecoveryResponse(input);
      expect(parsed.matrix).toEqual([[1, 2], [3, 4]]);
      expect(parsed.tags).toEqual(['a', 'b', 'c']);
    });

    test('13. Repeated keys across different nesting levels both preserved as Category 1', () => {
      const input = '{"cost_ccu": 100, "nested": {"cost_ccu": 200, "deep": {"cost_ccu": 300}}}';
      const parsed = parseLosslessRecoveryResponse(input);
      expect(parsed.cost_ccu).toBe('100');
      expect(parsed.nested.cost_ccu).toBe('200');
      expect(parsed.nested.deep.cost_ccu).toBe('300');
    });

    test('14. Numeric values inside Category 1 dictionary objects preserved as strings', () => {
      const input = JSON.stringify({
        district_equity_allocation_ccu: {
          'DIST-NORTH': 500000000,
          'DIST-SOUTH': 250000000,
        },
        periodic_expenditures_ccu: {
          '1': 166666666,
          '2': 166666667,
        },
      });
      const parsed = parseLosslessRecoveryResponse(input);
      expect(typeof parsed.district_equity_allocation_ccu['DIST-NORTH']).toBe('string');
      expect(parsed.district_equity_allocation_ccu['DIST-NORTH']).toBe('500000000');
      expect(parsed.district_equity_allocation_ccu['DIST-SOUTH']).toBe('250000000');
      expect(typeof parsed.periodic_expenditures_ccu['1']).toBe('string');
      expect(parsed.periodic_expenditures_ccu['1']).toBe('166666666');
      expect(parsed.periodic_expenditures_ccu['2']).toBe('166666667');
    });

    test('15. Escaped strings containing objective-like property names not parsed as numbers', () => {
      const input = '{"message": "Calculated \\"exact_objective_value\\": 18014398509491983 in solver"}';
      const parsed = parseLosslessRecoveryResponse(input);
      expect(typeof parsed.message).toBe('string');
      expect(parsed.message).toBe('Calculated "exact_objective_value": 18014398509491983 in solver');
    });

    test('16. Ordinary strings containing numeric-looking values preserved verbatim', () => {
      const input = '{"project_code": "PROJ-18014398509491983", "sha256": "1234567890abcdef"}';
      const parsed = parseLosslessRecoveryResponse(input);
      expect(typeof parsed.project_code).toBe('string');
      expect(parsed.project_code).toBe('PROJ-18014398509491983');
      expect(parsed.sha256).toBe('1234567890abcdef');
    });

    test('17. Unicode escape sequences unescaped accurately', () => {
      const input = '{"greeting": "\\u0048\\u0065\\u006c\\u006c\\u006f", "quote": "\\u0022"}';
      const parsed = parseLosslessRecoveryResponse(input);
      expect(parsed.greeting).toBe('Hello');
      expect(parsed.quote).toBe('"');
    });

    test('18. Null and boolean primitives preserved exactly', () => {
      const input = '{"flag_true": true, "flag_false": false, "empty_val": null}';
      const parsed = parseLosslessRecoveryResponse(input);
      expect(parsed.flag_true).toBe(true);
      expect(parsed.flag_false).toBe(false);
      expect(parsed.empty_val).toBeNull();
    });

    test('19. Whitespace variations handled conforming to RFC 8259', () => {
      const input = '  \t\r\n{\r\n  "key"  :  \t "value" \r\n}  \t\r\n';
      const parsed = parseLosslessRecoveryResponse(input);
      expect(parsed.key).toBe('value');
    });

    test('20. Trailing characters after root value throw SyntaxError', () => {
      const badInputs = [
        '{"valid": true} extra',
        '{"valid": true} 123',
        '{"valid": true} {}',
        '{"valid": true} ,',
      ];
      for (const bad of badInputs) {
        expect(() => parseLosslessRecoveryResponse(bad)).toThrow(SyntaxError);
      }
    });

    test('21. Unclosed strings and objects throw SyntaxError', () => {
      const unclosedInputs = [
        '{"unclosed_str": "val',
        '{"unclosed_obj": 1',
        '{"arr": [1, 2, 3',
        '{"key":',
      ];
      for (const bad of unclosedInputs) {
        expect(() => parseLosslessRecoveryResponse(bad)).toThrow(SyntaxError);
      }
    });

    test('22. Invalid escape sequences throw SyntaxError', () => {
      const badEscapes = [
        '{"bad": "\\x"}',
        '{"bad": "\\u00ZZ"}',
        '{"bad": "\\u12"}',
        '{"bad": "\\a"}',
      ];
      for (const bad of badEscapes) {
        expect(() => parseLosslessRecoveryResponse(bad)).toThrow(SyntaxError);
      }
    });
  });

  // ============================================================================
  // C. Solver Outcome Response Tests (All 6 Statuses)
  // ============================================================================
  test.describe('C. Solver Outcome Response Tests', () => {
    const statuses: SolverOutcomeStatus[] = [
      'OPTIMAL',
      'FEASIBLE',
      'INFEASIBLE',
      'UNKNOWN',
      'MODEL_INVALID',
      'POST_SOLVE_RECONCILIATION_FAILED',
    ];

    for (let i = 0; i < statuses.length; i++) {
      const status = statuses[i];
      const caseNum = 23 + i;
      test(`${caseNum}. Parses response with solver_status: ${status}`, () => {
        const payload: Partial<RecoveryOptimizationScenarioResponse> = {
          scenario_name: `Test ${status}`,
          solver_status: status,
          is_optimal: status === 'OPTIMAL',
          exact_objective_value: status === 'OPTIMAL' ? '850000000000' : null,
          total_cost_ccu: '500000000',
          total_cost_inr: '5000000.00',
          selected_project_count: status === 'OPTIMAL' || status === 'FEASIBLE' ? 1 : 0,
          solve_time_seconds: 0.15,
          scheduled_projects: [],
          periodic_solvency: [],
          district_equity_allocation_ccu: {},
          district_equity_allocation_inr: {},
          input_fingerprint_sha256: 'a'.repeat(64),
          ortools_version: '9.8.3296',
          solver_parameters: {},
          infeasibility_diagnostics: status === 'INFEASIBLE' ? {
            has_proven_infeasibility: true,
            proven_causes: [{
              category: 'MANDATORY_SAFETY',
              classification: 'PROVEN_CAUSE',
              message: 'Conflict',
              mathematical_condition: 'cond',
              affected_projects: ['P1'],
              conflicting_periods: [1],
              details: {},
            }],
            necessary_condition_violations: [],
            solver_hypotheses: [],
            warnings: [],
            is_assumption_core_minimal: true,
            is_assumption_core_sufficient: true,
          } : null,
        };

        const jsonStr = JSON.stringify(payload);
        const parsed = parseLosslessRecoveryResponse(jsonStr) as RecoveryOptimizationScenarioResponse;

        expect(parsed.solver_status).toBe(status);
        expect(parsed.is_optimal).toBe(status === 'OPTIMAL');
        expect(parsed.total_cost_ccu).toBe('500000000');
        expect(parsed.total_cost_inr).toBe('5000000.00');
        if (status === 'INFEASIBLE') {
          expect(parsed.infeasibility_diagnostics?.has_proven_infeasibility).toBe(true);
          expect(parsed.infeasibility_diagnostics?.proven_causes.length).toBe(1);
        }
      });
    }
  });

  // ============================================================================
  // D. Error Normalization
  // ============================================================================
  test.describe('D. Error Normalization', () => {
    test('29. Normalizes HTTP 401 Unauthorized', () => {
      const err = {
        isAxiosError: true,
        response: {
          status: 401,
          headers: {},
          data: { detail: 'Not authenticated' },
        },
      };
      const normalized = normalizeOptimizationError(err);
      expect(normalized.isOptimizationError).toBe(true);
      expect(normalized.status).toBe(401);
      expect(normalized.detail.error_type).toBe('INTERNAL_EXECUTION_FAILURE');
      expect(normalized.detail.message).toBe('Not authenticated');
    });

    test('30. Normalizes HTTP 403 Forbidden', () => {
      const err = {
        isAxiosError: true,
        response: {
          status: 403,
          headers: { 'x-correlation-id': 'auth-corr-403' },
          data: { detail: 'The user doesn\'t have enough privileges' },
        },
      };
      const normalized = normalizeOptimizationError(err);
      expect(normalized.isOptimizationError).toBe(true);
      expect(normalized.status).toBe(403);
      expect(normalized.correlationId).toBe('auth-corr-403');
      expect(normalized.detail.diagnostic_code).toBe('auth-corr-403');
    });

    test('31. Normalizes HTTP 422 RequestValidationError', () => {
      const err = {
        isAxiosError: true,
        response: {
          status: 422,
          headers: { 'x-correlation-id': 'val-corr-422' },
          data: {
            detail: [
              { loc: ['body', 'planning_horizon_periods'], msg: 'ensure this value is greater than 0' },
              { loc: ['body', 'candidates'], msg: 'field required' },
            ],
          },
        },
      };
      const normalized = normalizeOptimizationError(err);
      expect(normalized.isOptimizationError).toBe(true);
      expect(normalized.status).toBe(422);
      expect(normalized.detail.error_type).toBe('INVALID_REQUEST');
      expect(normalized.detail.validation_failures.length).toBe(2);
      expect(normalized.detail.validation_failures[0]).toContain('planning_horizon_periods');
      expect(normalized.correlationId).toBe('val-corr-422');
    });

    test('32. Normalizes HTTP 500 Internal Server Error', () => {
      const err = {
        isAxiosError: true,
        response: {
          status: 500,
          headers: {},
          data: { detail: 'Internal optimization solver error' },
        },
      };
      const normalized = normalizeOptimizationError(err);
      expect(normalized.isOptimizationError).toBe(true);
      expect(normalized.status).toBe(500);
      expect(normalized.detail.error_type).toBe('INTERNAL_EXECUTION_FAILURE');
      expect(normalized.detail.message).toBe('Internal optimization solver error');
    });

    test('33. Normalizes Timeout with ECONNABORTED to SOLVER_TIMEOUT', () => {
      const err = {
        isAxiosError: true,
        code: 'ECONNABORTED',
        message: 'timeout of 130000ms exceeded',
      };
      const normalized = normalizeOptimizationError(err);
      expect(normalized.isOptimizationError).toBe(true);
      expect(normalized.status).toBe(0);
      expect(normalized.detail.error_type).toBe('SOLVER_TIMEOUT');
      expect(normalized.detail.message).toContain('timed out');
    });

    test('34. Correlation ID extraction when present in headers', () => {
      const err = {
        isAxiosError: true,
        response: {
          status: 400,
          headers: { 'x-correlation-id': 'test-uuid-corr-1234' },
          data: { detail: 'Bad request' },
        },
      };
      const normalized = normalizeOptimizationError(err);
      expect(normalized.correlationId).toBe('test-uuid-corr-1234');
      expect(normalized.detail.diagnostic_code).toBe('test-uuid-corr-1234');
    });

    test('35. Correlation ID handling when absent from headers', () => {
      const err = {
        isAxiosError: true,
        response: {
          status: 500,
          headers: {},
          data: { detail: 'Error without correlation' },
        },
      };
      const normalized = normalizeOptimizationError(err);
      expect(normalized.correlationId).toBeNull();
      expect(normalized.detail.diagnostic_code).toBeNull();
    });

    test('36. Malformed or non-JSON HTML error body handled gracefully', () => {
      const err = {
        isAxiosError: true,
        message: 'Request failed with status code 502',
        response: {
          status: 502,
          headers: {},
          data: '<html><body>502 Bad Gateway</body></html>',
        },
      };
      const normalized = normalizeOptimizationError(err);
      expect(normalized.isOptimizationError).toBe(true);
      expect(normalized.status).toBe(502);
      expect(normalized.detail.error_type).toBe('INTERNAL_EXECUTION_FAILURE');
      expect(typeof normalized.detail.message).toBe('string');
    });
  });
});
