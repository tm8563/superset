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

import { getSequentialSchemeRegistry, SequentialScheme } from '@superset-ui/core';
import { HeatMapConfig, HeatMapColorMode } from './types';

export interface RgbColor {
  r: number;
  g: number;
  b: number;
}

// Built-in fallback palettes when registry lookup is not matched
export const DEFAULT_SEQUENTIAL_PALETTE: string[] = [
  '#f7fbff',
  '#deebf7',
  '#c6dbef',
  '#9ecae1',
  '#6baed6',
  '#4292c6',
  '#2171b5',
  '#084594',
];

export const DEFAULT_DIVERGING_PALETTE: string[] = [
  '#d73027', // Strong Red (low / negative)
  '#f46d43',
  '#fdae61',
  '#fee08b',
  '#ffffff', // White (midpoint)
  '#d9ef8b',
  '#a6d96a',
  '#66bd63',
  '#1a9850', // Strong Green (high / positive)
];

/**
 * Parses a hex string (#RGB, #RRGGBB) or rgb() string into RgbColor numbers.
 */
export function parseColor(colorStr: string): RgbColor {
  if (!colorStr) {
    return { r: 255, g: 255, b: 255 };
  }

  const trimmed = colorStr.trim();

  // Handle rgb(r, g, b)
  if (trimmed.startsWith('rgb')) {
    const match = trimmed.match(/rgb\s*\(\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)\s*\)/i);
    if (match) {
      return {
        r: Math.max(0, Math.min(255, parseInt(match[1], 10))),
        g: Math.max(0, Math.min(255, parseInt(match[2], 10))),
        b: Math.max(0, Math.min(255, parseInt(match[3], 10))),
      };
    }
  }

  // Handle named colors
  if (trimmed.toLowerCase() === 'white') return { r: 255, g: 255, b: 255 };
  if (trimmed.toLowerCase() === 'black') return { r: 0, g: 0, b: 0 };
  if (trimmed.toLowerCase() === 'red') return { r: 255, g: 0, b: 0 };
  if (trimmed.toLowerCase() === 'green') return { r: 0, g: 128, b: 0 };
  if (trimmed.toLowerCase() === 'blue') return { r: 0, g: 0, b: 255 };
  if (trimmed.toLowerCase() === 'yellow') return { r: 255, g: 255, b: 0 };

  // Handle hex string
  let hex = trimmed.replace(/^#/, '');
  if (hex.length === 3) {
    hex = hex[0] + hex[0] + hex[1] + hex[1] + hex[2] + hex[2];
  }

  if (hex.length === 6) {
    const num = parseInt(hex, 16);
    if (!Number.isNaN(num)) {
      return {
        r: (num >> 16) & 255,
        g: (num >> 8) & 255,
        b: num & 255,
      };
    }
  }

  return { r: 255, g: 255, b: 255 };
}

/**
 * Converts RGB components to a standardized #RRGGBB hex string.
 */
export function rgbToHex(r: number, g: number, b: number): string {
  const clampR = Math.max(0, Math.min(255, Math.round(r)));
  const clampG = Math.max(0, Math.min(255, Math.round(g)));
  const clampB = Math.max(0, Math.min(255, Math.round(b)));
  return `#${((1 << 24) + (clampR << 16) + (clampG << 8) + clampB)
    .toString(16)
    .slice(1)
    .toUpperCase()}`;
}

/**
 * Calculates WCAG 2.1 gamma-corrected relative luminance for an sRGB color component.
 */
export function sRgbToLinear(c: number): number {
  const cNorm = Math.max(0, Math.min(255, c)) / 255;
  return cNorm <= 0.04045
    ? cNorm / 12.92
    : Math.pow((cNorm + 0.055) / 1.055, 2.4);
}

/**
 * Calculates WCAG 2.1 relative luminance (L) in the sRGB color space.
 * https://www.w3.org/TR/WCAG21/#dfn-relative-luminance
 */
export function getRelativeLuminance(r: number, g: number, b: number): number {
  const R = sRgbToLinear(r);
  const G = sRgbToLinear(g);
  const B = sRgbToLinear(b);
  return 0.2126 * R + 0.7152 * G + 0.0722 * B;
}

/**
 * Calculates WCAG 2.1 contrast ratio between two relative luminance values.
 * https://www.w3.org/TR/WCAG21/#dfn-contrast-ratio
 */
