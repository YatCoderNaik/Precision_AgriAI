"""
Unit Tests for DbService

Tests DynamoDB operations including:
- Plot registration and retrieval
- Alert creation and querying
- Jurisdiction-based queries using GSI
- Data consistency and error handling
"""

import pytest
from datetime import datetime, timedelta
from services.db_service import DbService, PlotData, AlertData
from moto import mock_aws
import boto3


@pytest.fixture
def db_service(mock_dynamodb_tables):
    """Create DbService instance with mocked DynamoDB tables"""
    with mock_aws():
        service = DbService(region="ap-south-1")
        yield service


class TestPlotOperations:
    """Test plot registration and retrieval operations"""
    
    def test_register_plot(self, db_service, sample_plot_data):
        """Test plot registration"""
        plot_data = PlotData(
            **sample_plot_data,
            registration_date=datetime.now()
        )
        
        plot_id = db_service.register_plot(plot_data)
        
        assert plot_id == sample_plot_data["plot_id"]
    
    def test_get_plot_by_id(self, db_service, sample_plot_data):
        """Test retrieving a plot by ID"""
        # Register a plot first
        plot_data = PlotData(
            **sample_plot_data,
            registration_date=datetime.now()
        )
        db_service.register_plot(plot_data)
        
        # Retrieve the plot
        retrieved_plot = db_service.get_plot_by_id(
            sample_plot_data["user_id"],
            sample_plot_data["plot_id"]
        )
        
        assert retrieved_plot is not None
        assert retrieved_plot.user_id == sample_plot_data["user_id"]
        assert retrieved_plot.plot_id == sample_plot_data["plot_id"]
        assert retrieved_plot.lat == sample_plot_data["lat"]
        assert retrieved_plot.lon == sample_plot_data["lon"]
        assert retrieved_plot.crop == sample_plot_data["crop"]
    
    def test_get_plot_by_id_not_found(self, db_service):
        """Test retrieving a non-existent plot"""
        retrieved_plot = db_service.get_plot_by_id("nonexistent_user", "nonexistent_plot")
        
        assert retrieved_plot is None
    
    def test_get_hobli_plots(self, db_service, sample_plot_data):
        """Test retrieving all plots for a jurisdiction"""
        hobli_id = sample_plot_data["hobli_id"]
        
        # Register multiple plots in the same hobli
        for i in range(3):
            plot_data = PlotData(
                user_id=f"user_{i:03d}",
                plot_id=f"plot_{i:03d}",
                lat=sample_plot_data["lat"],
                lon=sample_plot_data["lon"],
                crop=sample_plot_data["crop"],
                hobli_id=hobli_id,
                farmer_name=f"Farmer {i}",
                phone_number=f"+9198765432{i:02d}",
                registration_date=datetime.now()
            )
            db_service.register_plot(plot_data)
        
        # Retrieve plots by hobli
        plots = db_service.get_hobli_plots(hobli_id)
        
        assert len(plots) == 3
        assert all(plot.hobli_id == hobli_id for plot in plots)
    
    def test_update_plot_last_analysis(self, db_service, sample_plot_data):
        """Test updating plot's last analysis timestamp"""
        # Register a plot
        plot_data = PlotData(
            **sample_plot_data,
            registration_date=datetime.now()
        )
        db_service.register_plot(plot_data)
        
        # Update last analysis
        analysis_time = datetime.now()
        db_service.update_plot_last_analysis(
            sample_plot_data["user_id"],
            sample_plot_data["plot_id"],
            analysis_time
        )
        
        # Verify update
        retrieved_plot = db_service.get_plot_by_id(
            sample_plot_data["user_id"],
            sample_plot_data["plot_id"]
        )
        
        assert retrieved_plot.last_analysis is not None
        # Allow small time difference due to serialization
        assert abs((retrieved_plot.last_analysis - analysis_time).total_seconds()) < 1


