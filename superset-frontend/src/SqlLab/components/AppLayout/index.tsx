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
import { useDispatch, useSelector } from 'react-redux';
import { noop } from 'lodash-es';
import type { SqlLabRootState } from 'src/SqlLab/types';
import { css, styled } from '@apache-superset/core/theme';
import { FeatureFlag, isFeatureEnabled, useComponentDidUpdate } from '@superset-ui/core';
import { Grid, Splitter } from '@superset-ui/core/components';
import { useViews } from 'src/core';
import useEffectEvent from 'src/hooks/useEffectEvent';
import useStoredSidebarWidth from 'src/components/ResizableSidebar/useStoredSidebarWidth';
import AIStudioScoped from 'src/ai-studio/AIStudioScoped';
import { isAuthenticatedUser } from 'src/utils/getBootstrapData';
import {
  SQL_EDITOR_LEFTBAR_WIDTH,
  SQL_EDITOR_RIGHTBAR_WIDTH,
} from 'src/SqlLab/constants';
import { ViewLocations } from 'src/SqlLab/contributions';
import ViewListExtension from 'src/components/ViewListExtension';
import { toggleLeftBar } from 'src/SqlLab/actions/sqlLab';

import SqlEditorLeftBar from '../SqlEditorLeftBar';
import StatusBar from '../StatusBar';

const AI_STUDIO_SQLLAB_DEFAULT_WIDTH = 420;
const AI_STUDIO_SQLLAB_MIN_WIDTH = 320;

const StyledContainer = styled.div`
  display: flex;
  flex-direction: column;
  height: 100%;

  & .ant-splitter-panel:not(.sqllab-body):not(.queryPane) {
    background-color: ${({ theme }) => theme.colorBgBase};
  }

  & .sqllab-body {
    flex-grow: 1 !important;
    padding-top: ${({ theme }) => theme.sizeUnit * 2.5}px;
  }
`;

const StyledSidebar = styled.div`
  position: relative;
  padding: ${({ theme }) => theme.sizeUnit * 2.5}px 0;
  margin: 0 ${({ theme }) => theme.sizeUnit * 2.5}px;
  flex: 1;
  height: 100%;
  background-color: ${({ theme }) => theme.colorBgBase};
`;

const ContentWrapper = styled.div`
  flex: 1;
  overflow: auto;
`;

const AppLayout: React.FC<{ children?: React.ReactNode }> = ({ children }) => {
  const dispatch = useDispatch();
  const queryEditorId = useSelector<SqlLabRootState, string>(
    ({ sqlLab: { tabHistory } }) => tabHistory.slice(-1)[0],
  );
  const { md } = Grid.useBreakpoint();
  const [leftWidth, setLeftWidth] = useStoredSidebarWidth(
    'sqllab:leftbar',
    SQL_EDITOR_LEFTBAR_WIDTH,
  );
  const [rightWidth, setRightWidth] = useStoredSidebarWidth(
    'sqllab:rightbar',
    SQL_EDITOR_RIGHTBAR_WIDTH,
  );
  const autoHide = useEffectEvent(() => {
    if (leftWidth > 0) {
      setLeftWidth(0);
    }
  });
  useComponentDidUpdate(() => {
    if (!md) {
      autoHide();
    }
  }, [md]);
  const onSidebarChange = (sizes: number[]) => {
    const [updatedWidth, _, possibleRightWidth] = sizes;
    setLeftWidth(updatedWidth);
    dispatch(toggleLeftBar(updatedWidth === 0));

    if (typeof possibleRightWidth === 'number') {
      setRightWidth(possibleRightWidth);
    }
  };
  const viewItems = useViews(ViewLocations.sqllab.rightSidebar) || [];
  const [aiStudioWidth, setAiStudioWidth] = useStoredSidebarWidth(
    'sqllab:ai-studio',
    AI_STUDIO_SQLLAB_DEFAULT_WIDTH,
  );
  const showAiStudio =
    isAuthenticatedUser() && isFeatureEnabled(FeatureFlag.AiStudio);

  const container = (
    <StyledContainer>
      <Splitter
        css={css`
          flex: 1;
        `}
        lazy
        onResizeEnd={onSidebarChange}
        onResize={noop}
      >
        <Splitter.Panel
          collapsible={{
            start: true,
            end: true,
            showCollapsibleIcon: true,
          }}
          size={leftWidth}
          min={SQL_EDITOR_LEFTBAR_WIDTH}
        >
          <StyledSidebar>
            <SqlEditorLeftBar
              key={queryEditorId}
              queryEditorId={queryEditorId}
            />
          </StyledSidebar>
        </Splitter.Panel>
        <Splitter.Panel className="sqllab-body">{children}</Splitter.Panel>
        {viewItems.length > 0 && (
          <Splitter.Panel
            collapsible={{
              start: true,
              end: true,
              showCollapsibleIcon: true,
            }}
            size={rightWidth}
            min={SQL_EDITOR_RIGHTBAR_WIDTH}
          >
            <ContentWrapper>
              <ViewListExtension viewId={ViewLocations.sqllab.rightSidebar} />
            </ContentWrapper>
          </Splitter.Panel>
        )}
      </Splitter>
      <StatusBar />
    </StyledContainer>
  );

  // The outer AI Studio Splitter only mounts when the panel would actually
  // render — AppLayout.test.tsx fully mocks the Splitter module with a
  // mock that can't distinguish nested instances, so an unconditional wrap
  // would break every existing test's panel-count/button assertions
  // regardless of this flag's value.
  if (!showAiStudio) return container;
  return (
    <Splitter
      lazy
      onResizeEnd={sizes => {
        const width = sizes[sizes.length - 1];
        if (typeof width === 'number' && width >= AI_STUDIO_SQLLAB_MIN_WIDTH) {
          setAiStudioWidth(width);
        }
      }}
      onResize={noop}
      css={css`
        flex: 1;
      `}
    >
      <Splitter.Panel>{container}</Splitter.Panel>
      <Splitter.Panel size={aiStudioWidth} min={AI_STUDIO_SQLLAB_MIN_WIDTH}>
        <AIStudioScoped variant="sqllab" />
      </Splitter.Panel>
    </Splitter>
  );
};

export default AppLayout;
