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
import { FC } from 'react';
import { t } from '@apache-superset/core/translation';
import { styled, css } from '@apache-superset/core/theme';
import {
  Button,
  Modal,
  Space,
} from '@superset-ui/core/components';
import { Alert } from '@apache-superset/core/components';
import { Icons } from '@superset-ui/core/components/Icons';
import { DashboardFilterPreset, FilterDriftDetail } from './types';

interface DriftWarningModalProps {
  isVisible: boolean;
  preset: DashboardFilterPreset | null;
  driftDetail: FilterDriftDetail | null;
  onProceed: () => void;
  onRefreshPreset: () => void;
  onCancel: () => void;
  canRefresh: boolean;
}

const FilterList = styled.ul`
  margin: ${({ theme }) => theme.sizeUnit}px 0 0 0;
  padding-left: ${({ theme }) => theme.sizeUnit * 4}px;
  color: ${({ theme }) => theme.colorTextSecondary};
  font-size: ${({ theme }) => theme.fontSizeSM}px;
`;

const SectionHeader = styled.div`
  font-weight: ${({ theme }) => theme.fontWeightStrong};
  font-size: ${({ theme }) => theme.fontSizeSM}px;
  display: flex;
  align-items: center;
  gap: ${({ theme }) => theme.sizeUnit}px;
  margin-top: ${({ theme }) => theme.sizeUnit * 2}px;
`;

export const DriftWarningModal: FC<DriftWarningModalProps> = ({
  isVisible,
  preset,
  driftDetail,
  onProceed,
  onRefreshPreset,
  onCancel,
  canRefresh,
}) => {
  if (!preset || !driftDetail) return null;

  const removedNames = driftDetail.removedFilterNames;
  const hasRemoved = removedNames.length > 0;

  return (
    <Modal
      title={
        <Space>
          <Icons.WarningOutlined />
          <span>{t('Dashboard Filters Changed (View Drift)')}</span>
        </Space>
      }
      show={isVisible}
      onHide={onCancel}
      footer={[
        <Button key="cancel" onClick={onCancel}>
          {t('Cancel')}
        </Button>,
        canRefresh && (
          <Button
            key="refresh"
            onClick={onRefreshPreset}
            data-test="drift-modal-refresh-preset"
          >
            {t('Update View to Current State')}
          </Button>
        ),
        <Button
          key="proceed"
          buttonStyle="primary"
          onClick={onProceed}
          data-test="drift-modal-proceed"
        >
          {t('Apply Compatible Filters')}
        </Button>,
      ]}
      destroyOnHidden
    >
      <Space direction="vertical" size={16} style={{ width: '100%' }}>
        <Alert
          type="warning"
          showIcon
          message={t(
            'This saved view was created before the dashboard filters were modified.',
          )}
          description={t(
            'Some filters in "%s" have been modified or deleted. You can proceed with applying all still-compatible filters or update this view.',
            preset.name,
          )}
        />

        {hasRemoved && (
          <div>
            <SectionHeader
              css={(theme: { colorWarningText: string }) => css`
                color: ${theme.colorWarningText};
              `}
            >
              <Icons.CloseCircleOutlined />
              <span>{t('Skipped Filters (No longer present):')}</span>
            </SectionHeader>
            <FilterList>
              {removedNames.map((name, idx) => (
                <li key={idx}>
                  <strong>{name}</strong>
                </li>
              ))}
            </FilterList>
          </div>
        )}

        <div>
          <SectionHeader
            css={(theme: { colorSuccessText: string }) => css`
              color: ${theme.colorSuccessText};
            `}
          >
            <Icons.CheckCircleOutlined />
            <span>
              {t(
                'Compatible Filters to Apply (%s):',
                driftDetail.compatibleFilterIds.length,
              )}
            </span>
          </SectionHeader>
          <div
            css={(theme: {
              colorTextSecondary: string;
              fontSizeSM: number;
              sizeUnit: number;
            }) => css`
              color: ${theme.colorTextSecondary};
              font-size: ${theme.fontSizeSM}px;
              margin-top: ${theme.sizeUnit}px;
            `}
          >
            {t(
              'All valid matching filter values will be restored and applied to your dashboard charts.',
            )}
          </div>
        </div>
      </Space>
    </Modal>
  );
};
