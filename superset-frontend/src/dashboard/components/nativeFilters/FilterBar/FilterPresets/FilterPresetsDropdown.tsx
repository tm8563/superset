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
import { FC, useState, useEffect, useCallback, useMemo } from 'react';
import { useDispatch, useSelector } from 'react-redux';
import { t } from '@apache-superset/core/translation';
import { styled, css, useTheme } from '@apache-superset/core/theme';
import {
  Badge,
  Button,
  EmptyState,
  Input,
  Loading,
  Popover,
  Popconfirm,
  Space,
  Tabs,
  Tag,
  Tooltip,
} from '@superset-ui/core/components';
import { Icons } from '@superset-ui/core/components/Icons';
import {
  ChartCustomization,
  ChartCustomizationDivider,
  DataMaskStateWithId,
  Divider,
  Filter,
} from '@superset-ui/core';
import { RootState } from 'src/dashboard/types';
import { updateDataMask } from 'src/dataMask/actions';
import { useFilters } from '../state';
import {
  DashboardFilterPreset,
  FilterDriftDetail,
} from './types';
import {
  computeFilterConfigChecksum,
  detectFilterDrift,
  generateFilterSummary,
  sanitizePresetDataMask,
} from './utils';
import {
  deleteFilterPreset,
  fetchFilterPresets,
  updateFilterPreset,
} from './api';
import { SavePresetModal } from './SavePresetModal';
import { DriftWarningModal } from './DriftWarningModal';

type AnyFilterItem =
  | Filter
  | Divider
  | ChartCustomization
  | ChartCustomizationDivider;

const DropdownWrapper = styled.div`
  display: flex;
  align-items: center;
`;

const PopoverContent = styled.div`
  width: 380px;
  max-height: 480px;
  display: flex;
  flex-direction: column;
`;

const PopoverHeader = styled.div`
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding-bottom: ${({ theme }) => theme.sizeUnit * 2}px;
  border-bottom: 1px solid ${({ theme }) => theme.colorSplit};
  margin-bottom: ${({ theme }) => theme.sizeUnit * 2}px;

  h4 {
    margin: 0;
    font-weight: ${({ theme }) => theme.fontWeightStrong};
    font-size: ${({ theme }) => theme.fontSize}px;
  }
`;

const PresetListContainer = styled.div`
  overflow-y: auto;
  max-height: 320px;
  display: flex;
  flex-direction: column;
  gap: ${({ theme }) => theme.sizeUnit * 2}px;
  padding-right: ${({ theme }) => theme.sizeUnit}px;
`;

const PresetItemCard = styled.div<{ isActive?: boolean }>`
  border: 1px solid ${({ theme }) => theme.colorBorderSecondary};
  border-radius: ${({ theme }) => theme.borderRadius}px;
  padding: ${({ theme }) => theme.sizeUnit * 2}px;
  background: ${({ theme }) => theme.colorBgContainer};
  transition: all 0.2s ease;

  &:hover {
    border-color: ${({ theme }) => theme.colorPrimary};
    box-shadow: 0 2px 6px rgba(0, 0, 0, 0.06);
  }
`;

const PresetItemHeader = styled.div`
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: ${({ theme }) => theme.sizeUnit}px;
`;

const PresetName = styled.span`
  font-weight: ${({ theme }) => theme.fontWeightStrong};
  font-size: ${({ theme }) => theme.fontSize}px;
  word-break: break-word;
`;

const PresetMeta = styled.div`
  font-size: ${({ theme }) => theme.fontSizeSM}px;
  color: ${({ theme }) => theme.colorTextSecondary};
  margin-bottom: ${({ theme }) => theme.sizeUnit * 2}px;
`;

const PresetActions = styled.div`
  display: flex;
  justify-content: space-between;
  align-items: center;
`;

