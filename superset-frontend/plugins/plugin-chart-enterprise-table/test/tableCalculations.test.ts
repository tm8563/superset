/**
 * Licensed to the Apache Software Foundation (ASF) under one
 * or more contributor license agreements.  See the NOTICE file
 * distributed with this work for additional information
 * regarding copyright ownership.  The ASF licenses this file
 * to you under the Apache License, Version 2.0 (the
 * "License"); you may not use this file except in compliance
 * with the License.  You may obtain a copy of the License at
 *
 *   http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing,
 * software distributed under the License is distributed on an
 * "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY
 * KIND, either express or implied.  See the License for the
 * specific language governing permissions and limitations
 * under the License.
 */

import {
  applyTableCalculations,
  getCalculatedColumnKey,
  getCalculatedColumnLabel,
  isValidNumber,
} from '../src/tableCalculations';
import { EnterpriseTableColumn, TableCalculationConfig } from '../src/types';

describe('Table Calculations Engine', () => {
  const sampleColumns: EnterpriseTableColumn[] = [
    { key: 'region', label: 'Region', isMetric: false, dataType: 'string' },
    { key: 'sales', label: 'Sales', isMetric: true, dataType: 'number', minValue: 100, maxValue: 300 },
    { key: 'profit', label: 'Profit', isMetric: true, dataType: 'number', minValue: 20, maxValue: 80 },
  ];

  const sampleData = [
    { region: 'North America', sales: 100, profit: 20 },
    { region: 'EMEA', sales: 200, profit: 50 },
    { region: 'APAC', sales: 300, profit: 80 },
  ];

  test('isValidNumber helper validates numbers and filters invalid values', () => {
    expect(isValidNumber(100)).toBe(true);
    expect(isValidNumber(0)).toBe(true);
    expect(isValidNumber(-50.5)).toBe(true);
    expect(isValidNumber(NaN)).toBe(false);
    expect(isValidNumber(Infinity)).toBe(false);
    expect(isValidNumber(null)).toBe(false);
    expect(isValidNumber(undefined)).toBe(false);
    expect(isValidNumber('100')).toBe(false);
  });

  describe('1. Percent of Total', () => {
    test('computes Percent of Column Total correctly and sums to 100%', () => {
      const calc: TableCalculationConfig = {
        column: 'sales',
        type: 'percent_of_total',
        basis: 'column',
      };
      const result = applyTableCalculations(sampleData, sampleColumns, [calc]);
      expect(result.calculatedColumns).toHaveLength(1);

      const calcKey = result.calculatedColumns[0].key;
      const pctValues = result.data.map(r => r[calcKey] as number);

      // 100 / 600 = 16.666..., 200 / 600 = 33.333..., 300 / 600 = 50%
      expect(pctValues[0]).toBeCloseTo(16.6667, 3);
      expect(pctValues[1]).toBeCloseTo(33.3333, 3);
      expect(pctValues[2]).toBeCloseTo(50.0, 3);

      const sum = pctValues.reduce((a, b) => a + b, 0);
      expect(sum).toBeCloseTo(100, 5);
    });

    test('computes Percent of Row Total across metric columns', () => {
      const calc: TableCalculationConfig = {
        column: 'sales',
        type: 'percent_of_total',
        basis: 'row',
      };
      const result = applyTableCalculations(sampleData, sampleColumns, [calc]);
      const calcKey = result.calculatedColumns[0].key;
      // Row 0: sales 100, profit 20 => total 120 => 100/120 = 83.333%
      expect(result.data[0][calcKey]).toBeCloseTo((100 / 120) * 100, 3);
      // Row 1: sales 200, profit 50 => total 250 => 200/250 = 80%
      expect(result.data[1][calcKey]).toBeCloseTo((200 / 250) * 100, 3);
    });

    test('computes Percent of Grand Total across all rows and metrics', () => {
      const calc: TableCalculationConfig = {
        column: 'sales',
        type: 'percent_of_total',
        basis: 'grand_total',
      };
      const result = applyTableCalculations(sampleData, sampleColumns, [calc]);
      const calcKey = result.calculatedColumns[0].key;
      // Grand sum = (100+200+300) + (20+50+80) = 600 + 150 = 750
      // sales 100 / 750 = 13.333%
      expect(result.data[0][calcKey]).toBeCloseTo((100 / 750) * 100, 3);
      expect(result.data[1][calcKey]).toBeCloseTo((200 / 750) * 100, 3);
      expect(result.data[2][calcKey]).toBeCloseTo((300 / 750) * 100, 3);
    });
  });

  describe('2. Rank (Standard and Dense)', () => {
    const tieData = [
      { name: 'A', score: 90 },
      { name: 'B', score: 80 },
      { name: 'C', score: 80 },
      { name: 'D', score: 70 },
    ];
    const tieCols: EnterpriseTableColumn[] = [
      { key: 'name', label: 'Name', isMetric: false, dataType: 'string' },
      { key: 'score', label: 'Score', isMetric: true, dataType: 'number' },
    ];

    test('computes Standard Rank (skips next rank after tie: 1, 2, 2, 4)', () => {
      const calc: TableCalculationConfig = {
        column: 'score',
        type: 'rank',
        rankMode: 'standard',
        rankDirection: 'desc',
      };
      const result = applyTableCalculations(tieData, tieCols, [calc]);
      const calcKey = result.calculatedColumns[0].key;
      expect(result.data[0][calcKey]).toBe(1); // 90
      expect(result.data[1][calcKey]).toBe(2); // 80 (tie)
      expect(result.data[2][calcKey]).toBe(2); // 80 (tie)
      expect(result.data[3][calcKey]).toBe(4); // 70 (skipped to 4)
    });

    test('computes Dense Rank (does NOT skip rank after tie: 1, 2, 2, 3)', () => {
      const calc: TableCalculationConfig = {
        column: 'score',
        type: 'rank',
        rankMode: 'dense',
        rankDirection: 'desc',
      };
      const result = applyTableCalculations(tieData, tieCols, [calc]);
      const calcKey = result.calculatedColumns[0].key;
      expect(result.data[0][calcKey]).toBe(1); // 90
      expect(result.data[1][calcKey]).toBe(2); // 80
      expect(result.data[2][calcKey]).toBe(2); // 80
      expect(result.data[3][calcKey]).toBe(3); // 70 (dense next is 3)
    });

    test('computes Ascending Rank (lowest score gets rank 1)', () => {
      const calc: TableCalculationConfig = {
        column: 'score',
        type: 'rank',
        rankMode: 'standard',
        rankDirection: 'asc',
      };
      const result = applyTableCalculations(tieData, tieCols, [calc]);
      const calcKey = result.calculatedColumns[0].key;
      expect(result.data[3][calcKey]).toBe(1); // 70 is lowest -> rank 1
      expect(result.data[1][calcKey]).toBe(2); // 80 -> rank 2
      expect(result.data[2][calcKey]).toBe(2); // 80 -> rank 2
      expect(result.data[0][calcKey]).toBe(4); // 90 -> rank 4
    });
  });

  describe('3. Running Total', () => {
    test('computes cumulative sum along column order', () => {
      const calc: TableCalculationConfig = {
        column: 'sales',
        type: 'running_total',
      };
      const result = applyTableCalculations(sampleData, sampleColumns, [calc]);
      const calcKey = result.calculatedColumns[0].key;
      expect(result.data[0][calcKey]).toBe(100);
      expect(result.data[1][calcKey]).toBe(300); // 100 + 200
      expect(result.data[2][calcKey]).toBe(600); // 100 + 200 + 300
    });
  });

  describe('4. Difference From', () => {
    test('computes Difference From Previous Row', () => {
      const calc: TableCalculationConfig = {
        column: 'sales',
        type: 'difference_from',
        basis: 'previous',
      };
      const result = applyTableCalculations(sampleData, sampleColumns, [calc]);
      const calcKey = result.calculatedColumns[0].key;
      expect(result.data[0][calcKey]).toBeNull(); // First row has no previous
      expect(result.data[1][calcKey]).toBe(100); // 200 - 100
      expect(result.data[2][calcKey]).toBe(100); // 300 - 200
    });

    test('computes Difference From First Row', () => {
      const calc: TableCalculationConfig = {
        column: 'sales',
        type: 'difference_from',
        basis: 'first',
      };
      const result = applyTableCalculations(sampleData, sampleColumns, [calc]);
      const calcKey = result.calculatedColumns[0].key;
      expect(result.data[0][calcKey]).toBe(0); // 100 - 100
      expect(result.data[1][calcKey]).toBe(100); // 200 - 100
      expect(result.data[2][calcKey]).toBe(200); // 300 - 100
    });
  });

  describe('5. Percent Difference From', () => {
    test('computes Percent Difference From Previous Row', () => {
      const calc: TableCalculationConfig = {
        column: 'sales',
        type: 'percent_difference_from',
        basis: 'previous',
      };
      const result = applyTableCalculations(sampleData, sampleColumns, [calc]);
      const calcKey = result.calculatedColumns[0].key;
      expect(result.data[0][calcKey]).toBeNull();
      expect(result.data[1][calcKey]).toBeCloseTo(((200 - 100) / 100) * 100, 3); // 100%
      expect(result.data[2][calcKey]).toBeCloseTo(((300 - 200) / 200) * 100, 3); // 50%
    });

    test('computes Percent Difference From First Row', () => {
      const calc: TableCalculationConfig = {
        column: 'sales',
        type: 'percent_difference_from',
        basis: 'first',
      };
      const result = applyTableCalculations(sampleData, sampleColumns, [calc]);
      const calcKey = result.calculatedColumns[0].key;
      expect(result.data[0][calcKey]).toBe(0);
      expect(result.data[1][calcKey]).toBeCloseTo(((200 - 100) / 100) * 100, 3); // 100%
      expect(result.data[2][calcKey]).toBeCloseTo(((300 - 100) / 100) * 100, 3); // 200%
    });
  });

  describe('6. Moving Average', () => {
    const timeData = [
      { day: 1, metric: 10 },
      { day: 2, metric: 20 },
      { day: 3, metric: 30 },
      { day: 4, metric: 40 },
    ];
    const timeCols: EnterpriseTableColumn[] = [
      { key: 'day', label: 'Day', isMetric: false, dataType: 'number' },
      { key: 'metric', label: 'Metric', isMetric: true, dataType: 'number' },
    ];

    test('computes Moving Average with window size 3', () => {
      const calc: TableCalculationConfig = {
        column: 'metric',
        type: 'moving_average',
        windowSize: 3,
      };
      const result = applyTableCalculations(timeData, timeCols, [calc]);
      const calcKey = result.calculatedColumns[0].key;
      expect(result.data[0][calcKey]).toBe(10); // [10] avg = 10
      expect(result.data[1][calcKey]).toBe(15); // [10, 20] avg = 15
      expect(result.data[2][calcKey]).toBe(20); // [10, 20, 30] avg = 20
      expect(result.data[3][calcKey]).toBe(30); // [20, 30, 40] avg = 30
    });
  });

  describe('7. Percentile', () => {
    test('computes percentile ranks between 0 and 100', () => {
      const calc: TableCalculationConfig = {
        column: 'sales',
        type: 'percentile',
      };
      const result = applyTableCalculations(sampleData, sampleColumns, [calc]);
      const calcKey = result.calculatedColumns[0].key;
      const p1 = result.data[0][calcKey] as number;
      const p2 = result.data[1][calcKey] as number;
      const p3 = result.data[2][calcKey] as number;

      expect(p1).toBeGreaterThanOrEqual(0);
      expect(p3).toBeLessThanOrEqual(100);
      expect(p1).toBeLessThan(p2);
      expect(p2).toBeLessThan(p3);
    });
  });

  describe('Null & Undefined Safety in All Calculations', () => {
    const dataWithNulls = [
      { region: 'NA', sales: 100, profit: null },
      { region: 'EMEA', sales: null, profit: 50 },
      { region: 'APAC', sales: undefined, profit: undefined },
      { region: 'LATAM', sales: 300, profit: 70 },
    ];

    test('handles nulls gracefully without throwing or producing NaN across all 7 calculation types', () => {
      const allCalcs: TableCalculationConfig[] = [
        { column: 'sales', type: 'percent_of_total', basis: 'column' },
        { column: 'sales', type: 'rank' },
        { column: 'sales', type: 'running_total' },
        { column: 'sales', type: 'difference_from', basis: 'previous' },
        { column: 'sales', type: 'percent_difference_from', basis: 'previous' },
        { column: 'sales', type: 'moving_average', windowSize: 3 },
        { column: 'sales', type: 'percentile' },
      ];

      expect(() => {
        const result = applyTableCalculations(dataWithNulls, sampleColumns, allCalcs);
        expect(result.calculatedColumns).toHaveLength(7);

        result.calculatedColumns.forEach(col => {
          result.data.forEach(row => {
            const val = row[col.key];
            if (val !== null && val !== undefined) {
              expect(Number.isNaN(val)).toBe(false);
              expect(Number.isFinite(val)).toBe(true);
            }
          });
        });
      }).not.toThrow();
    });
  });

  describe('Label & Key Generators', () => {
    test('generates intuitive column keys and readable labels', () => {
      const calc1: TableCalculationConfig = {
        column: 'sales',
        type: 'percent_of_total',
        basis: 'column',
      };
      expect(getCalculatedColumnKey('sales', calc1)).toBe('sales_calc_percent_of_total_column');
      expect(getCalculatedColumnLabel('Sales', calc1)).toBe('% of Column (Sales)');

      const calc2: TableCalculationConfig = {
        column: 'profit',
        type: 'rank',
        rankMode: 'dense',
        rankDirection: 'asc',
      };
      expect(getCalculatedColumnKey('profit', calc2)).toBe('profit_calc_rank_dense_asc');
      expect(getCalculatedColumnLabel('Profit', calc2)).toBe('Dense Rank (Asc) of Profit');
    });
  });
});
