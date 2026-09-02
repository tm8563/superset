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

import { buildQuery } from '../src/buildQuery';
import { EnterpriseTableFormData } from '../src/types';

test('builds correct query context with dimensions and metrics', () => {
  const formData: EnterpriseTableFormData = {
    datasource: '28__table',
    viz_type: 'enterprise_table',
    groupby: ['customer_region', 'product_category'],
    metrics: ['sum__sales_amount'],
    row_limit: 50,
  };

  const queryContext = buildQuery(formData);
  expect(queryContext.queries).toHaveLength(1);
  const query = queryContext.queries[0];
  expect(query.columns).toEqual(['customer_region', 'product_category']);
  expect(query.metrics).toEqual(['sum__sales_amount']);
  expect(query.row_limit).toBe(50);
});

test('applies default row limit when unspecified', () => {
  const formData: EnterpriseTableFormData = {
    datasource: '28__table',
    viz_type: 'enterprise_table',
    groupby: ['country'],
    metrics: ['count'],
  };

  const queryContext = buildQuery(formData);
  expect(queryContext.queries[0].row_limit).toBe(100);
});