class TestAlertOperations:
    """Test alert creation and querying operations"""
    
    def test_create_alert(self, db_service, sample_alert_data):
        """Test alert creation"""
        alert_data = AlertData(
            **sample_alert_data,
            timestamp=datetime.now()
        )
        
        # Should not raise an exception
        db_service.create_alert(alert_data)
    
    def test_get_recent_alerts(self, db_service, sample_alert_data):
        """Test retrieving recent alerts for a jurisdiction"""
        hobli_id = sample_alert_data["hobli_id"]
        
        # Create multiple alerts
        for i in range(3):
            alert_data = AlertData(
                hobli_id=hobli_id,
                timestamp=datetime.now() - timedelta(hours=i),
                plot_id=f"plot_{i:03d}",
                user_id=f"user_{i:03d}",
                risk_level="high",
                message=f"Alert {i}",
                gee_proof=sample_alert_data["gee_proof"],
                bedrock_reasoning=sample_alert_data["bedrock_reasoning"]
            )
            db_service.create_alert(alert_data)
        
        # Retrieve recent alerts (last 24 hours)
        alerts = db_service.get_recent_alerts(hobli_id, hours=24)
        
        assert len(alerts) == 3
        assert all(alert.hobli_id == hobli_id for alert in alerts)
        # Verify they're sorted by timestamp descending (newest first)
        assert alerts[0].timestamp >= alerts[1].timestamp >= alerts[2].timestamp
    
    def test_get_recent_alerts_time_filter(self, db_service, sample_alert_data):
        """Test that time filter works correctly"""
        hobli_id = sample_alert_data["hobli_id"]
        
        # Create alerts at different times
        alert_recent = AlertData(
            **sample_alert_data,
            timestamp=datetime.now() - timedelta(hours=1)
        )
        
        # Create old alert with modified plot_id
        alert_old_data = sample_alert_data.copy()
        alert_old_data["plot_id"] = "plot_old"
        alert_old = AlertData(
            **alert_old_data,
            timestamp=datetime.now() - timedelta(hours=48)
        )
        
        db_service.create_alert(alert_recent)
        db_service.create_alert(alert_old)
        
        # Retrieve alerts from last 24 hours only
        alerts = db_service.get_recent_alerts(hobli_id, hours=24)
        
        # Should only get the recent alert
        assert len(alerts) == 1
        assert alerts[0].plot_id == sample_alert_data["plot_id"]
    
    def test_update_alert_status(self, db_service, sample_alert_data):
        """Test updating alert resolution status"""
        alert_data = AlertData(
            **sample_alert_data,
            timestamp=datetime.now()
        )
        db_service.create_alert(alert_data)
        
        # Update alert status
        db_service.update_alert_status(
            alert_data.hobli_id,
            alert_data.timestamp,
            "resolved",
            "Issue addressed by Extension Officer"
        )
        
        # Verify update by retrieving alerts
        alerts = db_service.get_recent_alerts(alert_data.hobli_id, hours=24)
        
        assert len(alerts) == 1
        assert alerts[0].resolution_status == "resolved"
        assert alerts[0].officer_response == "Issue addressed by Extension Officer"
    
    def test_get_high_priority_alerts(self, db_service, sample_alert_data):
        """Test retrieving high priority alerts across all jurisdictions"""
        # Create alerts with different risk levels
        for i in range(2):
            alert_high = AlertData(
                hobli_id=f"hobli_{i:03d}",
                timestamp=datetime.now() - timedelta(hours=i),
                plot_id=f"plot_{i:03d}",
                user_id=f"user_{i:03d}",
                risk_level="high",
                message=f"High priority alert {i}",
                gee_proof=sample_alert_data["gee_proof"],
                bedrock_reasoning=sample_alert_data["bedrock_reasoning"]
            )
            db_service.create_alert(alert_high)
        
        # Create a low priority alert (should not be returned)
        alert_low_data = sample_alert_data.copy()
        alert_low_data["risk_level"] = "low"
        alert_low = AlertData(
            **alert_low_data,
            timestamp=datetime.now()
        )
        db_service.create_alert(alert_low)
        
        # Retrieve high priority alerts
        high_priority = db_service.get_high_priority_alerts()
        
        assert len(high_priority) == 2
        assert all(alert.risk_level == "high" for alert in high_priority)


class TestJurisdictionStats:
    """Test jurisdiction statistics aggregation"""
    
    def test_get_jurisdiction_stats(self, db_service, sample_plot_data, sample_alert_data):
        """Test calculating jurisdiction statistics"""
        hobli_id = sample_plot_data["hobli_id"]
        
        # Register plots
        for i in range(5):
            plot_data = PlotData(
                user_id=f"user_{i:03d}",
                plot_id=f"plot_{i:03d}",
                lat=sample_plot_data["lat"],
                lon=sample_plot_data["lon"],
                crop=sample_plot_data["crop"],
                hobli_id=hobli_id,
                farmer_name=f"Farmer {i}",
                phone_number=f"+9198765432{i:02d}",
                registration_date=datetime.now()
            )
            db_service.register_plot(plot_data)
        
        # Create alerts
        for i in range(3):
            alert_data = AlertData(
                hobli_id=hobli_id,
                timestamp=datetime.now() - timedelta(hours=i),
                plot_id=f"plot_{i:03d}",
                user_id=f"user_{i:03d}",
                risk_level="high" if i < 2 else "medium",
                message=f"Alert {i}",
                gee_proof={
                    "ndvi_value": 0.3 + (i * 0.1),
                    "moisture_index": 0.25,
                    "temperature_anomaly": 2.5
                },
                bedrock_reasoning=sample_alert_data["bedrock_reasoning"]
            )
            db_service.create_alert(alert_data)
        
        # Get statistics
        stats = db_service.get_jurisdiction_stats(hobli_id)
        
        assert stats.hobli_id == hobli_id
        assert stats.total_plots == 5
        assert stats.active_alerts == 3
        assert stats.high_priority_alerts == 2
        assert stats.avg_ndvi > 0  # Should have calculated average


class TestDataConversion:
    """Test float/Decimal conversion for DynamoDB compatibility"""
    
    def test_float_to_decimal_conversion(self, db_service):
        """Test that floats are properly converted to Decimal for DynamoDB"""
        test_data = {
            "lat": 12.9716,
            "lon": 77.5946,
            "nested": {
                "ndvi": 0.75,
                "values": [0.1, 0.2, 0.3]
            }
        }
        
        converted = db_service._convert_floats_to_decimal(test_data)
        
        from decimal import Decimal
        assert isinstance(converted["lat"], Decimal)
        assert isinstance(converted["lon"], Decimal)
        assert isinstance(converted["nested"]["ndvi"], Decimal)
        assert all(isinstance(v, Decimal) for v in converted["nested"]["values"])
    
    def test_decimal_to_float_conversion(self, db_service):
        """Test that Decimals are properly converted to float for Pydantic"""
        from decimal import Decimal
        
        test_data = {
            "lat": Decimal("12.9716"),
            "lon": Decimal("77.5946"),
            "nested": {
                "ndvi": Decimal("0.75"),
                "values": [Decimal("0.1"), Decimal("0.2"), Decimal("0.3")]
            }
        }
        
        converted = db_service._convert_decimal_to_float(test_data)
        
        assert isinstance(converted["lat"], float)
        assert isinstance(converted["lon"], float)
        assert isinstance(converted["nested"]["ndvi"], float)
        assert all(isinstance(v, float) for v in converted["nested"]["values"])


