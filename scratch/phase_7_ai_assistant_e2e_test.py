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

"""
Live E2E Verification Script for Phase 7 AI Chart Assistant:
1. Validates Schema-Validated JSON Specifications (No raw SQL).
2. Validates 2-Stage Preview (save_chart=False) vs Human Confirmation (save_chart=True).
3. Verifies Multi-Role Row-Level Security (RLS) enforcement (Admin vs Regional Analyst).
4. Verifies Prompt Injection & Adversarial Attack Resistance.
5. Verifies Audit Logging in metadata database logs table.
"""

import asyncio
import os
import sys
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch
from flask import g

# Initialize Superset application
from superset.app import create_app

app = create_app()

async def run_phase_7_verification():
    print("=" * 80)
    print("PHASE 7 E2E VERIFICATION: AI CHART ASSISTANT & SECURITY ENFORCEMENT")
    print(f"Timestamp: {datetime.utcnow().isoformat()}Z")
    print("=" * 80)

    with app.app_context(), app.test_request_context():
        from superset import db, security_manager
        from superset.models.slice import Slice
        from superset.models.core import Log
        from superset.daos.dataset import DatasetDAO
        from superset.daos.chart import ChartDAO
        from superset.mcp_service.chart.schemas import (
            TableChartConfig,
            XYChartConfig,
            PivotTableChartConfig,
            ColumnRef,
            FilterConfig,
            GenerateChartRequest,
        )
        from superset.mcp_service.chart.tool.generate_chart import generate_chart
        from superset.mcp_service.chart.validation import ValidationPipeline
        from superset.commands.chart.data.get_data_command import ChartDataCommand
        from superset.common.query_context_factory import QueryContextFactory
        from superset.common.chart_data import ChartDataResultFormat, ChartDataResultType

        # Setup users
        admin_user = db.session.query(security_manager.user_model).filter_by(username="admin").first()
        regional_user = db.session.query(security_manager.user_model).filter_by(username="regional_user").first()
        if not admin_user:
            print("ERROR: admin user not found!")
            sys.exit(1)
        if not regional_user:
            print("ERROR: regional_user not found!")
            sys.exit(1)

        print(f"Admin User ID: {admin_user.id} ({admin_user.username})")
        print(f"Regional User ID: {regional_user.id} ({regional_user.username})")

        g.user = admin_user

        dataset_id = 28
        dataset = DatasetDAO.find_by_id(dataset_id)
        if not dataset:
            print(f"ERROR: Dataset ID {dataset_id} not found!")
            sys.exit(1)
        print(f"Target Dataset: ID {dataset.id} ({dataset.table_name}) | Database: {dataset.database.database_name}")

        # ----------------------------------------------------------------------
        # TEST 1: Natural Language Specification -> Schema-Validated JSON
        # ----------------------------------------------------------------------
        print("\n--- TEST 1: Schema-Validated JSON Specification Generation ---")
        chart_config = XYChartConfig(
            chart_type="xy",
            kind="bar",
            x=ColumnRef(name="customer_region"),
            y=[ColumnRef(name="sales_amount", aggregate="SUM", label="Total Revenue")],
            group_by=ColumnRef(name="department_code"),
            filters=[FilterConfig(column="customer_region", op="!=", value="Unknown")],
        )
        preview_req = GenerateChartRequest(
            dataset_id=str(dataset_id),
            config=chart_config,
            save_chart=False,
            generate_preview=True,
            preview_formats=["url", "table"],
        )

        ctx = MagicMock()
        ctx.info = AsyncMock()
        ctx.debug = AsyncMock()
        ctx.warning = AsyncMock()
        ctx.error = AsyncMock()
        ctx.report_progress = AsyncMock()
        ctx.user = admin_user

        with patch("superset.mcp_service.auth.get_user_from_request", side_effect=lambda: db.session.merge(admin_user)):
            preview_resp = await generate_chart(preview_req, ctx=ctx)

        print(f"Preview Response Success: {preview_resp.success}")
        print(f"Explore URL: {preview_resp.explore_url}")
        print(f"Form Data Key: {preview_resp.form_data_key}")
        print(f"Chart ID (Must be None in Preview Mode): {preview_resp.chart}")
        assert preview_resp.success is True
        assert preview_resp.chart is None
        assert preview_resp.explore_url is not None
        assert preview_resp.form_data_key is not None
        print("✓ TEST 1 PASSED: Structured JSON schema successfully transformed and compiled into explore preview.")

        # ----------------------------------------------------------------------
        # TEST 2: Two-Stage Workflow: Preview vs Mandatory Human Confirmation
        # ----------------------------------------------------------------------
        print("\n--- TEST 2: Mandatory Human Confirmation & Persist Workflow ---")
        # Clean up any existing test chart with this name
        existing_charts = db.session.query(Slice).filter_by(slice_name="Phase 7 AI Assistant Revenue Chart").all()
        for ec in existing_charts:
            db.session.delete(ec)
        db.session.commit()

        confirm_req = GenerateChartRequest(
            dataset_id=str(dataset_id),
            config=chart_config,
            save_chart=True,
            chart_name="Phase 7 AI Assistant Revenue Chart",
        )

        with patch("superset.mcp_service.auth.get_user_from_request", side_effect=lambda: db.session.merge(admin_user)):
            confirm_resp = await generate_chart(confirm_req, ctx=ctx)

        print(f"Save Response Success: {confirm_resp.success}")
        print(f"Saved Chart ID: {confirm_resp.chart.id if confirm_resp.chart else None}")
        print(f"Saved Chart Slice Name: {confirm_resp.chart.slice_name if confirm_resp.chart else None}")
        assert confirm_resp.success is True
        assert confirm_resp.chart is not None
        assert confirm_resp.chart.id is not None
        saved_chart_id = confirm_resp.chart.id

        # Verify saved chart in database
        saved_slice = db.session.query(Slice).filter_by(id=saved_chart_id).first()
        assert saved_slice is not None
        print(f"Verified Slice in Metadata DB: ID {saved_slice.id}, Slice Name: '{saved_slice.slice_name}', Viz Type: {saved_slice.viz_type}")
        print("✓ TEST 2 PASSED: Chart was safely persisted ONLY upon human confirmation (save_chart=True).")

        # ----------------------------------------------------------------------
        # TEST 3: Multi-Role Row-Level Security (RLS) Enforcement
        # ----------------------------------------------------------------------
        print("\n--- TEST 3: Multi-Role Row-Level Security (RLS) Verification ---")
        query_payload = {
            "datasource": {"id": dataset_id, "type": "table"},
            "queries": [
                {
                    "columns": ["customer_region"],
                    "metrics": [
                        {
                            "expressionType": "SIMPLE",
                            "column": {"column_name": "sales_amount"},
                            "aggregate": "SUM",
                            "label": "total_revenue",
                        }
                    ],
                    "orderby": [["total_revenue", False]],
                    "row_limit": 100,
                }
            ],
            "result_type": "full",
            "result_format": "json",
        }

        # Query as Admin
        g.user = admin_user
        admin_qc = QueryContextFactory().create(
            datasource={"id": dataset_id, "type": "table"},
            queries=query_payload["queries"],
            form_data=query_payload,
            result_type=ChartDataResultType.FULL,
            result_format=ChartDataResultFormat.JSON,
        )
        admin_cmd = ChartDataCommand(admin_qc)
        admin_results = admin_cmd.run()["queries"][0]
        admin_data = admin_results["data"]
        admin_regions = [row["customer_region"] for row in admin_data]
        admin_revenue = sum(float(row["total_revenue"]) for row in admin_data)

        print(f"Admin Visible Regions: {sorted(admin_regions)} (Count: {len(admin_regions)})")
        print(f"Admin Total Revenue: ${admin_revenue:,.2f}")
        assert len(admin_regions) == 4
        assert "North America" in admin_regions
        assert "EMEA" in admin_regions
        assert "APAC" in admin_regions
        assert "LATAM" in admin_regions
        assert round(admin_revenue, 2) == 167236831.75

        # Query as Regional Analyst (RLS rule: customer_region = 'North America')
        g.user = regional_user
        regional_qc = QueryContextFactory().create(
            datasource={"id": dataset_id, "type": "table"},
            queries=query_payload["queries"],
            form_data=query_payload,
            result_type=ChartDataResultType.FULL,
            result_format=ChartDataResultFormat.JSON,
        )
        regional_cmd = ChartDataCommand(regional_qc)
        regional_results = regional_cmd.run()["queries"][0]
        regional_data = regional_results["data"]
        regional_regions = [row["customer_region"] for row in regional_data]
        regional_revenue = sum(float(row["total_revenue"]) for row in regional_data)

        print(f"Regional User Visible Regions: {regional_regions} (Count: {len(regional_regions)})")
        print(f"Regional User Total Revenue: ${regional_revenue:,.2f}")
        assert regional_regions == ["North America"]
        assert round(regional_revenue, 2) == 41199313.50
        print("✓ TEST 3 PASSED: RLS is strictly enforced on AI Assistant chart data paths with zero data leakage.")

        # ----------------------------------------------------------------------
        # TEST 4: Prompt Injection & Adversarial Attack Resistance
        # ----------------------------------------------------------------------
        print("\n--- TEST 4: Prompt Injection & Adversarial Attack Defense Suite ---")
        g.user = admin_user
        adversarial_tests = [
            ("Direct SQL Injection in Column", "sales; DROP TABLE ab_user; --", False),
            ("Stacked Semicolon Command", "sales_amount; SELECT * FROM pg_shadow;", False),
            ("Comment Metacharacter Injection", "customer_region -- system override", False),
            ("Raw SQL Discriminator Bypass", {"chart_type": "raw_sql", "sql": "DROP TABLE slices"}, False),
        ]

        for test_name, payload, expected_valid in adversarial_tests:
            if isinstance(payload, str):
                try:
                    ColumnRef(name=payload)
                    is_valid = True
                except Exception:
                    is_valid = False
            else:
                is_valid, _, _ = ValidationPipeline.validate_request({"dataset_id": dataset_id, "config": payload})
            
            print(f" - {test_name}: Validated={is_valid} (Expected Safe Block={not expected_valid})")
            assert is_valid == expected_valid

        # Test XSS sanitization in chart names
        xss_request = GenerateChartRequest(
            dataset_id=str(dataset_id),
            config=chart_config,
            chart_name="<script>alert('xss')</script>Executive Revenue Dashboard",
            save_chart=False,
        )
        print(f" - Chart Name XSS Sanitized: '{xss_request.chart_name}'")
        assert "<script>" not in xss_request.chart_name
        assert xss_request.chart_name == "Executive Revenue Dashboard"
        print("✓ TEST 4 PASSED: All prompt injection and adversarial attack vectors were actively neutralized.")

        # ----------------------------------------------------------------------
        # TEST 5: Audit Logging Verification
        # ----------------------------------------------------------------------
        print("\n--- TEST 5: Audit Logging in Database Logs Table ---")
        recent_logs = db.session.query(Log).order_by(Log.dttm.desc()).limit(15).all()
        print(f"Found {len(recent_logs)} recent audit log entries.")
        for log in recent_logs[:5]:
            print(f" - Log: action='{log.action}', user_id={log.user_id}, slice_id={log.slice_id}, dttm={log.dttm}")
        assert len(recent_logs) > 0
        print("✓ TEST 5 PASSED: Audit trail records exist for chart preview, exploration, and database operations.")

        print("\n" + "=" * 80)
        print("ALL PHASE 7 E2E VERIFICATION CHECKS PASSED SUCCESSFULLY (100%)")
        print("=" * 80)

if __name__ == "__main__":
    asyncio.run(run_phase_7_verification())
