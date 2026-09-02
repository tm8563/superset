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
import {
  ControlPanelConfig,
  formatSelectOptions,
  sharedControls,
} from '@superset-ui/chart-controls';

const PAGE_SIZE_OPTIONS = formatSelectOptions<number>([10, 20, 50, 100, 200]);

const HEATMAP_COLOR_MODES = [
  ['none', t('None (Binary Pos/Neg)')],
  ['sequential', t('Sequential Gradient (Single Hue)')],
  ['diverging', t('Diverging Gradient (Two Hues / Midpoint)')],
];

const HEATMAP_SCOPES = [
  ['per_column', t('Per Column (Independent Min/Max)')],
  ['per_table', t('Per Table (Shared Global Min/Max)')],
];

const PALETTE_OPTIONS = [
  ['blue_white_yellow', t('Blue / White / Yellow')],
  ['dark_blue', t('Dark Blues')],
  ['greens', t('Greens')],
  ['purples', t('Purples')],
  ['schemeRdYlGn', t('Red / Yellow / Green (Diverging)')],
  ['schemeRdBu', t('Red / Blue (Diverging)')],
  ['schemeBrBG', t('Brown / Blue-Green (Diverging)')],
  ['schemePRGn', t('Purple / Green (Diverging)')],
];

const config: ControlPanelConfig = {
  controlPanelSections: [
    {
      label: t('Query'),
      expanded: true,
      controlSetRows: [
        [
          {
            name: 'groupby',
            config: {
              ...sharedControls.groupby,
              label: t('Dimensions'),
              description: t('Select one or more dimension columns to group by'),
            },
          },
        ],
        [
          {
            name: 'metrics',
            config: {
              ...sharedControls.metrics,
              label: t('Metrics'),
              description: t('Select one or more metric aggregations'),
            },
          },
        ],
        ['adhoc_filters'],
        [
          {
            name: 'row_limit',
            config: sharedControls.row_limit,
          },
        ],
      ],
    },
    {
      label: t('Highlight Table / Heat Map'),
      expanded: true,
      controlSetRows: [
        [
          {
            name: 'heatmap_color_mode',
            config: {
              type: 'SelectControl',
              label: t('Heat Map Color Mode'),
              default: 'none',
              choices: HEATMAP_COLOR_MODES,
              description: t(
                'Choose continuous sequential/diverging color scale or standard binary coloring',
              ),
            },
          },
        ],
        [
          {
            name: 'heatmap_palette',
            config: {
              type: 'SelectControl',
              label: t('Color Palette'),
              default: 'schemeRdYlGn',
              choices: PALETTE_OPTIONS,
              description: t('Select gradient color palette for heat map cells'),
              visibility: ({ controls }) =>
                controls?.heatmap_color_mode?.value !== 'none',
            },
          },
        ],
        [
          {
            name: 'heatmap_scope',
            config: {
              type: 'SelectControl',
              label: t('Color Scale Scope'),
              default: 'per_column',
              choices: HEATMAP_SCOPES,
              description: t(
                'Compute scale range per column or shared across entire table',
              ),
              visibility: ({ controls }) =>
                controls?.heatmap_color_mode?.value !== 'none',
            },
          },
        ],
        [
          {
            name: 'heatmap_midpoint',
            config: {
              type: 'TextControl',
              label: t('Diverging Midpoint'),
              default: 0,
              isFloat: true,
              description: t(
                'Center value for diverging color scales (e.g. 0 for profit/loss)',
              ),
              visibility: ({ controls }) =>
                controls?.heatmap_color_mode?.value === 'diverging',
            },
          },
        ],
      ],
    },
    {
      label: t('Table Options'),
      expanded: true,
      controlSetRows: [
        [
          {
            name: 'page_size',
            config: {
              type: 'SelectControl',
              label: t('Page size'),
              default: 20,
              choices: PAGE_SIZE_OPTIONS,
              description: t('Number of rows displayed per page'),
            },
          },
        ],
        [
          {
            name: 'include_search',
            config: {
              type: 'CheckboxControl',
              label: t('Search box'),
              default: true,
              description: t('Show quick text filter search input above table'),
            },
          },
        ],
        [
          {
            name: 'enable_column_sort',
            config: {
              type: 'CheckboxControl',
              label: t('Enable sorting'),
              default: true,
              description: t('Allow interactive single and multi-column sorting'),
            },
          },
        ],
        [
          {
            name: 'enable_column_resize',
            config: {
              type: 'CheckboxControl',
              label: t('Enable resizing'),
              default: true,
              description: t('Allow interactive column width resizing'),
            },
          },
        ],
        [
          {
            name: 'enable_column_reorder',
            config: {
              type: 'CheckboxControl',
              label: t('Enable reordering (Drag & Buttons)'),
              default: true,
              description: t('Allow column reordering via drag-and-drop or header arrow buttons'),
            },
          },
        ],
        [
          {
            name: 'enable_column_pinning',
            config: {
              type: 'CheckboxControl',
              label: t('Enable column pinning'),
              default: true,
              description: t('Allow pinning columns to left or right sides of table'),
            },
          },
        ],
        [
          {
            name: 'enable_column_filters',
            config: {
              type: 'CheckboxControl',
              label: t('Enable column filters'),
              default: true,
              description: t('Show per-column text and numeric filter popovers'),
            },
          },
        ],
        [
          {
            name: 'enable_saved_layouts',
            config: {
              type: 'CheckboxControl',
              label: t('Enable saved layouts'),
              default: true,
              description: t('Allow saving and restoring customized views in local browser storage'),
            },
          },
        ],
        [
          {
            name: 'enable_cell_bars',
            config: {
              type: 'CheckboxControl',
              label: t('Enable cell bars'),
              default: true,
              description: t('Render proportional horizontal bar charts inside numeric metric cells'),
            },
          },
        ],
        [
          {
            name: 'enable_value_coloring',
            config: {
              type: 'CheckboxControl',
              label: t('Enable value coloring'),
              default: true,
              description: t('Color positive values green and negative values red'),
            },
          },
        ],
        [
          {
            name: 'enable_hyperlinks',
            config: {
              type: 'CheckboxControl',
              label: t('Enable safe hyperlinks'),
              default: true,
              description: t('Auto-render safe URLs (http/https/mailto) as clickable links'),
            },
          },
        ],
        [
          {
            name: 'enable_export_excel',
            config: {
              type: 'CheckboxControl',
              label: t('Enable Excel/CSV export'),
              default: true,
              description: t('Show export action button for downloading data as Excel or CSV'),
            },
          },
        ],
        [
          {
            name: 'enable_virtualization',
            config: {
              type: 'CheckboxControl',
              label: t('Enable virtualization'),
              default: false,
              description: t('Enable high-performance virtual windowing for 10,000+ rows'),
            },
          },
        ],
      ],
    },
  ],
};

export default config;
