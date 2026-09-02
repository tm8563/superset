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
import { render, screen, waitFor } from '@testing-library/react';
import '@testing-library/jest-dom';
import Handlebars from 'handlebars';
import { HandlebarsViewer } from '../../src/components/Handlebars/HandlebarsViewer';
import HandlebarsComponent from '../../src/Handlebars';

describe('Handlebars Security and Template Helpers Test Suite', () => {
  describe('Built-in Custom Helpers', () => {
    test('dateFormat helper formats dates correctly', () => {
      const template = Handlebars.compile('{{dateFormat my_date format="YYYY-MM-DD"}}');
      const result = template({ my_date: '2026-09-02T12:00:00Z' });
      expect(result).toBe('2026-09-02');
    });

    test('formatDate helper formats dates with fallback', () => {
      const template = Handlebars.compile('{{formatDate "YYYY" my_date}}');
      const result = template({ my_date: '2026-01-15' });
      expect(result).toBe('2026');
    });

    test('formatNumber helper formats numbers according to locale', () => {
      const template = Handlebars.compile('{{formatNumber amount "en-US"}}');
      const result = template({ amount: 1250000.5 });
      expect(result).toBe('1,250,000.5');
    });

    test('formatNumber helper passes through non-number values without error', () => {
      const template = Handlebars.compile('{{formatNumber amount}}');
      const result = template({ amount: 'N/A' });
      expect(result).toBe('N/A');
    });

    test('stringify helper serializes plain objects with double-brace HTML escaping', () => {
      const template = Handlebars.compile('{{stringify obj}}');
      const result = template({ obj: { region: 'North America', sales: 45000 } });
      // Double curly braces HTML-encode special characters by default (security feature)
      expect(result).toBe('{&quot;region&quot;:&quot;North America&quot;,&quot;sales&quot;:45000}');
    });

    test('stringify helper serializes plain objects with raw triple-brace syntax', () => {
      const template = Handlebars.compile('{{{stringify obj}}}');
      const result = template({ obj: { region: 'North America', sales: 45000 } });
      expect(result).toBe('{"region":"North America","sales":45000}');
    });

    test('stringify helper converts primitives to strings', () => {
      const template = Handlebars.compile('{{stringify num}}');
      const result = template({ num: 12345 });
      expect(result).toBe('12345');
    });

    test('parseJson helper parses JSON strings into objects in subexpressions', () => {
      const template = Handlebars.compile('{{#with (parseJson raw_json)}}{{name}}: {{value}}{{/with}}');
      const result = template({ raw_json: '{"name":"Revenue","value":99000}' });
      expect(result).toBe('Revenue: 99000');
    });

    test('parseJson throws a descriptive error on invalid JSON', () => {
      const template = Handlebars.compile('{{parseJson bad_json}}');
      expect(() => template({ bad_json: '{invalid-json' })).toThrow(/Invalid JSON string/);
    });

    test('group-by helper correctly groups records by dimension', () => {
      const template = Handlebars.compile(`
        {{#group data by="region"}}
          <h3>{{value}}</h3>
          {{#each items}}
            <p>{{product}}: {{sales}}</p>
          {{/each}}
        {{/group}}
      `.trim());

      const data = [
        { region: 'East', product: 'Widget A', sales: 100 },
        { region: 'East', product: 'Widget B', sales: 200 },
        { region: 'West', product: 'Widget C', sales: 300 },
      ];

      const result = template({ data });
      expect(result).toContain('<h3>East</h3>');
      expect(result).toContain('<p>Widget A: 100</p>');
      expect(result).toContain('<p>Widget B: 200</p>');
      expect(result).toContain('<h3>West</h3>');
      expect(result).toContain('<p>Widget C: 300</p>');
    });
  });

  describe('Handlebars AST & Prototype Pollution Protection', () => {
    test('disallows __proto__ property access in template execution', () => {
      const template = Handlebars.compile('{{data.__proto__}}');
      const result = template({ data: { name: 'safe' } });
      expect(result).toBe('');
    });

    test('disallows constructor property access in template execution', () => {
      const template = Handlebars.compile('{{data.constructor}}');
      const result = template({ data: { name: 'safe' } });
      expect(result).toBe('');
    });

    test('disallows prototype property access in template execution', () => {
      const template = Handlebars.compile('{{data.prototype}}');
      const result = template({ data: { name: 'safe' } });
      expect(result).toBe('');
    });
  });

  describe('Handlebars HTML Escaping and Injection Protection', () => {
    test('automatically HTML-escapes script tags in double-brace variables', () => {
      const template = Handlebars.compile('<div>{{user_input}}</div>');
      const result = template({ user_input: '<script>alert("xss")</script>' });
      expect(result).toBe('<div>&lt;script&gt;alert(&quot;xss&quot;)&lt;/script&gt;</div>');
    });

    test('automatically HTML-escapes event handlers in double-brace variables', () => {
      const template = Handlebars.compile('<span>{{user_input}}</span>');
      const result = template({ user_input: '<img src=x onerror=alert(1)>' });
      expect(result).toBe('<span>&lt;img src&#x3D;x onerror&#x3D;alert(1)&gt;</span>');
    });
  });

  describe('Handlebars Triple-Mustache {{{ }}} Unescaped Output', () => {
    test('triple-mustache output passes unescaped HTML through Handlebars layer', () => {
      const template = Handlebars.compile('<div>{{{user_input}}}</div>');
      const result = template({ user_input: '<img src="valid.png" alt="test">' });
      expect(result).toBe('<div><img src="valid.png" alt="test"></div>');
    });

    test('triple-mustache output preserves unescaped script and img tags in template string', () => {
      const template = Handlebars.compile('<div>{{{malicious_input}}}</div>');
      const result = template({ malicious_input: '<script>alert("xss")</script><img src=x onerror=alert(1)>' });
      // Confirms Handlebars does not encode special chars when using {{{ }}}
      expect(result).toBe('<div><script>alert("xss")</script><img src=x onerror=alert(1)></div>');
    });

    test('double-brace vs triple-brace comparison verifies deliberate unescape semantic', () => {
      const doubleTemplate = Handlebars.compile('{{input}}');
      const tripleTemplate = Handlebars.compile('{{{input}}}');
      const payload = '<b>Bold</b> & <script>';

      expect(doubleTemplate({ input: payload })).toBe('&lt;b&gt;Bold&lt;/b&gt; &amp; &lt;script&gt;');
      expect(tripleTemplate({ input: payload })).toBe('<b>Bold</b> & <script>');
    });

    test('renders HandlebarsViewer with triple-mustache template without throwing', async () => {
      const templateSource = '<div class="card">{{{data.[0].formatted_html}}}</div>';
      const data = [{ formatted_html: '<span><strong>$1,250,000</strong> Revenue</span>' }];

      const { container } = render(<HandlebarsViewer templateSource={templateSource} data={{ data }} />);
      await waitFor(() => {
        expect(container.textContent).toContain('$1,250,000');
      });
    });
  });

  describe('Handlebars Component & Viewer Rendering', () => {
    test('renders template with data cleanly without errors', async () => {
      const templateSource = '### KPI: {{data.[0].metric_name}} - {{data.[0].metric_value}}';
      const data = [{ metric_name: 'Total Revenue', metric_value: '$1,250,000' }];

      render(<HandlebarsViewer templateSource={templateSource} data={{ data }} />);
      await waitFor(() => {
        expect(screen.getByText(/Total Revenue/)).toBeInTheDocument();
      });
    });

    test('renders compilation error message in styled pre block when template syntax is invalid', () => {
      const templateSource = '{{#unclosedTag}}Some Content';
      const data = [{ metric_name: 'Total Revenue' }];

      render(<HandlebarsViewer templateSource={templateSource} data={{ data }} />);
      const pre = document.querySelector('pre');
      expect(pre).toBeTruthy();
      expect(pre?.textContent).toContain('Expecting');
    });

    test('renders full Handlebars chart component with custom CSS and formData', async () => {
      const formData = {
        datasource: '28__table',
        viz_type: 'handlebars',
        handlebarsTemplate: '<div class="kpi-card"><h3>{{data.[0].region}}</h3><p>{{data.[0].sales}}</p></div>',
        styleTemplate: '.kpi-card { background-color: #f0f0f0; border-radius: 8px; }',
      };
      const data = [{ __timestamp: null, region: 'North America', sales: '$98,500' }];

      const { container } = render(
        <HandlebarsComponent
          formData={formData as any}
          data={data}
          height={300}
          width={400}
        />,
      );

      await waitFor(() => {
        expect(container.querySelector('div')).toBeTruthy();
      });
    });
  });
});