class TestJurisdictionDirectory:
    """Test jurisdiction directory and Extension Officer management"""
    
    def test_register_hobli(self, db_service, sample_hobli_directory):
        """Test Hobli registration with Extension Officer assignment"""
        from services.db_service import HobliDirectory
        
        hobli_data = HobliDirectory(
            **sample_hobli_directory,
            created_date=datetime.now(),
            last_updated=datetime.now()
        )
        
        hobli_id = db_service.register_hobli(hobli_data)
        
        assert hobli_id == sample_hobli_directory["hobli_id"]
    
    def test_get_hobli_directory(self, db_service, sample_hobli_directory):
        """Test retrieving Hobli directory entry"""
        from services.db_service import HobliDirectory
        
        # Register a Hobli first
        hobli_data = HobliDirectory(
            **sample_hobli_directory,
            created_date=datetime.now(),
            last_updated=datetime.now()
        )
        db_service.register_hobli(hobli_data)
        
        # Retrieve the Hobli directory entry
        retrieved_hobli = db_service.get_hobli_directory(sample_hobli_directory["hobli_id"])
        
        assert retrieved_hobli is not None
        assert retrieved_hobli.hobli_id == sample_hobli_directory["hobli_id"]
        assert retrieved_hobli.officer_id == sample_hobli_directory["officer_id"]
        assert retrieved_hobli.officer_name == sample_hobli_directory["officer_name"]
    
    def test_get_hobli_directory_not_found(self, db_service):
        """Test retrieving a non-existent Hobli directory entry"""
        retrieved_hobli = db_service.get_hobli_directory("nonexistent_hobli")
        
        assert retrieved_hobli is None
    
    def test_update_hobli_officer(self, db_service, sample_hobli_directory):
        """Test updating Extension Officer assignment for a Hobli"""
        from services.db_service import HobliDirectory
        
        # Register a Hobli first
        hobli_data = HobliDirectory(
            **sample_hobli_directory,
            created_date=datetime.now(),
            last_updated=datetime.now()
        )
        db_service.register_hobli(hobli_data)
        
        # Update officer assignment
        new_officer_id = "officer_002"
        new_officer_name = "Extension Officer Sharma"
        new_officer_phone = "+919876543211"
        new_officer_email = "sharma@agriculture.gov.in"
        
        db_service.update_hobli_officer(
            sample_hobli_directory["hobli_id"],
            new_officer_id,
            new_officer_name,
            new_officer_phone,
            new_officer_email
        )
        
        # Verify update
        retrieved_hobli = db_service.get_hobli_directory(sample_hobli_directory["hobli_id"])
        
        assert retrieved_hobli.officer_id == new_officer_id
        assert retrieved_hobli.officer_name == new_officer_name
        assert retrieved_hobli.officer_phone == new_officer_phone
        assert retrieved_hobli.officer_email == new_officer_email
    
    def test_get_officer_hoblis(self, db_service, sample_hobli_directory):
        """Test retrieving all Hoblis assigned to an Extension Officer"""
        from services.db_service import HobliDirectory
        
        officer_id = sample_hobli_directory["officer_id"]
        
        # Register multiple Hoblis with the same officer
        for i in range(3):
            hobli_data = HobliDirectory(
                hobli_id=f"hobli_bangalore_{i:03d}",
                hobli_name=f"Bangalore Hobli {i}",
                district="Bangalore Urban",
                state="Karnataka",
                officer_id=officer_id,
                officer_name=sample_hobli_directory["officer_name"],
                officer_phone=sample_hobli_directory["officer_phone"],
                officer_email=sample_hobli_directory["officer_email"],
                created_date=datetime.now(),
                last_updated=datetime.now()
            )
            db_service.register_hobli(hobli_data)
        
        # Retrieve Hoblis for this officer
        hoblis = db_service.get_officer_hoblis(officer_id)
        
        assert len(hoblis) == 3
        assert all(hobli.officer_id == officer_id for hobli in hoblis)
    
    def test_get_officer_plots(self, db_service, sample_plot_data, sample_hobli_directory):
        """Test retrieving all plots assigned to an Extension Officer"""
        from services.db_service import HobliDirectory, PlotData
        
        officer_id = sample_hobli_directory["officer_id"]
        
        # Register Hobli with officer
        hobli_data = HobliDirectory(
            **sample_hobli_directory,
            created_date=datetime.now(),
            last_updated=datetime.now()
        )
        db_service.register_hobli(hobli_data)
        
        # Register multiple plots in this Hobli
        for i in range(5):
            plot_data = PlotData(
                user_id=f"user_{i:03d}",
                plot_id=f"plot_{i:03d}",
                lat=sample_plot_data["lat"],
                lon=sample_plot_data["lon"],
                crop=sample_plot_data["crop"],
                hobli_id=sample_hobli_directory["hobli_id"],
                farmer_name=f"Farmer {i}",
                phone_number=f"+9198765432{i:02d}",
                registration_date=datetime.now()
            )
            db_service.register_plot(plot_data)
        
        # Retrieve plots for this officer
        plots = db_service.get_officer_plots(officer_id)
        
        assert len(plots) == 5
        assert all(plot.hobli_id == sample_hobli_directory["hobli_id"] for plot in plots)
    
    def test_get_officer_assignment(self, db_service, sample_plot_data, sample_hobli_directory, sample_alert_data):
        """Test retrieving Extension Officer assignment summary"""
        from services.db_service import HobliDirectory, PlotData, AlertData
        
        officer_id = sample_hobli_directory["officer_id"]
        
        # Register Hobli with officer
        hobli_data = HobliDirectory(
            **sample_hobli_directory,
            created_date=datetime.now(),
            last_updated=datetime.now()
        )
        db_service.register_hobli(hobli_data)
        
        # Register plots
        for i in range(3):
            plot_data = PlotData(
                user_id=f"user_{i:03d}",
                plot_id=f"plot_{i:03d}",
                lat=sample_plot_data["lat"],
                lon=sample_plot_data["lon"],
                crop=sample_plot_data["crop"],
                hobli_id=sample_hobli_directory["hobli_id"],
                farmer_name=f"Farmer {i}",
                phone_number=f"+9198765432{i:02d}",
                registration_date=datetime.now()
            )
            db_service.register_plot(plot_data)
        
        # Create alerts
        for i in range(2):
            alert_data = AlertData(
                hobli_id=sample_hobli_directory["hobli_id"],
                timestamp=datetime.now() - timedelta(hours=i),
                plot_id=f"plot_{i:03d}",
                user_id=f"user_{i:03d}",
                risk_level="high",
                message=f"Alert {i}",
                gee_proof=sample_alert_data["gee_proof"],
                bedrock_reasoning=sample_alert_data["bedrock_reasoning"]
            )
            db_service.create_alert(alert_data)
        
        # Get officer assignment
        assignment = db_service.get_officer_assignment(officer_id)
        
        assert assignment.officer_id == officer_id
        assert assignment.officer_name == sample_hobli_directory["officer_name"]
        assert len(assignment.hobli_ids) == 1
        assert assignment.total_plots == 3
        assert assignment.active_alerts == 2
    
    def test_get_officer_for_plot(self, db_service, sample_plot_data, sample_hobli_directory):
        """Test retrieving the Extension Officer assigned to a specific plot"""
        from services.db_service import HobliDirectory, PlotData
        
        # Register Hobli with officer
        hobli_data = HobliDirectory(
            **sample_hobli_directory,
            created_date=datetime.now(),
            last_updated=datetime.now()
        )
        db_service.register_hobli(hobli_data)
        
        # Register plot
        plot_data = PlotData(
            **sample_plot_data,
            registration_date=datetime.now()
        )
        db_service.register_plot(plot_data)
        
        # Get officer for plot
        officer_hobli = db_service.get_officer_for_plot(
            sample_plot_data["user_id"],
            sample_plot_data["plot_id"]
        )
        
        assert officer_hobli is not None
        assert officer_hobli.officer_id == sample_hobli_directory["officer_id"]
        assert officer_hobli.hobli_id == sample_plot_data["hobli_id"]
    
    def test_get_officer_for_nonexistent_plot(self, db_service):
        """Test retrieving officer for a non-existent plot"""
        officer_hobli = db_service.get_officer_for_plot("nonexistent_user", "nonexistent_plot")
        
        assert officer_hobli is None


