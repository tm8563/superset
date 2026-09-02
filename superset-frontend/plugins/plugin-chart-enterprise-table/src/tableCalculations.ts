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

import { DataRecord, DataRecordValue } from '@superset-ui/core';
import {
  TableCalculationConfig,
  EnterpriseTableColumn,
} from './types';

/**
 * Returns true if a value is a valid, finite number.
 */
export function isValidNumber(val: DataRecordValue): val is number {
  return typeof val === 'number' && !Number.isNaN(val) && Number.isFinite(val);
}

/**
 * Generates a unique key for a calculated column based on source column and calculation config.
 */
export function getCalculatedColumnKey(
  sourceColumn: string,
  calc: TableCalculationConfig,
): string {
  const basisSuffix = calc.basis ? `_${calc.basis}` : '';
  const modeSuffix = calc.rankMode ? `_${calc.rankMode}` : '';
  const dirSuffix = calc.rankDirection ? `_${calc.rankDirection}` : '';
  const winSuffix = calc.windowSize ? `_w${calc.windowSize}` : '';
  return `${sourceColumn}_calc_${calc.type}${basisSuffix}${modeSuffix}${dirSuffix}${winSuffix}`;
}

/**
 * Generates a user-friendly label for a calculated column.
 */
export function getCalculatedColumnLabel(
  sourceLabel: string,
  calc: TableCalculationConfig,
): string {
  if (calc.outputColumnName) {
    return calc.outputColumnName;
  }
  switch (calc.type) {
    case 'percent_of_total': {
      const basisName =
        calc.basis === 'row'
          ? 'Row'
          : calc.basis === 'grand_total'
          ? 'Grand Total'
          : 'Column';
      return `% of ${basisName} (${sourceLabel})`;
    }
    case 'rank': {
      const modeName = calc.rankMode === 'dense' ? 'Dense Rank' : 'Rank';
      const dirName = calc.rankDirection === 'asc' ? ' (Asc)' : ' (Desc)';
      return `${modeName}${dirName} of ${sourceLabel}`;
    }
    case 'running_total':
      return `Running Total of ${sourceLabel}`;
    case 'difference_from': {
      const basisName = calc.basis === 'first' ? 'First' : 'Prev';
      return `Diff from ${basisName} (${sourceLabel})`;
    }
    case 'percent_difference_from': {
      const basisName = calc.basis === 'first' ? 'First' : 'Prev';
      return `% Diff from ${basisName} (${sourceLabel})`;
    }
    case 'moving_average': {
      const windowSize = calc.windowSize ?? 3;
      return `Moving Avg (${windowSize}) of ${sourceLabel}`;
    }
    case 'percentile':
      return `Percentile of ${sourceLabel}`;
    default:
      return `${sourceLabel} (calc)`;
  }
}

/**
 * Computes Percent of Total for a specific column.
 */
function computePercentOfTotal(
  data: DataRecord[],
  sourceCol: string,
  metricCols: string[],
  basis: 'column' | 'row' | 'grand_total' = 'column',
): (number | null)[] {
  if (data.length === 0) return [];

  if (basis === 'column') {
    let colSum = 0;
    for (let i = 0; i < data.length; i += 1) {
      const v = data[i][sourceCol];
      if (isValidNumber(v)) {
        colSum += v;
      }
    }
    return data.map(row => {
      const v = row[sourceCol];
      if (!isValidNumber(v) || colSum === 0) return null;
      return (v / colSum) * 100;
    });
  }

  if (basis === 'row') {
    return data.map(row => {
      const v = row[sourceCol];
      if (!isValidNumber(v)) return null;
      let rowSum = 0;
      for (let j = 0; j < metricCols.length; j += 1) {
        const mv = row[metricCols[j]];
        if (isValidNumber(mv)) {
          rowSum += mv;
        }
      }
      if (rowSum === 0) return null;
      return (v / rowSum) * 100;
    });
  }

  // basis === 'grand_total'
  let grandSum = 0;
  for (let i = 0; i < data.length; i += 1) {
    for (let j = 0; j < metricCols.length; j += 1) {
      const mv = data[i][metricCols[j]];
      if (isValidNumber(mv)) {
        grandSum += mv;
      }
    }
  }

  return data.map(row => {
    const v = row[sourceCol];
    if (!isValidNumber(v) || grandSum === 0) return null;
    return (v / grandSum) * 100;
  });
}

/**
 * Computes Rank (Standard competition rank or Dense rank) for a column.
 */
