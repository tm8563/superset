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

// HSC customization tests: Ctrl/Cmd+click multi-select, Shift+click range
// select and full-row highlighting on the Table chart, matching the pivot
// table (docs/00-runbook.md §5e/§5f/§5y/§5ab and their restoration).

import '@testing-library/jest-dom';
import { render, screen, fireEvent, within } from '@superset-ui/core/spec';
import { type DataMask } from '@superset-ui/core';
import TableChart from '../src/TableChart';
import transformProps from '../src/transformProps';
import { TableChartTransformedProps } from '../src/types';
import testData from './testData';
import { ProviderWrapper } from './testHelpers';

// testData.basic rows, in data order: Michael, Joe, Maria (Maria's
// __timestamp is null).

type Filters = TableChartTransformedProps['filters'];

function renderTable(
  filters?: Filters,
  highlightFilters?: Filters,
  setDataMask = jest.fn<void, [DataMask]>(),
) {
  const props = transformProps({
    ...testData.basic,
    hooks: { setDataMask },
    emitCrossFilters: true,
  });
  const ui = (f?: Filters, h?: Filters) => (
    <ProviderWrapper>
      <TableChart
        {...props}
        emitCrossFilters
        setDataMask={setDataMask}
        filters={f}
        highlightFilters={h}
        sticky={false}
      />
    </ProviderWrapper>
  );
  const utils = render(ui(filters, highlightFilters));
  return {
    setDataMask,
    rerender: (f?: Filters, h?: Filters) => utils.rerender(ui(f, h)),
  };
}

function lastCrossFilter(setDataMask: jest.Mock<void, [DataMask]>) {
  const calls = setDataMask.mock.calls.filter(
    ([mask]) => mask?.filterState !== undefined,
  );
  return calls[calls.length - 1]?.[0];
}

const rowOf = (text: string) => screen.getByText(text).closest('tr')!;

test('Ctrl+click adds a value to the selection and Ctrl+click again removes it', () => {
  const { setDataMask, rerender } = renderTable({ name: ['Michael'] });

  fireEvent.click(screen.getByText('Joe'), { ctrlKey: true });
  let mask = lastCrossFilter(setDataMask);
  expect(mask?.filterState?.filters).toEqual({ name: ['Michael', 'Joe'] });
  expect(mask?.extraFormData?.filters).toEqual([
    expect.objectContaining({ col: 'name', op: 'IN', val: ['Michael', 'Joe'] }),
  ]);

  rerender({ name: ['Michael', 'Joe'] });
  fireEvent.click(screen.getByText('Michael'), { metaKey: true });
  mask = lastCrossFilter(setDataMask);
  expect(mask?.filterState?.filters).toEqual({ name: ['Joe'] });
});

test('plain click still replaces the selection with a single value', () => {
  const { setDataMask } = renderTable({ name: ['Michael', 'Joe'] });

  fireEvent.click(screen.getByText('Maria'));
  expect(lastCrossFilter(setDataMask)?.filterState?.filters).toEqual({
    name: ['Maria'],
  });
});

test('Shift+click selects every row between the anchor and the clicked row', () => {
  const { setDataMask } = renderTable();

  fireEvent.click(screen.getByText('Michael'));
  fireEvent.click(screen.getByText('Maria'), { shiftKey: true });
  expect(lastCrossFilter(setDataMask)?.filterState?.filters).toEqual({
    name: ['Michael', 'Joe', 'Maria'],
  });
});

test('Shift+click works upward and keeps the anchor for the next Shift+click', () => {
  const { setDataMask } = renderTable();

  fireEvent.click(screen.getByText('Maria'));
  fireEvent.click(screen.getByText('Joe'), { shiftKey: true });
  expect(lastCrossFilter(setDataMask)?.filterState?.filters).toEqual({
    name: ['Joe', 'Maria'],
  });

  // anchor is still Maria, so this grows the range to the top row
  fireEvent.click(screen.getByText('Michael'), { shiftKey: true });
  expect(lastCrossFilter(setDataMask)?.filterState?.filters).toEqual({
    name: ['Michael', 'Joe', 'Maria'],
  });
});