class TestGSIPerformance:
    """Test Global Secondary Index (GSI) performance and functionality"""
    
    def test_hobli_gsi_query_performance(self, db_service, sample_plot_data):
        """Test hobli_id-registration_date-index GSI query performance"""
        hobli_id = sample_plot_data["hobli_id"]
        
        # Register 10 plots in the same hobli with different registration dates
        from datetime import datetime, timedelta
        for i in range(10):
            plot_data = PlotData(
                user_id=f"user_{i:03d}",
                plot_id=f"plot_{i:03d}",
                lat=sample_plot_data["lat"],
                lon=sample_plot_data["lon"],
                crop=sample_plot_data["crop"],
                hobli_id=hobli_id,
                farmer_name=f"Farmer {i}",
                phone_number=f"+9198765432{i:02d}",
                registration_date=datetime.now() - timedelta(days=i)
            )
            db_service.register_plot(plot_data)
        
        # Query using GSI - should return all plots for this hobli
        plots = db_service.get_hobli_plots(hobli_id)
        
        assert len(plots) == 10
        assert all(plot.hobli_id == hobli_id for plot in plots)
        # Verify plots are sorted by registration_date (GSI sort key)
        # Note: DynamoDB returns in ascending order by default
        for i in range(len(plots) - 1):
            assert plots[i].registration_date <= plots[i + 1].registration_date
    
    def test_risk_level_gsi_query(self, db_service, sample_alert_data):
        """Test risk_level-timestamp-index GSI query"""
        # Create alerts with different risk levels
        risk_levels = ["low", "medium", "high", "critical"]
        
        for i, risk_level in enumerate(risk_levels):
            for j in range(3):  # 3 alerts per risk level
                alert_data = AlertData(
                    hobli_id=f"hobli_{i:03d}",
                    timestamp=datetime.now() - timedelta(hours=j),
                    plot_id=f"plot_{i}_{j}",
                    user_id=f"user_{i}_{j}",
                    risk_level=risk_level,
                    message=f"{risk_level} alert {j}",
                    gee_proof=sample_alert_data["gee_proof"],
                    bedrock_reasoning=sample_alert_data["bedrock_reasoning"]
                )
                db_service.create_alert(alert_data)
        
        # Query high priority alerts using GSI
        high_priority = db_service.get_high_priority_alerts()
        
        # Should only get "high" risk level alerts (not "critical")
        assert len(high_priority) == 3
        assert all(alert.risk_level == "high" for alert in high_priority)
        # Verify sorted by timestamp descending
        for i in range(len(high_priority) - 1):
            assert high_priority[i].timestamp >= high_priority[i + 1].timestamp
    
    def test_officer_gsi_query(self, db_service, sample_hobli_directory):
        """Test officer_id-last_updated-index GSI query"""
        from services.db_service import HobliDirectory
        
        officer_id = sample_hobli_directory["officer_id"]
        
        # Register multiple Hoblis with the same officer at different times
        for i in range(5):
            hobli_data = HobliDirectory(
                hobli_id=f"hobli_bangalore_{i:03d}",
                hobli_name=f"Bangalore Hobli {i}",
                district="Bangalore Urban",
                state="Karnataka",
                officer_id=officer_id,
                officer_name=sample_hobli_directory["officer_name"],
                officer_phone=sample_hobli_directory["officer_phone"],
                officer_email=sample_hobli_directory["officer_email"],
                created_date=datetime.now() - timedelta(days=i),
                last_updated=datetime.now() - timedelta(hours=i)
            )
            db_service.register_hobli(hobli_data)
        
        # Query Hoblis for this officer
        hoblis = db_service.get_officer_hoblis(officer_id)
        
        assert len(hoblis) == 5
        assert all(hobli.officer_id == officer_id for hobli in hoblis)
    
    def test_gsi_limit_parameter(self, db_service, sample_plot_data):
        """Test that GSI queries respect limit parameter"""
        hobli_id = sample_plot_data["hobli_id"]
        
        # Register 20 plots
        for i in range(20):
            plot_data = PlotData(
                user_id=f"user_{i:03d}",
                plot_id=f"plot_{i:03d}",
                lat=sample_plot_data["lat"],
                lon=sample_plot_data["lon"],
                crop=sample_plot_data["crop"],
                hobli_id=hobli_id,
                farmer_name=f"Farmer {i}",
                phone_number=f"+9198765432{i:02d}",
                registration_date=datetime.now()
            )
            db_service.register_plot(plot_data)
        
        # Query with limit
        plots = db_service.get_hobli_plots(hobli_id, limit=10)
        
        assert len(plots) == 10