function computeRank(
  data: DataRecord[],
  sourceCol: string,
  mode: 'standard' | 'dense' = 'standard',
  direction: 'asc' | 'desc' = 'desc',
): (number | null)[] {
  if (data.length === 0) return [];

  // Extract non-null values with their original indices
  const indexedValues: { index: number; val: number }[] = [];
  for (let i = 0; i < data.length; i += 1) {
    const v = data[i][sourceCol];
    if (isValidNumber(v)) {
      indexedValues.push({ index: i, val: v });
    }
  }

  // Sort values
  indexedValues.sort((a, b) => {
    if (direction === 'asc') {
      return a.val - b.val;
    }
    return b.val - a.val;
  });

  const ranks: (number | null)[] = new Array(data.length).fill(null);

  if (mode === 'standard') {
    let currentRank = 1;
    for (let i = 0; i < indexedValues.length; i += 1) {
      if (i > 0 && indexedValues[i].val !== indexedValues[i - 1].val) {
        currentRank = i + 1;
      }
      ranks[indexedValues[i].index] = currentRank;
    }
  } else {
    // Dense rank
    let denseRank = 1;
    for (let i = 0; i < indexedValues.length; i += 1) {
      if (i > 0 && indexedValues[i].val !== indexedValues[i - 1].val) {
        denseRank += 1;
      }
      ranks[indexedValues[i].index] = denseRank;
    }
  }

  return ranks;
}

/**
 * Computes Running Total (Cumulative sum) for a column.
 */
function computeRunningTotal(
  data: DataRecord[],
  sourceCol: string,
): (number | null)[] {
  if (data.length === 0) return [];
  let runningSum = 0;
  let hasEncounteredNumber = false;

  return data.map(row => {
    const v = row[sourceCol];
    if (isValidNumber(v)) {
      runningSum += v;
      hasEncounteredNumber = true;
      return runningSum;
    }
    return hasEncounteredNumber ? runningSum : null;
  });
}

/**
 * Computes Difference From (Previous Row or First Row).
 */
function computeDifferenceFrom(
  data: DataRecord[],
  sourceCol: string,
  basis: 'previous' | 'first' = 'previous',
): (number | null)[] {
  if (data.length === 0) return [];

  if (basis === 'first') {
    const firstVal = data[0]?.[sourceCol];
    const firstNum = isValidNumber(firstVal) ? firstVal : null;

    return data.map((row, idx) => {
      const v = row[sourceCol];
      if (!isValidNumber(v) || firstNum === null) return null;
      if (idx === 0) return 0;
      return v - firstNum;
    });
  }

  // basis === 'previous'
  return data.map((row, idx) => {
    if (idx === 0) return null;
    const v = row[sourceCol];
    const prevVal = data[idx - 1]?.[sourceCol];
    if (!isValidNumber(v) || !isValidNumber(prevVal)) return null;
    return v - prevVal;
  });
}

/**
 * Computes Percent Difference From (Previous Row or First Row).
 */
function computePercentDifferenceFrom(
  data: DataRecord[],
  sourceCol: string,
  basis: 'previous' | 'first' = 'previous',
): (number | null)[] {
  if (data.length === 0) return [];

  if (basis === 'first') {
    const firstVal = data[0]?.[sourceCol];
    const firstNum = isValidNumber(firstVal) && firstVal !== 0 ? firstVal : null;

    return data.map((row, idx) => {
      const v = row[sourceCol];
      if (!isValidNumber(v) || firstNum === null) return null;
      if (idx === 0) return 0;
      return ((v - firstNum) / Math.abs(firstNum)) * 100;
    });
  }

  // basis === 'previous'
  return data.map((row, idx) => {
    if (idx === 0) return null;
    const v = row[sourceCol];
    const prevVal = data[idx - 1]?.[sourceCol];
    if (!isValidNumber(v) || !isValidNumber(prevVal) || prevVal === 0) return null;
    return ((v - prevVal) / Math.abs(prevVal)) * 100;
  });
}

/**
 * Computes Moving Average with configurable window size.
 */
function computeMovingAverage(
  data: DataRecord[],
  sourceCol: string,
  windowSize = 3,
): (number | null)[] {
  if (data.length === 0) return [];
  const safeWindow = Math.max(1, windowSize);

  return data.map((_, idx) => {
    const startIdx = Math.max(0, idx - safeWindow + 1);
    let sum = 0;
    let count = 0;

    for (let i = startIdx; i <= idx; i += 1) {
      const v = data[i][sourceCol];
      if (isValidNumber(v)) {
        sum += v;
        count += 1;
      }
    }

    if (count === 0) return null;
    return sum / count;
  });
}

