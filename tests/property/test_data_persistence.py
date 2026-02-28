"""
Property-Based Test: Data Persistence Consistency

This test validates data persistence, privacy, and consistency requirements
for the DynamoDB-based storage system.

**Validates: Requirements 4.1, 4.3, 4.4, 4.6, 12.5, 12.6**
**Property 13: Privacy and Data Protection**
"""

import pytest
from hypothesis import given, assume, strategies as st, settings, HealthCheck
from datetime import datetime, timedelta
from typing import List, Dict, Any
import concurrent.futures
from decimal import Decimal

from services.db_service import DbService, PlotData, AlertData, HobliDirectory
from tests.conftest import (
    indian_coordinates,
    plot_data,
    alert_data,
    hobli_ids,
)
from tests.test_utils import (
    CoordinateTestHelper,
    HobliTestHelper,
)


@pytest.mark.property
class TestDataPersistenceConsistency:
    """
    Property 13: Privacy and Data Protection
    
    Tests that the system maintains data persistence consistency while
    respecting privacy requirements and jurisdiction-based access control.
    """
    
    @given(plot=plot_data())
    @settings(max_examples=30, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_plot_registration_round_trip(self, mock_dynamodb_tables, plot):
        """
        Property: For any valid plot data, registration followed by retrieval
        should return the exact same data (round-trip consistency).
        
        **Validates: Requirements 4.1, 12.6**
        """
        # Initialize DbService with mocked DynamoDB
        db_service = DbService(region="ap-south-1")
        
        # Create PlotData object
        plot_data_obj = PlotData(
            user_id=plot["user_id"],
            plot_id=plot["plot_id"],
            lat=plot["lat"],
            lon=plot["lon"],
            crop=plot["crop"],
            hobli_id=plot["hobli_id"],
            farmer_name=plot["farmer_name"],
            phone_number=plot["phone_number"],
            registration_date=datetime.now(),
            status="active"
        )
        
        # Register the plot
        returned_plot_id = db_service.register_plot(plot_data_obj)
        assert returned_plot_id == plot["plot_id"]
        
        # Retrieve the plot
        retrieved_plot = db_service.get_plot_by_id(plot["user_id"], plot["plot_id"])
        
        # Verify round-trip consistency
        assert retrieved_plot is not None
        assert retrieved_plot.user_id == plot_data_obj.user_id
        assert retrieved_plot.plot_id == plot_data_obj.plot_id
        assert retrieved_plot.lat == plot_data_obj.lat
        assert retrieved_plot.lon == plot_data_obj.lon
        assert retrieved_plot.crop == plot_data_obj.crop
        assert retrieved_plot.hobli_id == plot_data_obj.hobli_id
        assert retrieved_plot.farmer_name == plot_data_obj.farmer_name
        assert retrieved_plot.phone_number == plot_data_obj.phone_number
        assert retrieved_plot.status == plot_data_obj.status
    
    @given(alert=alert_data())
    @settings(max_examples=30, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_alert_creation_round_trip(self, mock_dynamodb_tables, alert):
        """
        Property: For any valid alert data, creation followed by retrieval
        should return the exact same data with all fields intact.
        
        **Validates: Requirements 4.1, 12.5, 12.6**
        """
        # Initialize DbService
        db_service = DbService(region="ap-south-1")
        
        # Create AlertData object
        timestamp = datetime.now()
        alert_data_obj = AlertData(
            hobli_id=alert["hobli_id"],
            timestamp=timestamp,
            plot_id=alert["plot_id"],
            user_id=alert["user_id"],
            risk_level=alert["risk_level"],
            message=alert["message"],
            gee_proof=alert["gee_proof"],
            bedrock_reasoning=alert["bedrock_reasoning"],
            resolution_status="pending",
            sms_sent=False
        )
        
        # Create the alert
        db_service.create_alert(alert_data_obj)
        
        # Retrieve alerts for the hobli
        retrieved_alerts = db_service.get_recent_alerts(
            alert["hobli_id"], 
            hours=1
        )
        
        # Find our alert
        matching_alert = None
        for a in retrieved_alerts:
            if (a.plot_id == alert["plot_id"] and 
                a.user_id == alert["user_id"] and
                abs((a.timestamp - timestamp).total_seconds()) < 1):
                matching_alert = a
                break
        
        # Verify round-trip consistency
        assert matching_alert is not None
        assert matching_alert.hobli_id == alert_data_obj.hobli_id
        assert matching_alert.plot_id == alert_data_obj.plot_id
        assert matching_alert.user_id == alert_data_obj.user_id
        assert matching_alert.risk_level == alert_data_obj.risk_level
        assert matching_alert.message == alert_data_obj.message
        assert matching_alert.bedrock_reasoning == alert_data_obj.bedrock_reasoning
        assert matching_alert.resolution_status == alert_data_obj.resolution_status
        assert matching_alert.sms_sent == alert_data_obj.sms_sent
        
        # Verify GEE proof data integrity
        assert "ndvi_value" in matching_alert.gee_proof
        assert "moisture_index" in matching_alert.gee_proof
        assert "temperature_anomaly" in matching_alert.gee_proof
    
    @given(
        plots=st.lists(plot_data(), min_size=3, max_size=10, unique_by=lambda p: (p["user_id"], p["plot_id"]))
    )
    @settings(max_examples=10, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_jurisdiction_based_filtering(self, mock_dynamodb_tables, plots):
        """
        Property: For any set of plots across multiple jurisdictions,
        jurisdiction-based filtering should return only plots within
        the specified jurisdiction.
        
        **Validates: Requirements 4.3, 12.5**
        """
        # Initialize DbService
        db_service = DbService(region="ap-south-1")
        
        # Assign all plots to specific hoblis for testing and ensure unique IDs
        hobli_mapping = {}
        for i, plot in enumerate(plots):
            # Assign to one of 3 test hoblis
            hobli_id = f"hobli_test_{i % 3:03d}"
            plot["hobli_id"] = hobli_id
            # Ensure unique plot IDs to avoid primary key conflicts
            plot["plot_id"] = f"plot_jurisdiction_{i:04d}"
            plot["user_id"] = f"user_jurisdiction_{i:04d}"
            
            if hobli_id not in hobli_mapping:
                hobli_mapping[hobli_id] = []
            hobli_mapping[hobli_id].append(plot)
        
        # Register all plots
        for plot in plots:
            plot_data_obj = PlotData(
                user_id=plot["user_id"],
                plot_id=plot["plot_id"],
                lat=plot["lat"],
                lon=plot["lon"],
                crop=plot["crop"],
                hobli_id=plot["hobli_id"],
                farmer_name=plot["farmer_name"],
                phone_number=plot["phone_number"],
                registration_date=datetime.now(),
                status="active"
            )
            db_service.register_plot(plot_data_obj)
        
        # Test jurisdiction-based filtering for each hobli
        for hobli_id, expected_plots in hobli_mapping.items():
            retrieved_plots = db_service.get_hobli_plots(hobli_id)
            
            # Verify only plots from this jurisdiction are returned
            assert len(retrieved_plots) == len(expected_plots)
            
            retrieved_plot_ids = {p.plot_id for p in retrieved_plots}
            expected_plot_ids = {p["plot_id"] for p in expected_plots}
            
            assert retrieved_plot_ids == expected_plot_ids
            
            # Verify all retrieved plots have the correct hobli_id
            for plot in retrieved_plots:
                assert plot.hobli_id == hobli_id
    
    @given(
        plots=st.lists(plot_data(), min_size=5, max_size=15, unique_by=lambda p: (p["user_id"], p["plot_id"]))
    )
    @settings(max_examples=15, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_concurrent_plot_registration(self, mock_dynamodb_tables, plots):
        """
        Property: For any set of plots, concurrent registration operations
        should maintain data consistency with no data loss or corruption.
        
        **Validates: Requirements 12.6**
        """
        # Initialize DbService
        db_service = DbService(region="ap-south-1")
        
        # Ensure unique plot IDs to avoid primary key conflicts
        for i, plot in enumerate(plots):
            plot["plot_id"] = f"plot_concurrent_{i:04d}"
            plot["user_id"] = f"user_concurrent_{i:04d}"
        
        def register_plot(plot_dict):
            """Helper function to register a plot"""
            plot_data_obj = PlotData(
                user_id=plot_dict["user_id"],
                plot_id=plot_dict["plot_id"],
                lat=plot_dict["lat"],
                lon=plot_dict["lon"],
                crop=plot_dict["crop"],
                hobli_id=plot_dict["hobli_id"],
                farmer_name=plot_dict["farmer_name"],
                phone_number=plot_dict["phone_number"],
                registration_date=datetime.now(),
                status="active"
            )
            return db_service.register_plot(plot_data_obj)
        
        # Register plots concurrently
        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(register_plot, plot) for plot in plots]
            results = [f.result() for f in concurrent.futures.as_completed(futures)]
        
        # Verify all plots were registered successfully
        assert len(results) == len(plots)
        
        # Verify data consistency by retrieving all plots
        for plot in plots:
            retrieved_plot = db_service.get_plot_by_id(
                plot["user_id"], 
                plot["plot_id"]
            )
            
            assert retrieved_plot is not None
            assert retrieved_plot.plot_id == plot["plot_id"]
            assert retrieved_plot.user_id == plot["user_id"]
            assert retrieved_plot.hobli_id == plot["hobli_id"]
    
    @given(
        alerts=st.lists(alert_data(), min_size=5, max_size=15)
    )
    @settings(max_examples=10, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_concurrent_alert_creation(self, mock_dynamodb_tables, alerts):
        """
        Property: For any set of alerts, concurrent creation operations
        should maintain data consistency with no data loss.
        
        **Validates: Requirements 12.6**
        """
        # Initialize DbService
        db_service = DbService(region="ap-south-1")
        
        # Assign all alerts to the same hobli for testing and ensure unique plot IDs
        test_hobli = "hobli_concurrent_test_001"
        for i, alert in enumerate(alerts):
            alert["hobli_id"] = test_hobli
            alert["plot_id"] = f"plot_alert_{i:04d}"
            alert["user_id"] = f"user_alert_{i:04d}"
        
        def create_alert(alert_dict):
            """Helper function to create an alert"""
            alert_data_obj = AlertData(
                hobli_id=alert_dict["hobli_id"],
                timestamp=datetime.now(),
                plot_id=alert_dict["plot_id"],
                user_id=alert_dict["user_id"],
                risk_level=alert_dict["risk_level"],
                message=alert_dict["message"],
                gee_proof=alert_dict["gee_proof"],
                bedrock_reasoning=alert_dict["bedrock_reasoning"],
                resolution_status="pending",
                sms_sent=False
            )
            db_service.create_alert(alert_data_obj)
            return alert_dict["plot_id"]
        
        # Create alerts concurrently
        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(create_alert, alert) for alert in alerts]
            results = [f.result() for f in concurrent.futures.as_completed(futures)]
        
        # Verify all alerts were created successfully
        assert len(results) == len(alerts)
        
        # Retrieve all alerts for the hobli
        retrieved_alerts = db_service.get_recent_alerts(test_hobli, hours=1)
        
        # Verify data consistency
        assert len(retrieved_alerts) >= len(alerts)
        
        retrieved_plot_ids = {a.plot_id for a in retrieved_alerts}
        expected_plot_ids = {a["plot_id"] for a in alerts}
        
        # All expected alerts should be present
        assert expected_plot_ids.issubset(retrieved_plot_ids)
    
    @given(plot=plot_data())
    @settings(max_examples=20, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_essential_data_only_stored(self, mock_dynamodb_tables, plot):
        """
        Property: For any plot registration, only essential operational data
        should be stored (coordinates, alert history, jurisdiction mapping).
        No unnecessary PII beyond contact details should be stored.
        
        **Validates: Requirements 4.1**
        """
        # Initialize DbService
        db_service = DbService(region="ap-south-1")
        
        # Register plot
        plot_data_obj = PlotData(
            user_id=plot["user_id"],
            plot_id=plot["plot_id"],
            lat=plot["lat"],
            lon=plot["lon"],
            crop=plot["crop"],
            hobli_id=plot["hobli_id"],
            farmer_name=plot["farmer_name"],
            phone_number=plot["phone_number"],
            registration_date=datetime.now(),
            status="active"
        )
        db_service.register_plot(plot_data_obj)
        
        # Retrieve the plot
        retrieved_plot = db_service.get_plot_by_id(plot["user_id"], plot["plot_id"])
        
        # Verify only essential fields are present
        essential_fields = {
            "user_id", "plot_id", "lat", "lon", "crop", "hobli_id",
            "farmer_name", "phone_number", "registration_date", 
            "last_analysis", "status"
        }
        
        # Get all fields from the retrieved plot
        plot_dict = retrieved_plot.dict()
        stored_fields = set(plot_dict.keys())
        
        # Verify no extra fields beyond essential ones
        assert stored_fields == essential_fields
        
        # Verify essential operational data is present
        assert retrieved_plot.lat is not None  # Coordinates
        assert retrieved_plot.lon is not None
        assert retrieved_plot.hobli_id is not None  # Jurisdiction mapping
        assert retrieved_plot.farmer_name is not None  # Contact for alerts
        assert retrieved_plot.phone_number is not None
    
    @given(
        plots=st.lists(plot_data(), min_size=3, max_size=8, unique_by=lambda p: (p["user_id"], p["plot_id"])),
        alerts=st.lists(alert_data(), min_size=3, max_size=8)
    )
    @settings(max_examples=10, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_data_retrieval_accuracy(self, mock_dynamodb_tables, plots, alerts):
        """
        Property: For any set of plots and alerts, data retrieval operations
        should return accurate and complete results matching the stored data.
        
        **Validates: Requirements 12.5, 12.6**
        """
        # Initialize DbService
        db_service = DbService(region="ap-south-1")
        
        # Use a single hobli for testing and ensure unique IDs
        test_hobli = "hobli_accuracy_test_001"
        
        # Register plots with unique IDs
        for i, plot in enumerate(plots):
            plot["hobli_id"] = test_hobli
            plot["plot_id"] = f"plot_accuracy_{i:04d}"
            plot["user_id"] = f"user_accuracy_{i:04d}"
            
            plot_data_obj = PlotData(
                user_id=plot["user_id"],
                plot_id=plot["plot_id"],
                lat=plot["lat"],
                lon=plot["lon"],
                crop=plot["crop"],
                hobli_id=plot["hobli_id"],
                farmer_name=plot["farmer_name"],
                phone_number=plot["phone_number"],
                registration_date=datetime.now(),
                status="active"
            )
            db_service.register_plot(plot_data_obj)
        
        # Create alerts
        for i, alert in enumerate(alerts):
            alert["hobli_id"] = test_hobli
            alert["plot_id"] = f"plot_accuracy_{i % len(plots):04d}"
            
            alert_data_obj = AlertData(
                hobli_id=alert["hobli_id"],
                timestamp=datetime.now(),
                plot_id=alert["plot_id"],
                user_id=alert["user_id"],
                risk_level=alert["risk_level"],
                message=alert["message"],
                gee_proof=alert["gee_proof"],
                bedrock_reasoning=alert["bedrock_reasoning"],
                resolution_status="pending",
                sms_sent=False
            )
            db_service.create_alert(alert_data_obj)
        
        # Test plot retrieval accuracy
        retrieved_plots = db_service.get_hobli_plots(test_hobli)
        assert len(retrieved_plots) == len(plots)
        
        # Verify all plots are present
        retrieved_plot_ids = {p.plot_id for p in retrieved_plots}
        expected_plot_ids = {p["plot_id"] for p in plots}
        assert retrieved_plot_ids == expected_plot_ids
        
        # Test alert retrieval accuracy
        retrieved_alerts = db_service.get_recent_alerts(test_hobli, hours=1)
        assert len(retrieved_alerts) >= len(alerts)
        
        # Verify all alerts are present
        retrieved_alert_plots = {a.plot_id for a in retrieved_alerts}
        expected_alert_plots = {a["plot_id"] for a in alerts}
        assert expected_alert_plots.issubset(retrieved_alert_plots)
        
        # Test jurisdiction stats accuracy
        stats = db_service.get_jurisdiction_stats(test_hobli)
        assert stats.hobli_id == test_hobli
        assert stats.total_plots == len(plots)
        assert stats.active_alerts >= len(alerts)
    
    @given(
        hobli_id=hobli_ids(),
        officer_name=st.text(min_size=5, max_size=50, alphabet=st.characters(categories=["Lu", "Ll", "Zs"]))
    )
    @settings(max_examples=20, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_jurisdiction_directory_consistency(self, mock_dynamodb_tables, hobli_id, officer_name):
        """
        Property: For any hobli directory entry, registration and retrieval
        should maintain consistency of jurisdiction-to-officer mappings.
        
        **Validates: Requirements 4.3, 12.5**
        """
        # Initialize DbService
        db_service = DbService(region="ap-south-1")
        
        # Extract district from hobli_id
        district = HobliTestHelper.extract_district(hobli_id)
        
        # Create hobli directory entry
        hobli_data = HobliDirectory(
            hobli_id=hobli_id,
            hobli_name=f"{district.title()} Test Hobli",
            district=district.title(),
            state="Karnataka",
            officer_id=f"officer_{hobli_id}",
            officer_name=officer_name.strip(),
            officer_phone="+919876543210",
            officer_email=f"officer@{district}.gov.in",
            created_date=datetime.now(),
            last_updated=datetime.now()
        )
        
        # Register hobli
        returned_hobli_id = db_service.register_hobli(hobli_data)
        assert returned_hobli_id == hobli_id
        
        # Retrieve hobli directory
        retrieved_hobli = db_service.get_hobli_directory(hobli_id)
        
        # Verify consistency
        assert retrieved_hobli is not None
        assert retrieved_hobli.hobli_id == hobli_data.hobli_id
        assert retrieved_hobli.hobli_name == hobli_data.hobli_name
        assert retrieved_hobli.district == hobli_data.district
        assert retrieved_hobli.state == hobli_data.state
        assert retrieved_hobli.officer_id == hobli_data.officer_id
        assert retrieved_hobli.officer_name == hobli_data.officer_name
        assert retrieved_hobli.officer_phone == hobli_data.officer_phone
        assert retrieved_hobli.officer_email == hobli_data.officer_email
    
    @given(
        plots=st.lists(plot_data(), min_size=2, max_size=5, unique_by=lambda p: (p["user_id"], p["plot_id"]))
    )
    @settings(max_examples=15, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_data_consistency_across_updates(self, mock_dynamodb_tables, plots):
        """
        Property: For any plot, updates to last_analysis timestamp should
        maintain data consistency without affecting other fields.
        
        **Validates: Requirements 12.6**
        """
        # Initialize DbService
        db_service = DbService(region="ap-south-1")
        
        # Register plots with unique IDs
        for i, plot in enumerate(plots):
            plot["plot_id"] = f"plot_update_{i:04d}"
            plot["user_id"] = f"user_update_{i:04d}"
            
            plot_data_obj = PlotData(
                user_id=plot["user_id"],
                plot_id=plot["plot_id"],
                lat=plot["lat"],
                lon=plot["lon"],
                crop=plot["crop"],
                hobli_id=plot["hobli_id"],
                farmer_name=plot["farmer_name"],
                phone_number=plot["phone_number"],
                registration_date=datetime.now(),
                status="active"
            )
            db_service.register_plot(plot_data_obj)
        
        # Update last_analysis for each plot
        update_time = datetime.now()
        for plot in plots:
            db_service.update_plot_last_analysis(
                plot["user_id"],
                plot["plot_id"],
                update_time
            )
        
        # Verify updates maintained consistency
        for plot in plots:
            retrieved_plot = db_service.get_plot_by_id(
                plot["user_id"],
                plot["plot_id"]
            )
            
            # Verify last_analysis was updated
            assert retrieved_plot.last_analysis is not None
            assert abs((retrieved_plot.last_analysis - update_time).total_seconds()) < 2
            
            # Verify other fields remain unchanged
            assert retrieved_plot.lat == plot["lat"]
            assert retrieved_plot.lon == plot["lon"]
            assert retrieved_plot.crop == plot["crop"]
            assert retrieved_plot.hobli_id == plot["hobli_id"]
            assert retrieved_plot.farmer_name == plot["farmer_name"]
            assert retrieved_plot.phone_number == plot["phone_number"]