class TestJurisdictionBasedFiltering:
    """Test jurisdiction-based data filtering and querying"""
    
    def test_multi_hobli_isolation(self, db_service, sample_plot_data):
        """Test that plots from different Hoblis are properly isolated"""
        # Register plots in different Hoblis
        hobli_ids = ["hobli_bangalore_001", "hobli_mysore_001", "hobli_mandya_001"]
        
        for hobli_id in hobli_ids:
            for i in range(3):
                plot_data = PlotData(
                    user_id=f"user_{hobli_id}_{i:03d}",
                    plot_id=f"plot_{hobli_id}_{i:03d}",
                    lat=sample_plot_data["lat"],
                    lon=sample_plot_data["lon"],
                    crop=sample_plot_data["crop"],
                    hobli_id=hobli_id,
                    farmer_name=f"Farmer {i}",
                    phone_number=f"+9198765432{i:02d}",
                    registration_date=datetime.now()
                )
                db_service.register_plot(plot_data)
        
        # Query each Hobli separately
        for hobli_id in hobli_ids:
            plots = db_service.get_hobli_plots(hobli_id)
            
            # Should only get plots for this specific Hobli
            assert len(plots) == 3
            assert all(plot.hobli_id == hobli_id for plot in plots)
            assert all(hobli_id in plot.plot_id for plot in plots)
    
    def test_alert_jurisdiction_filtering(self, db_service, sample_alert_data):
        """Test that alerts are properly filtered by jurisdiction"""
        hobli_ids = ["hobli_bangalore_001", "hobli_mysore_001"]
        
        # Create alerts in different Hoblis
        for hobli_id in hobli_ids:
            for i in range(5):
                alert_data = AlertData(
                    hobli_id=hobli_id,
                    timestamp=datetime.now() - timedelta(hours=i),
                    plot_id=f"plot_{hobli_id}_{i:03d}",
                    user_id=f"user_{hobli_id}_{i:03d}",
                    risk_level="high",
                    message=f"Alert for {hobli_id}",
                    gee_proof=sample_alert_data["gee_proof"],
                    bedrock_reasoning=sample_alert_data["bedrock_reasoning"]
                )
                db_service.create_alert(alert_data)
        
        # Query alerts for each Hobli
        for hobli_id in hobli_ids:
            alerts = db_service.get_recent_alerts(hobli_id, hours=24)
            
            # Should only get alerts for this specific Hobli
            assert len(alerts) == 5
            assert all(alert.hobli_id == hobli_id for alert in alerts)
    
    def test_officer_jurisdiction_access(self, db_service, sample_plot_data, sample_hobli_directory):
        """Test that Extension Officers can only access their assigned jurisdictions"""
        from services.db_service import HobliDirectory
        
        # Create two officers with different jurisdictions
        officer1_id = "officer_001"
        officer2_id = "officer_002"
        
        # Register Hoblis for officer 1
        for i in range(3):
            hobli_data = HobliDirectory(
                hobli_id=f"hobli_officer1_{i:03d}",
                hobli_name=f"Officer 1 Hobli {i}",
                district="Bangalore Urban",
                state="Karnataka",
                officer_id=officer1_id,
                officer_name="Officer One",
                officer_phone="+919876543210",
                officer_email="officer1@agriculture.gov.in",
                created_date=datetime.now(),
                last_updated=datetime.now()
            )
            db_service.register_hobli(hobli_data)
            
            # Register plots in this Hobli
            for j in range(2):
                plot_data = PlotData(
                    user_id=f"user_{i}_{j}",
                    plot_id=f"plot_{i}_{j}",
                    lat=sample_plot_data["lat"],
                    lon=sample_plot_data["lon"],
                    crop=sample_plot_data["crop"],
                    hobli_id=f"hobli_officer1_{i:03d}",
                    farmer_name=f"Farmer {j}",
                    phone_number=f"+9198765432{j:02d}",
                    registration_date=datetime.now()
                )
                db_service.register_plot(plot_data)
        
        # Register Hoblis for officer 2
        for i in range(2):
            hobli_data = HobliDirectory(
                hobli_id=f"hobli_officer2_{i:03d}",
                hobli_name=f"Officer 2 Hobli {i}",
                district="Mysore",
                state="Karnataka",
                officer_id=officer2_id,
                officer_name="Officer Two",
                officer_phone="+919876543211",
                officer_email="officer2@agriculture.gov.in",
                created_date=datetime.now(),
                last_updated=datetime.now()
            )
            db_service.register_hobli(hobli_data)
        
        # Verify officer 1 can only access their plots
        officer1_plots = db_service.get_officer_plots(officer1_id)
        assert len(officer1_plots) == 6  # 3 Hoblis * 2 plots each
        assert all("officer1" in plot.hobli_id for plot in officer1_plots)
        
        # Verify officer 2 has no plots (we didn't register any)
        officer2_plots = db_service.get_officer_plots(officer2_id)
        assert len(officer2_plots) == 0
    
    def test_cross_jurisdiction_alert_aggregation(self, db_service, sample_alert_data):
        """Test aggregating alerts across multiple jurisdictions"""
        # Create high priority alerts in multiple Hoblis
        hobli_ids = [f"hobli_{i:03d}" for i in range(5)]
        
        for hobli_id in hobli_ids:
            for i in range(2):
                alert_data = AlertData(
                    hobli_id=hobli_id,
                    timestamp=datetime.now() - timedelta(hours=i),
                    plot_id=f"plot_{hobli_id}_{i:03d}",
                    user_id=f"user_{hobli_id}_{i:03d}",
                    risk_level="high",
                    message=f"High priority alert in {hobli_id}",
                    gee_proof=sample_alert_data["gee_proof"],
                    bedrock_reasoning=sample_alert_data["bedrock_reasoning"]
                )
                db_service.create_alert(alert_data)
        
        # Query high priority alerts across all jurisdictions
        high_priority = db_service.get_high_priority_alerts()
        
        # Should get alerts from all Hoblis
        assert len(high_priority) == 10  # 5 Hoblis * 2 alerts each
        unique_hoblis = set(alert.hobli_id for alert in high_priority)
        assert len(unique_hoblis) == 5


