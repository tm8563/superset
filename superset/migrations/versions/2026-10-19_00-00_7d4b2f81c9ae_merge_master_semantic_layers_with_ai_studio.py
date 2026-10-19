# Licensed to the Apache Software Foundation (ASF) under one
# or more contributor license agreements.  See the NOTICE file
# distributed with this work for additional information
# regarding copyright ownership.  The ASF licenses this file
# to you under the Apache License, Version 2.0 (the
# "License"); you may not use this file except in compliance
# with the License.  You may obtain a copy of the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing,
# software distributed under the License is distributed on an
# "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY
# KIND, either express or implied.  See the License for the
# specific language governing permissions and limitations
# under the License.
"""merge master (semantic layer cache + report run_as) with AI Studio chain

Third occurrence of the same recurring situation (see
``2026-09-25_00-00_a7c4e91b25d3_merge_ai_studio_with_master.py`` and
``2026-10-08_00-00_c1e5d7a93b28_merge_master_annotation_uuid_with_ai_studio.py``):
merging origin/master into this fork leaves two alembic heads, so ``superset db
upgrade`` aborts with "Multiple head revisions are present for given argument
'head'" and the whole stack fails to start (``superset``/``worker`` depend on
``superset-init`` completing).

Graph at the time of writing::

    95d8a99c822e ──┬── 703cb42bd437 -> ... -> c1e5d7a93b28   (fork: AI Studio)
                   └── 00fab727cd0a -> e4a7c2b9d1f3 -> c179af013f48 (master)

This no-op merge revision re-unifies them into a single head. It is
deliberately ADDITIVE: the parents of ``c1e5d7a93b28`` are left untouched, so
that master's ``e4a7c2b9d1f3`` (reports run_as + report config) and
``c179af013f48`` (semantic layer cache version) are genuinely applied. Had we
instead re-pointed ``c1e5d7a93b28`` at ``c179af013f48``, the database — which
already records ``c1e5d7a93b28`` as applied — would have reported "already at
head" and silently skipped those two migrations. Never rewrite migration
history to fix a multi-head state; always add a merge revision.

Fork-only: re-create whenever master is merged in and both sides have grown a
new head (same pattern upstream uses in its ``*_merge_*`` revisions).

Revision ID: 7d4b2f81c9ae
Revises: ('c1e5d7a93b28', 'c179af013f48')
Create Date: 2026-10-19 00:00:00.000000

"""

# revision identifiers, used by Alembic.
revision = "7d4b2f81c9ae"
down_revision = ("c1e5d7a93b28", "c179af013f48")


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