test('Shift+click follows the on-screen order after sorting by a column header', () => {
  const { setDataMask } = renderTable();

  // the fixture sorts descending first (order_desc) -> Michael, Maria, Joe
  fireEvent.click(screen.getByRole('columnheader', { name: /name/ }));
  const names = screen
    .getAllByRole('row')
    .slice(1)
    .map(row => within(row).getAllByRole('cell')[1].textContent);
  expect(names).toEqual(['Michael', 'Maria', 'Joe']);

  fireEvent.click(screen.getByText('Michael'));
  fireEvent.click(screen.getByText('Maria'), { shiftKey: true });
  // data order (Michael, Joe, Maria) would wrongly include Joe
  expect(lastCrossFilter(setDataMask)?.filterState?.filters).toEqual({
    name: ['Michael', 'Maria'],
  });
});

test('Shift+click with no anchor in that column acts as a plain click', () => {
  const { setDataMask } = renderTable();

  fireEvent.click(screen.getByText('Joe'), { shiftKey: true });
  expect(lastCrossFilter(setDataMask)?.filterState?.filters).toEqual({
    name: ['Joe'],
  });
});

test('whole row is highlighted from own selection and cleared with none', () => {
  const { rerender } = renderTable(undefined, undefined);
  expect(document.querySelectorAll('.dt-is-active-row')).toHaveLength(0);

  rerender({ name: ['Joe'] }, { name: ['Joe'] });
  const joeCells = within(rowOf('Joe')).getAllByRole('cell');
  joeCells.forEach(cell => expect(cell).toHaveClass('dt-is-active-row'));
  within(rowOf('Michael'))
    .getAllByRole('cell')
    .forEach(cell => expect(cell).not.toHaveClass('dt-is-active-row'));
});

test('rows matching another chart filter are highlighted without becoming this chart selection', () => {
  renderTable(undefined, { 'abc.com': ['bar'] });

  within(rowOf('Joe'))
    .getAllByRole('cell')
    .forEach(cell => expect(cell).toHaveClass('dt-is-active-row'));
  // the stronger "clicked here" tint is reserved for this chart's own clicks
  expect(screen.getByText('bar')).not.toHaveClass('dt-is-active-filter');
});

test('temporal filters emitted as epoch ms highlight the matching Date row', () => {
  renderTable(undefined, { __timestamp: [1585932584140] });

  expect(within(rowOf('Joe')).getAllByRole('cell')[0]).toHaveClass(
    'dt-is-active-row',
  );
  expect(within(rowOf('Michael')).getAllByRole('cell')[0]).not.toHaveClass(
    'dt-is-active-row',
  );
});

test('an empty cell in a highlighted row is marked so it can stay unpainted', () => {
  renderTable(undefined, { name: ['Maria'] });

  const timestampCell = within(rowOf('Maria')).getAllByRole('cell')[0];
  expect(timestampCell).toHaveClass('dt-is-active-row');
  expect(timestampCell).toHaveClass('dt-is-null');
});

test('Ctrl+click never re-emits values that only come from other charts', () => {
  const { setDataMask } = renderTable(
    { name: ['Michael'] },
    { name: ['Michael'], 'abc.com': ['bar'] },
  );

  fireEvent.click(screen.getByText('Joe'), { ctrlKey: true });
  expect(lastCrossFilter(setDataMask)?.filterState?.filters).toEqual({
    name: ['Michael', 'Joe'],
  });
});

test('plain click on a row highlighted by another chart selects it', () => {
  const { setDataMask } = renderTable(undefined, { name: ['Joe'] });

  fireEvent.click(screen.getByText('Joe'));
  expect(lastCrossFilter(setDataMask)?.filterState?.filters).toEqual({
    name: ['Joe'],
  });
});

test('transformProps keeps own filters apart from merged highlight filters', () => {
  const own = { name: ['Michael'] };
  const props = transformProps({
    ...testData.basic,
    filterState: { filters: own },
    rawFormData: {
      ...testData.basic.rawFormData,
      extra_form_data: {
        filters: [
          { col: 'name', op: 'IN', val: ['Joe'] },
          { col: 'abc.com', op: '==', val: 'bar' },
          { col: '__timestamp', op: 'TEMPORAL_RANGE', val: 'a : b' },
          { col: 'name', op: 'IS NULL' },
        ],
      },
    },
  });

  expect(props.filters).toEqual({ name: ['Michael'] });
  expect(props.highlightFilters).toEqual({
    name: ['Michael', 'Joe'],
    'abc.com': ['bar'],
  });
  // the dashboard's filterState arrays are never mutated by the merge
  expect(own.name).toEqual(['Michael']);
});