class TestDataConsistency:
    """Test data consistency across operations"""
    
    def test_plot_alert_consistency(self, db_service, sample_plot_data, sample_alert_data):
        """Test consistency between plot registration and alert creation"""
        # Register a plot
        plot_data = PlotData(
            **sample_plot_data,
            registration_date=datetime.now()
        )
        db_service.register_plot(plot_data)
        
        # Create an alert for this plot
        alert_data = AlertData(
            hobli_id=sample_plot_data["hobli_id"],
            timestamp=datetime.now(),
            plot_id=sample_plot_data["plot_id"],
            user_id=sample_plot_data["user_id"],
            risk_level="high",
            message="Test alert",
            gee_proof=sample_alert_data["gee_proof"],
            bedrock_reasoning=sample_alert_data["bedrock_reasoning"]
        )
        db_service.create_alert(alert_data)
        
        # Verify plot exists
        retrieved_plot = db_service.get_plot_by_id(
            sample_plot_data["user_id"],
            sample_plot_data["plot_id"]
        )
        assert retrieved_plot is not None
        
        # Verify alert exists
        alerts = db_service.get_recent_alerts(sample_plot_data["hobli_id"], hours=24)
        assert len(alerts) == 1
        assert alerts[0].plot_id == sample_plot_data["plot_id"]
        assert alerts[0].user_id == sample_plot_data["user_id"]
    
    def test_hobli_officer_plot_consistency(self, db_service, sample_plot_data, sample_hobli_directory):
        """Test consistency between Hobli directory, officer assignment, and plots"""
        from services.db_service import HobliDirectory
        
        # Register Hobli with officer
        hobli_data = HobliDirectory(
            **sample_hobli_directory,
            created_date=datetime.now(),
            last_updated=datetime.now()
        )
        db_service.register_hobli(hobli_data)
        
        # Register plot in this Hobli
        plot_data = PlotData(
            **sample_plot_data,
            registration_date=datetime.now()
        )
        db_service.register_plot(plot_data)
        
        # Verify Hobli directory entry
        hobli = db_service.get_hobli_directory(sample_hobli_directory["hobli_id"])
        assert hobli is not None
        assert hobli.officer_id == sample_hobli_directory["officer_id"]
        
        # Verify plot is in Hobli
        plots = db_service.get_hobli_plots(sample_hobli_directory["hobli_id"])
        assert len(plots) == 1
        assert plots[0].plot_id == sample_plot_data["plot_id"]
        
        # Verify officer can access plot
        officer_plots = db_service.get_officer_plots(sample_hobli_directory["officer_id"])
        assert len(officer_plots) == 1
        assert officer_plots[0].plot_id == sample_plot_data["plot_id"]
        
        # Verify officer assignment for plot
        officer_hobli = db_service.get_officer_for_plot(
            sample_plot_data["user_id"],
            sample_plot_data["plot_id"]
        )
        assert officer_hobli is not None
        assert officer_hobli.officer_id == sample_hobli_directory["officer_id"]
    
    def test_alert_status_update_consistency(self, db_service, sample_alert_data):
        """Test that alert status updates maintain data consistency"""
        # Create an alert
        alert_data = AlertData(
            **sample_alert_data,
            timestamp=datetime.now()
        )
        db_service.create_alert(alert_data)
        
        # Update alert status
        db_service.update_alert_status(
            alert_data.hobli_id,
            alert_data.timestamp,
            "acknowledged",
            "Officer has reviewed the alert"
        )
        
        # Retrieve and verify update
        alerts = db_service.get_recent_alerts(alert_data.hobli_id, hours=24)
        assert len(alerts) == 1
        assert alerts[0].resolution_status == "acknowledged"
        assert alerts[0].officer_response == "Officer has reviewed the alert"
        
        # Update again to resolved
        db_service.update_alert_status(
            alert_data.hobli_id,
            alert_data.timestamp,
            "resolved",
            "Issue has been addressed"
        )
        
        # Verify second update
        alerts = db_service.get_recent_alerts(alert_data.hobli_id, hours=24)
        assert len(alerts) == 1
        assert alerts[0].resolution_status == "resolved"
        assert alerts[0].officer_response == "Issue has been addressed"
    
    def test_jurisdiction_stats_consistency(self, db_service, sample_plot_data, sample_alert_data):
        """Test that jurisdiction statistics are consistent with underlying data"""
        hobli_id = sample_plot_data["hobli_id"]
        
        # Register 5 plots
        for i in range(5):
            plot_data = PlotData(
                user_id=f"user_{i:03d}",
                plot_id=f"plot_{i:03d}",
                lat=sample_plot_data["lat"],
                lon=sample_plot_data["lon"],
                crop=sample_plot_data["crop"],
                hobli_id=hobli_id,
                farmer_name=f"Farmer {i}",
                phone_number=f"+9198765432{i:02d}",
                registration_date=datetime.now()
            )
            db_service.register_plot(plot_data)
        
        # Create 3 alerts (2 high priority, 1 medium)
        for i in range(3):
            alert_data = AlertData(
                hobli_id=hobli_id,
                timestamp=datetime.now() - timedelta(hours=i),
                plot_id=f"plot_{i:03d}",
                user_id=f"user_{i:03d}",
                risk_level="high" if i < 2 else "medium",
                message=f"Alert {i}",
                gee_proof={
                    "ndvi_value": 0.3 + (i * 0.05),
                    "moisture_index": 0.25,
                    "temperature_anomaly": 2.5
                },
                bedrock_reasoning=sample_alert_data["bedrock_reasoning"]
            )
            db_service.create_alert(alert_data)
        
        # Get statistics
        stats = db_service.get_jurisdiction_stats(hobli_id)
        
        # Verify consistency
        assert stats.total_plots == 5
        assert stats.active_alerts == 3
        assert stats.high_priority_alerts == 2
        
        # Verify NDVI calculation
        expected_avg_ndvi = (0.3 + 0.35 + 0.4) / 3
        assert abs(stats.avg_ndvi - expected_avg_ndvi) < 0.01
    
    def test_concurrent_plot_registration(self, db_service, sample_plot_data):
        """Test that concurrent plot registrations maintain consistency"""
        hobli_id = sample_plot_data["hobli_id"]
        
        # Register multiple plots with same hobli_id
        plot_ids = []
        for i in range(10):
            plot_data = PlotData(
                user_id=f"user_{i:03d}",
                plot_id=f"plot_{i:03d}",
                lat=sample_plot_data["lat"],
                lon=sample_plot_data["lon"],
                crop=sample_plot_data["crop"],
                hobli_id=hobli_id,
                farmer_name=f"Farmer {i}",
                phone_number=f"+9198765432{i:02d}",
                registration_date=datetime.now()
            )
            returned_id = db_service.register_plot(plot_data)
            plot_ids.append(returned_id)
        
        # Verify all plots were registered
        assert len(plot_ids) == 10
        assert len(set(plot_ids)) == 10  # All unique
        
        # Verify all plots can be retrieved
        plots = db_service.get_hobli_plots(hobli_id)
        assert len(plots) == 10
        
        # Verify each plot can be retrieved individually
        for i in range(10):
            plot = db_service.get_plot_by_id(f"user_{i:03d}", f"plot_{i:03d}")
            assert plot is not None
            assert plot.plot_id == f"plot_{i:03d}"