export const FilterPresetsDropdown: FC = () => {
  const theme = useTheme();
  const dispatch = useDispatch();

  const dashboardId = useSelector<RootState, number>(
    ({ dashboardInfo }) => dashboardInfo.id,
  );
  const canEdit = useSelector<RootState, boolean>(
    ({ dashboardInfo }) => Boolean(dashboardInfo.dash_edit_perm),
  );
  const dataMask = useSelector<RootState, DataMaskStateWithId>(
    state => state.dataMask,
  );

  const filters = useFilters() as Record<string, AnyFilterItem>;

  const [isOpen, setIsOpen] = useState(false);
  const [presets, setPresets] = useState<DashboardFilterPreset[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');
  const [activeTab, setActiveTab] = useState<'personal' | 'shared'>('personal');

  // Modals state
  const [isSaveModalVisible, setIsSaveModalVisible] = useState(false);
  const [driftModalState, setDriftModalState] = useState<{
    isVisible: boolean;
    preset: DashboardFilterPreset | null;
    driftDetail: FilterDriftDetail | null;
  }>({
    isVisible: false,
    preset: null,
    driftDetail: null,
  });

  const loadPresets = useCallback(async () => {
    if (!dashboardId) return;
    setIsLoading(true);
    try {
      const result = await fetchFilterPresets(dashboardId);
      setPresets(result);
    } catch {
      // Error handled in API layer
    } finally {
      setIsLoading(false);
    }
  }, [dashboardId]);

  useEffect(() => {
    if (isOpen) {
      loadPresets();
    }
  }, [isOpen, loadPresets]);

  const personalPresets = useMemo(
    () =>
      presets.filter(
        p =>
          !p.is_shared &&
          p.name.toLowerCase().includes(searchQuery.toLowerCase()),
      ),
    [presets, searchQuery],
  );

  const sharedPresets = useMemo(
    () =>
      presets.filter(
        p =>
          p.is_shared &&
          p.name.toLowerCase().includes(searchQuery.toLowerCase()),
      ),
    [presets, searchQuery],
  );

  const applyPresetDataMask = useCallback(
    (preset: DashboardFilterPreset, sanitize = false) => {
      const sourceMask = sanitize
        ? sanitizePresetDataMask(preset.data_mask, filters)
        : preset.data_mask;

      Object.entries(sourceMask).forEach(([filterId, mask]) => {
        dispatch(updateDataMask(filterId, mask));
      });
      setIsOpen(false);
    },
    [dispatch, filters],
  );

  const handleApplyClick = useCallback(
    (preset: DashboardFilterPreset) => {
      const driftDetail = detectFilterDrift(preset, filters);
      if (driftDetail.hasDrift) {
        setDriftModalState({
          isVisible: true,
          preset,
          driftDetail,
        });
      } else {
        applyPresetDataMask(preset, false);
      }
    },
    [filters, applyPresetDataMask],
  );

  const handleRefreshPreset = useCallback(
    async (preset: DashboardFilterPreset) => {
      try {
        const checksum = computeFilterConfigChecksum(filters);
        const summary = generateFilterSummary(filters);
        const updated = await updateFilterPreset(dashboardId, preset.id, {
          data_mask: dataMask,
          filter_config_checksum: checksum,
          filter_summary: summary,
        });
        setPresets(prev => prev.map(p => (p.id === updated.id ? updated : p)));
        setDriftModalState({ isVisible: false, preset: null, driftDetail: null });
        applyPresetDataMask(updated, false);
      } catch {
        // Error handled in API layer
      }
    },
    [dashboardId, dataMask, filters, applyPresetDataMask],
  );

  const handleDeletePreset = useCallback(
    async (presetId: string) => {
      try {
        await deleteFilterPreset(dashboardId, presetId);
        setPresets(prev => prev.filter(p => p.id !== presetId));
      } catch {
        // Error handled in API layer
      }
    },
    [dashboardId],
  );

  const renderPresetList = (items: DashboardFilterPreset[]) => {
    if (isLoading) {
      return (
        <div
          css={css`
            padding: ${theme.sizeUnit * 8}px;
            text-align: center;
          `}
        >
          <Loading position="inline-centered" size="s" muted />
        </div>
      );
    }

    if (items.length === 0) {
      return (
        <EmptyState
          size="small"
          title={t('No saved views found')}
          description={t('Save your current filter selections as a preset.')}
        />
      );
    }

    return (
      <PresetListContainer>
        {items.map(preset => {
          const drift = detectFilterDrift(preset, filters);
          const canManage = Boolean(
            preset.is_owner || (preset.is_shared && canEdit),
          );

          return (
            <PresetItemCard key={preset.id} data-test={`preset-card-${preset.id}`}>
              <PresetItemHeader>
                <PresetName>{preset.name}</PresetName>
                <Space size={4}>
                  {drift.hasDrift && (
                    <Tooltip
                      title={t(
                        'Dashboard filters have changed since this view was saved. Click Apply to inspect.',
                      )}
                    >
                      <Tag color="warning" icon={<Icons.WarningOutlined />}>
                        {t('Drifted')}
                      </Tag>
                    </Tooltip>
                  )}
                  {preset.is_shared ? (
                    <Tag color="blue">{t('Shared')}</Tag>
                  ) : (
                    <Tag>{t('Personal')}</Tag>
                  )}
                </Space>
              </PresetItemHeader>

              {preset.description && (
                <div
                  css={css`
                    font-size: ${theme.fontSizeSM}px;
                    color: ${theme.colorTextSecondary};
                    margin-bottom: ${theme.sizeUnit}px;
                  `}
                >
                  {preset.description}
                </div>
              )}

              <PresetMeta>
                {preset.created_by?.username && (
                  <span>
                    {t('By %s', preset.created_by.username)}
                    {' • '}
                  </span>
                )}
                <span>
                  {t(
                    '%s filter(s)',
                    Object.keys(preset.data_mask || {}).length,
                  )}
                </span>
              </PresetMeta>

              <PresetActions>
                <Button
                  buttonSize="xsmall"
                  buttonStyle="primary"
                  onClick={() => handleApplyClick(preset)}
                  data-test={`apply-preset-${preset.id}`}
                >
                  {t('Apply View')}
                </Button>

                <Space size={4}>
                  {canManage && (
                    <Tooltip title={t('Update view with current filter values')}>
                      <Button
                        buttonSize="xsmall"
                        buttonStyle="secondary"
                        onClick={() => handleRefreshPreset(preset)}
                        data-test={`refresh-preset-${preset.id}`}
                      >
                        <Icons.ReloadOutlined iconSize="s" />
                      </Button>
                    </Tooltip>
                  )}

                  {canManage && (
                    <Popconfirm
                      title={t('Delete this saved view?')}
                      okText={t('Delete')}
                      cancelText={t('Cancel')}
                      onConfirm={() => handleDeletePreset(preset.id)}
                    >
                      <Button
                        buttonSize="xsmall"
                        buttonStyle="link"
                        danger
                        data-test={`delete-preset-${preset.id}`}
                      >
                        <Icons.DeleteOutlined iconSize="s" />
                      </Button>
                    </Popconfirm>
                  )}
                </Space>
              </PresetActions>
            </PresetItemCard>
          );
        })}
      </PresetListContainer>
    );
  };

  const totalPresetsCount = presets.length;

  return (
    <DropdownWrapper>
      <Popover
        open={isOpen}
        onOpenChange={setIsOpen}
        trigger="click"
        placement="bottomLeft"
        content={
          <PopoverContent>
            <PopoverHeader>
              <h4>{t('Saved Views / Presets')}</h4>
              <Button
                buttonSize="xsmall"
                buttonStyle="primary"
                onClick={() => {
                  setIsOpen(false);
                  setIsSaveModalVisible(true);
                }}
                data-test="save-current-view-btn"
              >
                <Icons.PlusOutlined iconSize="s" /> {t('Save View')}
              </Button>
            </PopoverHeader>

            <Input
              placeholder={t('Search saved views...')}
              value={searchQuery}
              onChange={e => setSearchQuery(e.target.value)}
              prefix={<Icons.SearchOutlined iconSize="m" />}
              allowClear
              css={css`
                margin-bottom: ${theme.sizeUnit * 2}px;
              `}
            />

            <Tabs
              activeKey={activeTab}
              onChange={k => setActiveTab(k as 'personal' | 'shared')}
              items={[
                {
                  key: 'personal',
                  label: (
                    <span>
                      {t('Personal')}{' '}
                      <Badge
                        count={personalPresets.length}
                        size="small"
                        overflowCount={99}
                      />
                    </span>
                  ),
                  children: renderPresetList(personalPresets),
                },
                {
                  key: 'shared',
                  label: (
                    <span>
                      {t('Shared')}{' '}
                      <Badge
                        count={sharedPresets.length}
                        size="small"
                        overflowCount={99}
                      />
                    </span>
                  ),
                  children: renderPresetList(sharedPresets),
                },
              ]}
            />
          </PopoverContent>
        }
      >
        <Button
          buttonStyle="link"
          buttonSize="xsmall"
          css={css`
            padding: 0 ${theme.sizeUnit}px;
            display: flex;
            align-items: center;
            gap: ${theme.sizeUnit}px;
            color: ${theme.colorTextSecondary};

            &:hover {
              color: ${theme.colorPrimary};
            }
          `}
          data-test="filter-presets-dropdown-trigger"
        >
          <Icons.StarOutlined iconSize="m" />
          <span>{t('Saved Views')}</span>
          {totalPresetsCount > 0 && (
            <Badge
              count={totalPresetsCount}
              size="small"
              overflowCount={99}
              css={css`
                .ant-badge-count {
                  background-color: ${theme.colorBgContainer};
                  color: ${theme.colorTextSecondary};
                  border: 1px solid ${theme.colorBorder};
                  box-shadow: none;
                }
              `}
            />
          )}
        </Button>
      </Popover>

      <SavePresetModal
        isVisible={isSaveModalVisible}
        onClose={() => setIsSaveModalVisible(false)}
        onSaveSuccess={saved => {
          setPresets(prev => [saved, ...prev]);
        }}
        dashboardId={dashboardId}
        dataMask={dataMask}
        filters={filters}
        canEdit={canEdit}
      />

      <DriftWarningModal
        isVisible={driftModalState.isVisible}
        preset={driftModalState.preset}
        driftDetail={driftModalState.driftDetail}
        onProceed={() => {
          if (driftModalState.preset) {
            applyPresetDataMask(driftModalState.preset, true);
          }
          setDriftModalState({ isVisible: false, preset: null, driftDetail: null });
        }}
        onRefreshPreset={() => {
          if (driftModalState.preset) {
            handleRefreshPreset(driftModalState.preset);
          }
        }}
        onCancel={() =>
          setDriftModalState({ isVisible: false, preset: null, driftDetail: null })
        }
        canRefresh={Boolean(
          driftModalState.preset?.is_owner ||
            (driftModalState.preset?.is_shared && canEdit),
        )}
      />
    </DropdownWrapper>
  );
};

export default FilterPresetsDropdown;
