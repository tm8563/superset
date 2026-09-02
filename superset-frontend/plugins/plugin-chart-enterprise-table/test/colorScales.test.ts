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
  parseColor,
  rgbToHex,
  sRgbToLinear,
  getRelativeLuminance,
  getContrastRatio,
  getContrastTextColor,
  interpolateMultiColor,
  computeHeatMapColor,
  DEFAULT_SEQUENTIAL_PALETTE,
  DEFAULT_DIVERGING_PALETTE,
} from '../src/colorScales';
import { HeatMapConfig } from '../src/types';

describe('Highlight Table / Heat Map Color Scales Engine', () => {
  describe('Color Parsing & Hex Conversion', () => {
    test('parses 3-digit and 6-digit hex strings correctly', () => {
      expect(parseColor('#FFF')).toEqual({ r: 255, g: 255, b: 255 });
      expect(parseColor('#000000')).toEqual({ r: 0, g: 0, b: 0 });
      expect(parseColor('#FF0000')).toEqual({ r: 255, g: 0, b: 0 });
    });

    test('parses rgb() strings correctly', () => {
      expect(parseColor('rgb(100, 150, 200)')).toEqual({ r: 100, g: 150, b: 200 });
    });

    test('parses named colors correctly', () => {
      expect(parseColor('white')).toEqual({ r: 255, g: 255, b: 255 });
      expect(parseColor('black')).toEqual({ r: 0, g: 0, b: 0 });
    });

    test('converts RGB numbers to standardized #RRGGBB hex string', () => {
      expect(rgbToHex(255, 255, 255)).toBe('#FFFFFF');
      expect(rgbToHex(0, 0, 0)).toBe('#000000');
      expect(rgbToHex(255, 0, 0)).toBe('#FF0000');
      expect(rgbToHex(0, 255, 0)).toBe('#00FF00');
      expect(rgbToHex(0, 0, 255)).toBe('#0000FF');
    });
  });

  describe('WCAG 2.1 Relative Luminance & Text Contrast Calculation', () => {
    test('sRgbToLinear correctly applies gamma correction curve', () => {
      expect(sRgbToLinear(0)).toBe(0);
      expect(sRgbToLinear(255)).toBe(1);
      // Value <= 0.04045 * 255 (= 10.31) uses linear segment / 12.92
      expect(sRgbToLinear(10)).toBeCloseTo(10 / 255 / 12.92, 5);
      // Value > 10.31 uses power function ((c + 0.055) / 1.055)^2.4
      expect(sRgbToLinear(128)).toBeCloseTo(Math.pow((128 / 255 + 0.055) / 1.055, 2.4), 5);
    });

    test('getRelativeLuminance matches standard sRGB coefficients', () => {
      expect(getRelativeLuminance(0, 0, 0)).toBe(0);
      expect(getRelativeLuminance(255, 255, 255)).toBe(1);
      // Pure Red
      expect(getRelativeLuminance(255, 0, 0)).toBeCloseTo(0.2126, 4);
      // Pure Green
      expect(getRelativeLuminance(0, 255, 0)).toBeCloseTo(0.7152, 4);
      // Pure Blue
      expect(getRelativeLuminance(0, 0, 255)).toBeCloseTo(0.0722, 4);
    });

    test('getContrastRatio computes (L1+0.05)/(L2+0.05)', () => {
      expect(getContrastRatio(1.0, 0.0)).toBeCloseTo(21.0, 1);
      expect(getContrastRatio(0.0, 1.0)).toBeCloseTo(21.0, 1);
      expect(getContrastRatio(0.5, 0.5)).toBeCloseTo(1.0, 1);
    });

    test('returns light text (#ffffff) for dark backgrounds', () => {
      expect(getContrastTextColor('#000000')).toBe('#ffffff');
      expect(getContrastTextColor('#084594')).toBe('#ffffff'); // Dark blue
      expect(getContrastTextColor('#67001f')).toBe('#ffffff'); // Dark red
      expect(getContrastTextColor('#006837')).toBe('#ffffff'); // Dark green
    });

    test('returns dark text (#1f1f1f) for light backgrounds', () => {
      expect(getContrastTextColor('#ffffff')).toBe('#1f1f1f');
      expect(getContrastTextColor('#f7fbff')).toBe('#1f1f1f'); // Light blue
      expect(getContrastTextColor('#fee08b')).toBe('#1f1f1f'); // Light yellow
      expect(getContrastTextColor('#d9ef8b')).toBe('#1f1f1f'); // Light green
    });
  });

  describe('Multi-Color Interpolation', () => {
    test('interpolates color stops smoothly along [0, 1]', () => {
      const palette = ['#000000', '#ffffff'];
      expect(interpolateMultiColor(palette, 0)).toBe('#000000');
      expect(interpolateMultiColor(palette, 1)).toBe('#FFFFFF');
      expect(interpolateMultiColor(palette, 0.5)).toBe('#808080');
    });

    test('clamps values beyond [0, 1]', () => {
      const palette = ['#000000', '#ffffff'];
      expect(interpolateMultiColor(palette, -0.5)).toBe('#000000');
      expect(interpolateMultiColor(palette, 1.5)).toBe('#FFFFFF');
    });
  });

  describe('Continuous Heat Map Color Computation', () => {
    test('computes sequential gradient background and contrast text color', () => {
      const config: HeatMapConfig = {
        colorMode: 'sequential',
        scope: 'per_column',
      };

      const minColor = computeHeatMapColor(0, 0, 100, config);
      expect(minColor).not.toBeNull();
      expect(minColor?.backgroundColor).toBe(DEFAULT_SEQUENTIAL_PALETTE[0].toUpperCase());
      expect(minColor?.textColor).toBe('#1f1f1f');

      const maxColor = computeHeatMapColor(100, 0, 100, config);
      expect(maxColor).not.toBeNull();
      expect(maxColor?.backgroundColor).toBe(
        DEFAULT_SEQUENTIAL_PALETTE[DEFAULT_SEQUENTIAL_PALETTE.length - 1].toUpperCase(),
      );
      expect(maxColor?.textColor).toBe('#ffffff');
    });

    test('computes diverging gradient with distinct hues above/below midpoint', () => {
      const config: HeatMapConfig = {
        colorMode: 'diverging',
        scope: 'per_column',
        midpoint: 0,
      };

      // Negative value (-100) -> Strong red
      const negColor = computeHeatMapColor(-100, -100, 100, config);
      expect(negColor).not.toBeNull();
      expect(negColor?.backgroundColor).toBe(DEFAULT_DIVERGING_PALETTE[0].toUpperCase());

      // Midpoint value (0) -> Center white
      const midColor = computeHeatMapColor(0, -100, 100, config);
      expect(midColor).not.toBeNull();
      expect(midColor?.backgroundColor).toBe('#FFFFFF');
      expect(midColor?.textColor).toBe('#1f1f1f');

      // Positive value (100) -> Strong green
      const posColor = computeHeatMapColor(100, -100, 100, config);
      expect(posColor).not.toBeNull();
      expect(posColor?.backgroundColor).toBe(
        DEFAULT_DIVERGING_PALETTE[DEFAULT_DIVERGING_PALETTE.length - 1].toUpperCase(),
      );
    });

    test('returns null when colorMode is none or value is non-numeric', () => {
      const noneConfig: HeatMapConfig = { colorMode: 'none', scope: 'per_column' };
      expect(computeHeatMapColor(50, 0, 100, noneConfig)).toBeNull();

      const seqConfig: HeatMapConfig = { colorMode: 'sequential', scope: 'per_column' };
      expect(computeHeatMapColor(null, 0, 100, seqConfig)).toBeNull();
      expect(computeHeatMapColor(undefined, 0, 100, seqConfig)).toBeNull();
      expect(computeHeatMapColor(NaN, 0, 100, seqConfig)).toBeNull();
    });
  });
});