class TestEdgeCases:
    """Test edge cases and error handling"""
    
    def test_empty_hobli_query(self, db_service):
        """Test querying a Hobli with no plots"""
        plots = db_service.get_hobli_plots("nonexistent_hobli")
        assert len(plots) == 0
    
    def test_empty_alert_query(self, db_service):
        """Test querying alerts for a Hobli with no alerts"""
        alerts = db_service.get_recent_alerts("nonexistent_hobli", hours=24)
        assert len(alerts) == 0
    
    def test_old_alerts_filtered_out(self, db_service, sample_alert_data):
        """Test that old alerts are properly filtered by time range"""
        hobli_id = sample_alert_data["hobli_id"]
        
        # Create an old alert (48 hours ago)
        old_alert = AlertData(
            hobli_id=hobli_id,
            timestamp=datetime.now() - timedelta(hours=48),
            plot_id="plot_old",
            user_id="user_old",
            risk_level="high",
            message="Old alert",
            gee_proof=sample_alert_data["gee_proof"],
            bedrock_reasoning=sample_alert_data["bedrock_reasoning"]
        )
        db_service.create_alert(old_alert)
        
        # Create a recent alert (1 hour ago)
        recent_alert = AlertData(
            hobli_id=hobli_id,
            timestamp=datetime.now() - timedelta(hours=1),
            plot_id="plot_recent",
            user_id="user_recent",
            risk_level="high",
            message="Recent alert",
            gee_proof=sample_alert_data["gee_proof"],
            bedrock_reasoning=sample_alert_data["bedrock_reasoning"]
        )
        db_service.create_alert(recent_alert)
        
        # Query last 24 hours
        alerts = db_service.get_recent_alerts(hobli_id, hours=24)
        
        # Should only get recent alert
        assert len(alerts) == 1
        assert alerts[0].plot_id == "plot_recent"
    
    def test_plot_with_no_last_analysis(self, db_service, sample_plot_data):
        """Test handling plots with no last_analysis timestamp"""
        plot_data = PlotData(
            **sample_plot_data,
            registration_date=datetime.now(),
            last_analysis=None
        )
        db_service.register_plot(plot_data)
        
        retrieved_plot = db_service.get_plot_by_id(
            sample_plot_data["user_id"],
            sample_plot_data["plot_id"]
        )
        
        assert retrieved_plot is not None
        assert retrieved_plot.last_analysis is None
    
    def test_alert_with_no_officer_response(self, db_service, sample_alert_data):
        """Test handling alerts with no officer response"""
        alert_data = AlertData(
            **sample_alert_data,
            timestamp=datetime.now(),
            officer_response=None
        )
        db_service.create_alert(alert_data)
        
        alerts = db_service.get_recent_alerts(sample_alert_data["hobli_id"], hours=24)
        
        assert len(alerts) == 1
        assert alerts[0].officer_response is None
    
    def test_officer_with_no_hoblis(self, db_service):
        """Test querying officer with no assigned Hoblis"""
        hoblis = db_service.get_officer_hoblis("nonexistent_officer")
        assert len(hoblis) == 0
    
    def test_officer_assignment_with_no_hoblis(self, db_service):
        """Test getting assignment for officer with no Hoblis"""
        assignment = db_service.get_officer_assignment("nonexistent_officer")
        
        assert assignment.officer_id == "nonexistent_officer"
        assert assignment.officer_name == "Unknown"
        assert len(assignment.hobli_ids) == 0
        assert assignment.total_plots == 0
        assert assignment.active_alerts == 0
    
    def test_jurisdiction_stats_with_no_data(self, db_service):
        """Test calculating statistics for Hobli with no data"""
        stats = db_service.get_jurisdiction_stats("nonexistent_hobli")
        
        assert stats.hobli_id == "nonexistent_hobli"
        assert stats.total_plots == 0
        assert stats.active_alerts == 0
        assert stats.high_priority_alerts == 0
        assert stats.avg_ndvi == 0.0
    
    def test_high_ndvi_values(self, db_service, sample_alert_data):
        """Test handling high NDVI values (healthy vegetation)"""
        alert_data = AlertData(
            hobli_id=sample_alert_data["hobli_id"],
            timestamp=datetime.now(),
            plot_id=sample_alert_data["plot_id"],
            user_id=sample_alert_data["user_id"],
            risk_level="low",
            message="Healthy vegetation",
            gee_proof={
                "ndvi_value": 0.95,  # Very high NDVI
                "moisture_index": 0.85,
                "temperature_anomaly": 0.0
            },
            bedrock_reasoning="High NDVI indicates healthy vegetation"
        )
        db_service.create_alert(alert_data)
        
        alerts = db_service.get_recent_alerts(sample_alert_data["hobli_id"], hours=24)
        
        assert len(alerts) == 1
        assert alerts[0].gee_proof["ndvi_value"] == 0.95
    
    def test_negative_ndvi_values(self, db_service, sample_alert_data):
        """Test handling negative NDVI values (water/snow)"""
        alert_data = AlertData(
            hobli_id=sample_alert_data["hobli_id"],
            timestamp=datetime.now(),
            plot_id=sample_alert_data["plot_id"],
            user_id=sample_alert_data["user_id"],
            risk_level="critical",
            message="Possible flooding",
            gee_proof={
                "ndvi_value": -0.25,  # Negative NDVI (water)
                "moisture_index": 0.95,
                "temperature_anomaly": -1.0
            },
            bedrock_reasoning="Negative NDVI may indicate flooding"
        )
        db_service.create_alert(alert_data)
        
        alerts = db_service.get_recent_alerts(sample_alert_data["hobli_id"], hours=24)
        
        assert len(alerts) == 1
        assert alerts[0].gee_proof["ndvi_value"] == -0.25