/**
 * Computes Percentile Rank (0 to 100) for a column.
 */
function computePercentile(
  data: DataRecord[],
  sourceCol: string,
): (number | null)[] {
  if (data.length === 0) return [];

  const validNumbers: number[] = [];
  for (let i = 0; i < data.length; i += 1) {
    const v = data[i][sourceCol];
    if (isValidNumber(v)) {
      validNumbers.push(v);
    }
  }

  const n = validNumbers.length;
  if (n === 0) {
    return new Array(data.length).fill(null);
  }
  if (n === 1) {
    return data.map(row => (isValidNumber(row[sourceCol]) ? 100 : null));
  }

  validNumbers.sort((a, b) => a - b);

  return data.map(row => {
    const v = row[sourceCol];
    if (!isValidNumber(v)) return null;

    let countLess = 0;
    let countEqual = 0;
    for (let i = 0; i < validNumbers.length; i += 1) {
      if (validNumbers[i] < v) {
        countLess += 1;
      } else if (validNumbers[i] === v) {
        countEqual += 1;
      }
    }

    const percentile = ((countLess + 0.5 * countEqual) / n) * 100;
    return Math.round(percentile * 100) / 100;
  });
}

/**
 * Main function to evaluate all configured table calculations over a dataset.
 * Returns augmented data array and list of newly generated EnterpriseTableColumn descriptors.
 */
export function applyTableCalculations(
  data: DataRecord[],
  columns: EnterpriseTableColumn[],
  calculations: TableCalculationConfig[] = [],
): {
  data: DataRecord[];
  calculatedColumns: EnterpriseTableColumn[];
} {
  if (!calculations || calculations.length === 0 || data.length === 0) {
    return { data, calculatedColumns: [] };
  }

  const metricCols = columns.filter(c => c.isMetric).map(c => c.key);
  const columnMap = new Map<string, EnterpriseTableColumn>();
  columns.forEach(c => columnMap.set(c.key, c));

  // Shallow clone records so original data is not mutated
  const augmentedData: DataRecord[] = data.map(row => ({ ...row }));
  const calculatedColumns: EnterpriseTableColumn[] = [];

  calculations.forEach(calc => {
    if (!calc.column || calc.type === 'none') return;
    const sourceColDef = columnMap.get(calc.column);
    const sourceLabel = sourceColDef?.label || calc.column;
    const calcKey = getCalculatedColumnKey(calc.column, calc);
    const calcLabel = getCalculatedColumnLabel(sourceLabel, calc);

    let calculatedValues: (number | null)[] = [];

    switch (calc.type) {
      case 'percent_of_total':
        calculatedValues = computePercentOfTotal(
          data,
          calc.column,
          metricCols,
          (calc.basis as 'column' | 'row' | 'grand_total') || 'column',
        );
        break;
      case 'rank':
        calculatedValues = computeRank(
          data,
          calc.column,
          calc.rankMode || 'standard',
          calc.rankDirection || 'desc',
        );
        break;
      case 'running_total':
        calculatedValues = computeRunningTotal(data, calc.column);
        break;
      case 'difference_from':
        calculatedValues = computeDifferenceFrom(
          data,
          calc.column,
          (calc.basis as 'previous' | 'first') || 'previous',
        );
        break;
      case 'percent_difference_from':
        calculatedValues = computePercentDifferenceFrom(
          data,
          calc.column,
          (calc.basis as 'previous' | 'first') || 'previous',
        );
        break;
      case 'moving_average':
        calculatedValues = computeMovingAverage(
          data,
          calc.column,
          calc.windowSize || 3,
        );
        break;
      case 'percentile':
        calculatedValues = computePercentile(data, calc.column);
        break;
      default:
        break;
    }

    let minVal: number | undefined;
    let maxVal: number | undefined;

    for (let i = 0; i < augmentedData.length; i += 1) {
      const val = calculatedValues[i] ?? null;
      augmentedData[i][calcKey] = val;

      if (val !== null) {
        if (minVal === undefined || val < minVal) minVal = val;
        if (maxVal === undefined || val > maxVal) maxVal = val;
      }
    }

    calculatedColumns.push({
      key: calcKey,
      label: calcLabel,
      isMetric: true,
      dataType: 'number',
      minValue: minVal,
      maxValue: maxVal,
      isCalculated: true,
      calculationType: calc.type,
      sourceColumn: calc.column,
    });
  });

  return { data: augmentedData, calculatedColumns };
}