export function getContrastRatio(l1: number, l2: number): number {
  const lighter = Math.max(l1, l2);
  const darker = Math.min(l1, l2);
  return (lighter + 0.05) / (darker + 0.05);
}

/**
 * Calculates WCAG 2.1 gamma-corrected relative luminance and chooses the maximum contrast text color.
 * Returns '#ffffff' (light text) or '#1f1f1f' (dark text) based on which provides the highest contrast ratio.
 */
export function getContrastTextColor(backgroundColor: string): string {
  const { r, g, b } = parseColor(backgroundColor);
  const bgLuminance = getRelativeLuminance(r, g, b);
  const whiteLuminance = 1.0;
  // #1f1f1f: r=31, g=31, b=31
  const darkLuminance = getRelativeLuminance(31, 31, 31);

  const contrastWithWhite = getContrastRatio(bgLuminance, whiteLuminance);
  const contrastWithDark = getContrastRatio(bgLuminance, darkLuminance);

  return contrastWithWhite >= contrastWithDark ? '#ffffff' : '#1f1f1f';
}

/**
 * Retrieves palette color array from Superset's SequentialSchemeRegistry or built-in defaults.
 */
export function getPaletteColors(
  paletteId?: string,
  mode: HeatMapColorMode = 'sequential',
): string[] {
  if (paletteId) {
    try {
      const registry = getSequentialSchemeRegistry();
      const scheme = registry.get(paletteId) as SequentialScheme | undefined;
      if (scheme && scheme.colors && scheme.colors.length > 0) {
        return scheme.colors;
      }
    } catch {
      // Fallback to defaults
    }
  }

  return mode === 'diverging'
    ? DEFAULT_DIVERGING_PALETTE
    : DEFAULT_SEQUENTIAL_PALETTE;
}

/**
 * Linearly interpolates between an array of color stops for a normalized position t in [0, 1].
 */
export function interpolateMultiColor(colors: string[], t: number): string {
  if (!colors || colors.length === 0) return '#ffffff';
  if (colors.length === 1) return colors[0];

  const clampedT = Math.max(0, Math.min(1, t));
  const segmentCount = colors.length - 1;
  const rawIndex = clampedT * segmentCount;
  const index = Math.min(Math.floor(rawIndex), segmentCount - 1);
  const localT = rawIndex - index;

  const c1 = parseColor(colors[index]);
  const c2 = parseColor(colors[index + 1]);

  const r = c1.r + (c2.r - c1.r) * localT;
  const g = c1.g + (c2.g - c1.g) * localT;
  const b = c1.b + (c2.b - c1.b) * localT;

  return rgbToHex(r, g, b);
}

/**
 * Computes the continuous heat map background color for a numeric value.
 */
export function computeHeatMapColor(
  value: number | null | undefined,
  minVal: number,
  maxVal: number,
  config: HeatMapConfig,
): { backgroundColor: string; textColor: string } | null {
  if (
    value === null ||
    value === undefined ||
    typeof value !== 'number' ||
    Number.isNaN(value) ||
    config.colorMode === 'none'
  ) {
    return null;
  }

  const palette = getPaletteColors(config.palette, config.colorMode);

  if (config.colorMode === 'sequential') {
    const range = maxVal - minVal;
    const t = range > 0 ? (value - minVal) / range : 0.5;
    const bg = interpolateMultiColor(palette, t);
    return {
      backgroundColor: bg,
      textColor: getContrastTextColor(bg),
    };
  }

  if (config.colorMode === 'diverging') {
    const midpoint = config.midpoint ?? 0;
    let t = 0.5;

    if (value >= midpoint) {
      const upperRange = maxVal - midpoint;
      const upperT = upperRange > 0 ? (value - midpoint) / upperRange : 0;
      // Map midpoint to maxVal across upper half [0.5, 1.0]
      t = 0.5 + 0.5 * Math.min(1, Math.max(0, upperT));
    } else {
      const lowerRange = midpoint - minVal;
      const lowerT = lowerRange > 0 ? (midpoint - value) / lowerRange : 0;
      // Map minVal to midpoint across lower half [0.0, 0.5]
      t = 0.5 - 0.5 * Math.min(1, Math.max(0, lowerT));
    }

    const bg = interpolateMultiColor(palette, t);
    return {
      backgroundColor: bg,
      textColor: getContrastTextColor(bg),
    };
  }

  return null;
}
