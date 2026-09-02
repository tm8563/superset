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
import { FC, useState, useCallback, useMemo } from 'react';
import { t } from '@apache-superset/core/translation';
import { styled, css } from '@apache-superset/core/theme';
import {
  Button,
  Form,
  Input,
  Modal,
  Radio,
  Tooltip,
} from '@superset-ui/core/components';
import {
  ChartCustomization,
  ChartCustomizationDivider,
  DataMaskStateWithId,
  Divider,
  Filter,
} from '@superset-ui/core';
import { createFilterPreset } from './api';
import { computeFilterConfigChecksum, generateFilterSummary } from './utils';
import { DashboardFilterPreset } from './types';

interface SavePresetModalProps {
  isVisible: boolean;
  onClose: () => void;
  onSaveSuccess: (preset: DashboardFilterPreset) => void;
  dashboardId: string | number;
  dataMask: DataMaskStateWithId;
  filters: Record<
    string,
    Filter | Divider | ChartCustomization | ChartCustomizationDivider
  >;
  canEdit: boolean;
}

const StyledForm = styled(Form)`
  .ant-form-item-label > label {
    font-weight: ${({ theme }) => theme.fontWeightStrong};
  }
`;

const ScopeOptionContainer = styled.div`
  display: flex;
  flex-direction: column;
  gap: ${({ theme }) => theme.sizeUnit}px;
`;

const ScopeDescription = styled.span`
  color: ${({ theme }) => theme.colorTextSecondary};
  font-size: ${({ theme }) => theme.fontSizeSM}px;
  margin-left: ${({ theme }) => theme.sizeUnit * 6}px;
`;

export const SavePresetModal: FC<SavePresetModalProps> = ({
  isVisible,
  onClose,
  onSaveSuccess,
  dashboardId,
  dataMask,
  filters,
  canEdit,
}) => {
  const [name, setName] = useState('');
  const [description, setDescription] = useState('');
  const [isShared, setIsShared] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  const activeFiltersCount = useMemo(() => {
    return Object.values(dataMask).filter(
      mask =>
        mask?.filterState?.value !== undefined ||
        mask?.ownState?.column !== undefined,
    ).length;
  }, [dataMask]);

  const handleSubmit = useCallback(async () => {
    const trimmedName = name.trim();
    if (!trimmedName) {
      setErrorMessage(t('Preset name is required'));
      return;
    }

    setErrorMessage(null);
    setIsSubmitting(true);

    try {
      const checksum = computeFilterConfigChecksum(filters);
      const summary = generateFilterSummary(filters);

      const savedPreset = await createFilterPreset(dashboardId, {
        name: trimmedName,
        description: description.trim() || undefined,
        is_shared: isShared,
        filter_config_checksum: checksum,
        filter_summary: summary,
        data_mask: dataMask,
      });

      setName('');
      setDescription('');
      setIsShared(false);
      onSaveSuccess(savedPreset);
      onClose();
    } catch (err: unknown) {
      const msg =
        err instanceof Error ? err.message : t('Failed to save filter preset');
      setErrorMessage(msg);
    } finally {
      setIsSubmitting(false);
    }
  }, [
    name,
    description,
    isShared,
    filters,
    dashboardId,
    dataMask,
    onSaveSuccess,
    onClose,
  ]);

  return (
    <Modal
      title={t('Save Filter View / Preset')}
      show={isVisible}
      onHide={onClose}
      footer={[
        <Button key="cancel" onClick={onClose} disabled={isSubmitting}>
          {t('Cancel')}
        </Button>,
        <Button
          key="submit"
          buttonStyle="primary"
          onClick={handleSubmit}
          loading={isSubmitting}
          data-test="save-filter-preset-submit"
        >
          {t('Save View')}
        </Button>,
      ]}
      destroyOnHidden
    >
      <StyledForm layout="vertical">
        <Form.Item
          label={t('View Name')}
          required
          help={errorMessage || undefined}
          validateStatus={errorMessage ? 'error' : undefined}
        >
          <Input
            placeholder={t('e.g., North America - Last 7 Days')}
            value={name}
            onChange={e => {
              setName(e.target.value);
              if (errorMessage) setErrorMessage(null);
            }}
            autoFocus
            maxLength={250}
            data-test="preset-name-input"
          />
        </Form.Item>

        <Form.Item label={t('Description (Optional)')}>
          <Input.TextArea
            placeholder={t('Add notes about what this view filters...')}
            value={description}
            onChange={e => setDescription(e.target.value)}
            rows={2}
            maxLength={1000}
          />
        </Form.Item>

        <Form.Item label={t('Sharing & Visibility')}>
          <Radio.Group
            value={isShared}
            onChange={e => setIsShared(e.target.value)}
            css={css`
              width: 100%;
            `}
          >
            <ScopeOptionContainer>
              <Radio value={false}>
                <strong>{t('Personal (Only You)')}</strong>
              </Radio>
              <ScopeDescription>
                {t('This saved view will be private and visible only to you.')}
              </ScopeDescription>

              <Tooltip
                title={
                  !canEdit
                    ? t(
                        'Dashboard edit permission is required to create a Shared view.',
                      )
                    : undefined
                }
              >
                <div>
                  <Radio value={true} disabled={!canEdit}>
                    <strong>{t('Shared (All Dashboard Viewers)')}</strong>
                  </Radio>
                </div>
              </Tooltip>
              <ScopeDescription>
                {t(
                  'Visible to everyone who has access to this dashboard. (Query data is always scoped by each user’s own permissions and RLS).',
                )}
              </ScopeDescription>
            </ScopeOptionContainer>
          </Radio.Group>
        </Form.Item>

        <div
          css={(theme: {
            colorTextSecondary: string;
            fontSizeSM: number;
            sizeUnit: number;
          }) => css`
            color: ${theme.colorTextSecondary};
            font-size: ${theme.fontSizeSM}px;
            margin-top: ${theme.sizeUnit * 2}px;
          `}
        >
          {t(
            'This preset captures current values across %s active filter(s).',
            activeFiltersCount,
          )}
        </div>
      </StyledForm>
    </Modal>
  );
};
