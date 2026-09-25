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
"""merge AI Studio chain with upstream master

This fork adds an AI Studio feature whose six migrations
(c9a1d5e7f201 -> afb32b2091ae -> b5e7a2c4d813 -> c1f6b3d29a47 ->
b259df8367b2 -> 703cb42bd437) branch off a common ancestor, while upstream
master independently grew to its own head (95d8a99c822e, the
deprecated-permissions merges). Merging master into the fork therefore left
two alembic heads, which makes `superset db upgrade` fail with "Multiple head
revisions are present for given argument 'head'".

This no-op merge revision re-unifies the graph so there is exactly one head
again. It contains no schema changes of its own -- the AI Studio tables are
created by the revisions above, and the upstream ones by their own.

This file is fork-only: it must be re-created whenever master is merged in
and both sides have grown a new head (same pattern upstream uses in its
``*_merge_*`` revisions).

Revision ID: a7c4e91b25d3
Revises: ('703cb42bd437', '95d8a99c822e')
Create Date: 2026-09-25 00:00:00.000000

"""

# revision identifiers, used by Alembic.
revision = "a7c4e91b25d3"
down_revision = ("703cb42bd437", "95d8a99c822e")


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
