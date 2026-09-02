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

import { t } from '@apache-superset/core/translation';
import { Behavior, ChartMetadata, ChartPlugin } from '@superset-ui/core';
import transformProps from './transformProps';
import thumbnail from './images/thumbnail.png';
import thumbnailDark from './images/thumbnail-dark.png';
import controlPanel from './controlPanel';
import buildQuery from './buildQuery';
import { EnterpriseTableFormData, EnterpriseTableProps } from './types';

export * from './types';
export * from './tableCalculations';
export * from './colorScales';

const metadata = new ChartMetadata({
  behaviors: [
    Behavior.InteractiveChart,
    Behavior.DrillToDetail,
    Behavior.DrillBy,
  ],
  category: t('Table'),
  description: t(
    'Enterprise interactive table with rich formatting, client and server-side controls, and high-performance dataset rendering.',
  ),
  name: t('Enterprise Interactive Table'),
  tags: [
    t('Table'),
    t('Enterprise'),
    t('Interactive'),
    t('Preset-like'),
  ],
  thumbnail,
  thumbnailDark,
});

export class EnterpriseTableChartPlugin extends ChartPlugin<
  EnterpriseTableFormData,
  EnterpriseTableProps
> {
  constructor() {
    super({
      buildQuery,
      controlPanel,
      loadChart: () => import('./EnterpriseTableChart'),
      metadata,
      transformProps,
    });
  }
}

export default EnterpriseTableChartPlugin;
