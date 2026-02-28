"""
DbService - DynamoDB Operations

Handles all database operations and data persistence including:
- Plot registration and management
- Alert creation and tracking
- Jurisdiction-based data querying
- Officer dashboard data aggregation
"""

from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
from datetime import datetime, timedelta
from decimal import Decimal
import logging
import boto3
from botocore.exceptions import ClientError
from config.settings import get_settings

logger = logging.getLogger(__name__)


class PlotData(BaseModel):
    """Plot registration data"""
    user_id: str
    plot_id: str
    lat: float
    lon: float
    crop: str
    hobli_id: str
    farmer_name: str
    phone_number: str
    registration_date: datetime
    last_analysis: Optional[datetime] = None
    status: str = "active"
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class AlertData(BaseModel):
    """Alert data for DynamoDB storage"""
    hobli_id: str
    timestamp: datetime
    plot_id: str
    user_id: str
    risk_level: str
    message: str
    gee_proof: Dict[str, Any]
    bedrock_reasoning: str
    officer_response: Optional[str] = None
    resolution_status: str = "pending"
    sms_sent: bool = False
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class JurisdictionStats(BaseModel):
    """Aggregated statistics for a jurisdiction"""
    hobli_id: str
    total_plots: int
    active_alerts: int
    high_priority_alerts: int
    avg_ndvi: float
    last_updated: datetime


class HobliDirectory(BaseModel):
    """Hobli directory entry mapping jurisdiction to Extension Officer"""
    hobli_id: str
    hobli_name: str
    district: str
    state: str
    officer_id: str
    officer_name: str
    officer_phone: str
    officer_email: str
    created_date: datetime
    last_updated: datetime
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class OfficerAssignment(BaseModel):
    """Extension Officer assignment data"""
    officer_id: str
    officer_name: str
    hobli_ids: List[str]
    total_plots: int
    active_alerts: int
    last_updated: datetime

    class HobliDirectory(BaseModel):
        """Hobli directory entry mapping jurisdiction to Extension Officer"""
        hobli_id: str
        hobli_name: str
        district: str
        state: str
        officer_id: str
        officer_name: str
        officer_phone: str
        officer_email: str
        created_date: datetime
        last_updated: datetime

        class Config:
            json_encoders = {
                datetime: lambda v: v.isoformat()
            }


    class OfficerAssignment(BaseModel):
        """Extension Officer assignment data"""
        officer_id: str
        officer_name: str
        hobli_ids: List[str]
        total_plots: int
        active_alerts: int
        last_updated: datetime


class DbService:
    """Service for DynamoDB operations and data persistence"""
    
    def __init__(self, region: Optional[str] = None):
        """
        Initialize DbService with DynamoDB client
        
        Args:
            region: AWS region (defaults to settings)
        """
        settings = get_settings()
        
        # Initialize boto3 DynamoDB resource
        self.region = region or settings.aws.region
        self.dynamodb = boto3.resource('dynamodb', region_name=self.region)
        
        # Get table names from settings
        self.plots_table_name = settings.aws.dynamodb_plots_table
        self.alerts_table_name = settings.aws.dynamodb_alerts_table
        self.hobli_directory_table_name = "PrecisionAgri_HobliDirectory"
        
        # Initialize table references
        self.plots_table = self.dynamodb.Table(self.plots_table_name)
        self.alerts_table = self.dynamodb.Table(self.alerts_table_name)
        self.hobli_directory_table = self.dynamodb.Table(self.hobli_directory_table_name)
        
        # Configuration
        self.query_limit = settings.db_service.query_limit
        
        logger.info(f"DbService initialized with region={self.region}, "
                   f"plots_table={self.plots_table_name}, "
                   f"alerts_table={self.alerts_table_name}, "
                   f"hobli_directory_table={self.hobli_directory_table_name}")
    
    def _convert_floats_to_decimal(self, obj: Any) -> Any:
        """
        Convert float values to Decimal for DynamoDB compatibility
        
        Args:
            obj: Object to convert
            
        Returns:
            Object with floats converted to Decimal
        """
        if isinstance(obj, float):
            return Decimal(str(obj))
        elif isinstance(obj, dict):
            return {k: self._convert_floats_to_decimal(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [self._convert_floats_to_decimal(item) for item in obj]
        return obj
    
    def _convert_decimal_to_float(self, obj: Any) -> Any:
        """
        Convert Decimal values to float for Pydantic compatibility
        
        Args:
            obj: Object to convert
            
        Returns:
            Object with Decimals converted to float
        """
        if isinstance(obj, Decimal):
            return float(obj)
        elif isinstance(obj, dict):
            return {k: self._convert_decimal_to_float(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [self._convert_decimal_to_float(item) for item in obj]
        return obj
    
    def register_plot(self, plot_data: PlotData) -> str:
        """
        Register a new plot in DynamoDB
        
        Args:
            plot_data: Plot registration data
            
        Returns:
            Plot ID
            
        Raises:
            ClientError: If DynamoDB operation fails
        """
        try:
            # Prepare item for DynamoDB
            item = {
                'user_id': plot_data.user_id,
                'plot_id': plot_data.plot_id,
                'lat': self._convert_floats_to_decimal(plot_data.lat),
                'lon': self._convert_floats_to_decimal(plot_data.lon),
                'crop': plot_data.crop,
                'hobli_id': plot_data.hobli_id,
                'farmer_name': plot_data.farmer_name,
                'phone_number': plot_data.phone_number,
                'registration_date': plot_data.registration_date.isoformat(),
                'status': plot_data.status
            }
            
            # Add optional fields
            if plot_data.last_analysis:
                item['last_analysis'] = plot_data.last_analysis.isoformat()
            
            # Write to DynamoDB
            self.plots_table.put_item(Item=item)
            
            logger.info(f"Successfully registered plot: {plot_data.plot_id} for user: {plot_data.user_id}")
            
            return plot_data.plot_id
            
        except ClientError as e:
            logger.error(f"Failed to register plot {plot_data.plot_id}: {e}")
            raise
    
    def create_alert(self, alert_data: AlertData) -> None:
        """
        Create a new alert in DynamoDB
        
        Args:
            alert_data: Alert data to store
            
        Raises:
            ClientError: If DynamoDB operation fails
        """
        try:
            # Prepare item for DynamoDB
            item = {
                'hobli_id': alert_data.hobli_id,
                'timestamp': alert_data.timestamp.isoformat(),
                'plot_id': alert_data.plot_id,
                'user_id': alert_data.user_id,
                'risk_level': alert_data.risk_level,
                'message': alert_data.message,
                'gee_proof': self._convert_floats_to_decimal(alert_data.gee_proof),
                'bedrock_reasoning': alert_data.bedrock_reasoning,
                'resolution_status': alert_data.resolution_status,
                'sms_sent': alert_data.sms_sent
            }
            
            # Add optional fields
            if alert_data.officer_response:
                item['officer_response'] = alert_data.officer_response
            
            # Write to DynamoDB
            self.alerts_table.put_item(Item=item)
            
            logger.info(f"Successfully created alert for hobli: {alert_data.hobli_id}, "
                       f"plot: {alert_data.plot_id}, risk_level: {alert_data.risk_level}")
            
        except ClientError as e:
            logger.error(f"Failed to create alert for hobli {alert_data.hobli_id}: {e}")
            raise
    
    def get_hobli_plots(self, hobli_id: str, limit: Optional[int] = None) -> List[PlotData]:
        """
        Get all plots for a specific jurisdiction using GSI
        
        Args:
            hobli_id: Hobli identifier
            limit: Maximum number of results (defaults to query_limit from settings)
            
        Returns:
            List of PlotData for the jurisdiction
            
        Raises:
            ClientError: If DynamoDB operation fails
        """
        try:
            # Query using GSI on hobli_id
            query_params = {
                'IndexName': 'hobli_id-registration_date-index',
                'KeyConditionExpression': 'hobli_id = :hobli_id',
                'ExpressionAttributeValues': {
                    ':hobli_id': hobli_id
                },
                'Limit': limit or self.query_limit
            }
            
            response = self.plots_table.query(**query_params)
            items = response.get('Items', [])
            
            # Convert to PlotData objects
            plots = []
            for item in items:
                # Convert Decimal to float
                item = self._convert_decimal_to_float(item)
                
                plot = PlotData(
                    user_id=item['user_id'],
                    plot_id=item['plot_id'],
                    lat=item['lat'],
                    lon=item['lon'],
                    crop=item['crop'],
                    hobli_id=item['hobli_id'],
                    farmer_name=item['farmer_name'],
                    phone_number=item['phone_number'],
                    registration_date=datetime.fromisoformat(item['registration_date']),
                    last_analysis=datetime.fromisoformat(item['last_analysis']) if item.get('last_analysis') else None,
                    status=item.get('status', 'active')
                )
                plots.append(plot)
            
            logger.info(f"Retrieved {len(plots)} plots for hobli: {hobli_id}")
            
            return plots
            
        except ClientError as e:
            logger.error(f"Failed to retrieve plots for hobli {hobli_id}: {e}")
            raise
    
    def get_recent_alerts(
        self, 
        hobli_id: str, 
        hours: int = 24,
        limit: Optional[int] = None
    ) -> List[AlertData]:
        """
        Get recent alerts for a jurisdiction within a time range
        
        Args:
            hobli_id: Hobli identifier
            hours: Number of hours to look back
            limit: Maximum number of results (defaults to query_limit from settings)
            
        Returns:
            List of AlertData within the time range
            
        Raises:
            ClientError: If DynamoDB operation fails
        """
        try:
            # Calculate time threshold
            time_threshold = datetime.now() - timedelta(hours=hours)
            time_threshold_str = time_threshold.isoformat()
            
            # Query alerts by hobli_id with timestamp filter
            query_params = {
                'KeyConditionExpression': 'hobli_id = :hobli_id AND #ts >= :time_threshold',
                'ExpressionAttributeNames': {
                    '#ts': 'timestamp'
                },
                'ExpressionAttributeValues': {
                    ':hobli_id': hobli_id,
                    ':time_threshold': time_threshold_str
                },
                'Limit': limit or self.query_limit,
                'ScanIndexForward': False  # Sort by timestamp descending (newest first)
            }
            
            response = self.alerts_table.query(**query_params)
            items = response.get('Items', [])
            
            # Convert to AlertData objects
            alerts = []
            for item in items:
                # Convert Decimal to float
                item = self._convert_decimal_to_float(item)
                
                alert = AlertData(
                    hobli_id=item['hobli_id'],
                    timestamp=datetime.fromisoformat(item['timestamp']),
                    plot_id=item['plot_id'],
                    user_id=item['user_id'],
                    risk_level=item['risk_level'],
                    message=item['message'],
                    gee_proof=item['gee_proof'],
                    bedrock_reasoning=item['bedrock_reasoning'],
                    officer_response=item.get('officer_response'),
                    resolution_status=item.get('resolution_status', 'pending'),
                    sms_sent=item.get('sms_sent', False)
                )
                alerts.append(alert)
            
            logger.info(f"Retrieved {len(alerts)} alerts for hobli: {hobli_id} (last {hours} hours)")
            
            return alerts
            
        except ClientError as e:
            logger.error(f"Failed to retrieve alerts for hobli {hobli_id}: {e}")
            raise
    
    def get_jurisdiction_stats(self, hobli_id: str) -> JurisdictionStats:
        """
        Get aggregated statistics for a jurisdiction
        
        Args:
            hobli_id: Hobli identifier
            
        Returns:
            JurisdictionStats with aggregated data
            
        Raises:
            ClientError: If DynamoDB operation fails
        """
        try:
            # Get all plots for the jurisdiction
            plots = self.get_hobli_plots(hobli_id, limit=1000)
            
            # Get recent alerts (last 24 hours)
            recent_alerts = self.get_recent_alerts(hobli_id, hours=24, limit=1000)
            
            # Calculate statistics
            total_plots = len(plots)
            active_alerts = len([a for a in recent_alerts if a.resolution_status == 'pending'])
            high_priority_alerts = len([a for a in recent_alerts if a.risk_level in ['high', 'critical']])
            
            # Calculate average NDVI from recent alerts
            ndvi_values = []
            for alert in recent_alerts:
                if 'ndvi_value' in alert.gee_proof:
                    ndvi_values.append(float(alert.gee_proof['ndvi_value']))
            
            avg_ndvi = sum(ndvi_values) / len(ndvi_values) if ndvi_values else 0.0
            
            stats = JurisdictionStats(
                hobli_id=hobli_id,
                total_plots=total_plots,
                active_alerts=active_alerts,
                high_priority_alerts=high_priority_alerts,
                avg_ndvi=avg_ndvi,
                last_updated=datetime.now()
            )
            
            logger.info(f"Calculated statistics for hobli: {hobli_id} - "
                       f"{total_plots} plots, {active_alerts} active alerts")
            
            return stats
            
        except ClientError as e:
            logger.error(f"Failed to calculate statistics for hobli {hobli_id}: {e}")
            raise
    
    def update_alert_status(
        self, 
        hobli_id: str, 
        timestamp: datetime, 
        status: str,
        officer_response: Optional[str] = None
    ) -> None:
        """
        Update alert resolution status
        
        Args:
            hobli_id: Hobli identifier
            timestamp: Alert timestamp
            status: New resolution status
            officer_response: Optional officer response text
            
        Raises:
            ClientError: If DynamoDB operation fails
        """
        try:
            # Prepare update expression
            update_expr = "SET resolution_status = :status"
            expr_values = {':status': status}
            
            if officer_response:
                update_expr += ", officer_response = :response"
                expr_values[':response'] = officer_response
            
            # Update item in DynamoDB
            self.alerts_table.update_item(
                Key={
                    'hobli_id': hobli_id,
                    'timestamp': timestamp.isoformat()
                },
                UpdateExpression=update_expr,
                ExpressionAttributeValues=expr_values
            )
            
            logger.info(f"Updated alert status: {hobli_id} @ {timestamp} -> {status}")
            
        except ClientError as e:
            logger.error(f"Failed to update alert status for {hobli_id} @ {timestamp}: {e}")
            raise
    
    def get_plot_by_id(self, user_id: str, plot_id: str) -> Optional[PlotData]:
        """
        Get a specific plot by ID
        
        Args:
            user_id: User identifier
            plot_id: Plot identifier
            
        Returns:
            PlotData or None if not found
            
        Raises:
            ClientError: If DynamoDB operation fails
        """
        try:
            # Get item from DynamoDB
            response = self.plots_table.get_item(
                Key={
                    'user_id': user_id,
                    'plot_id': plot_id
                }
            )
            
            item = response.get('Item')
            
            if not item:
                logger.info(f"Plot not found: {user_id}/{plot_id}")
                return None
            
            # Convert Decimal to float
            item = self._convert_decimal_to_float(item)
            
            # Convert to PlotData
            plot = PlotData(
                user_id=item['user_id'],
                plot_id=item['plot_id'],
                lat=item['lat'],
                lon=item['lon'],
                crop=item['crop'],
                hobli_id=item['hobli_id'],
                farmer_name=item['farmer_name'],
                phone_number=item['phone_number'],
                registration_date=datetime.fromisoformat(item['registration_date']),
                last_analysis=datetime.fromisoformat(item['last_analysis']) if item.get('last_analysis') else None,
                status=item.get('status', 'active')
            )
            
            logger.info(f"Retrieved plot: {user_id}/{plot_id}")
            
            return plot
            
        except ClientError as e:
            logger.error(f"Failed to retrieve plot {user_id}/{plot_id}: {e}")
            raise
    
    def update_plot_last_analysis(self, user_id: str, plot_id: str, timestamp: datetime) -> None:
        """
        Update the last analysis timestamp for a plot
        
        Args:
            user_id: User identifier
            plot_id: Plot identifier
            timestamp: Analysis timestamp
            
        Raises:
            ClientError: If DynamoDB operation fails
        """
        try:
            self.plots_table.update_item(
                Key={
                    'user_id': user_id,
                    'plot_id': plot_id
                },
                UpdateExpression="SET last_analysis = :timestamp",
                ExpressionAttributeValues={
                    ':timestamp': timestamp.isoformat()
                }
            )
            
            logger.info(f"Updated last_analysis for plot: {user_id}/{plot_id}")
            
        except ClientError as e:
            logger.error(f"Failed to update last_analysis for plot {user_id}/{plot_id}: {e}")
            raise
    
    def get_high_priority_alerts(self, limit: Optional[int] = None) -> List[AlertData]:
        """
        Get high priority alerts across all jurisdictions using GSI
        
        Args:
            limit: Maximum number of results (defaults to query_limit from settings)
            
        Returns:
            List of high priority AlertData
            
        Raises:
            ClientError: If DynamoDB operation fails
        """
        try:
            # Query using GSI on risk_level
            query_params = {
                'IndexName': 'risk_level-timestamp-index',
                'KeyConditionExpression': 'risk_level = :risk_level',
                'ExpressionAttributeValues': {
                    ':risk_level': 'high'
                },
                'Limit': limit or self.query_limit,
                'ScanIndexForward': False  # Sort by timestamp descending
            }
            
            response = self.alerts_table.query(**query_params)
            items = response.get('Items', [])
            
            # Convert to AlertData objects
            alerts = []
            for item in items:
                # Convert Decimal to float
                item = self._convert_decimal_to_float(item)
                
                alert = AlertData(
                    hobli_id=item['hobli_id'],
                    timestamp=datetime.fromisoformat(item['timestamp']),
                    plot_id=item['plot_id'],
                    user_id=item['user_id'],
                    risk_level=item['risk_level'],
                    message=item['message'],
                    gee_proof=item['gee_proof'],
                    bedrock_reasoning=item['bedrock_reasoning'],
                    officer_response=item.get('officer_response'),
                    resolution_status=item.get('resolution_status', 'pending'),
                    sms_sent=item.get('sms_sent', False)
                )
                alerts.append(alert)
            
            logger.info(f"Retrieved {len(alerts)} high priority alerts")
            
            return alerts
            
        except ClientError as e:
            logger.error(f"Failed to retrieve high priority alerts: {e}")
            raise
    
    # Jurisdiction Directory Management Methods
    
    def register_hobli(self, hobli_data: HobliDirectory) -> str:
        """
        Register a Hobli in the directory with Extension Officer assignment
        
        Args:
            hobli_data: Hobli directory entry data
            
        Returns:
            Hobli ID
            
        Raises:
            ClientError: If DynamoDB operation fails
        """
        try:
            # Prepare item for DynamoDB
            item = {
                'hobli_id': hobli_data.hobli_id,
                'hobli_name': hobli_data.hobli_name,
                'district': hobli_data.district,
                'state': hobli_data.state,
                'officer_id': hobli_data.officer_id,
                'officer_name': hobli_data.officer_name,
                'officer_phone': hobli_data.officer_phone,
                'officer_email': hobli_data.officer_email,
                'created_date': hobli_data.created_date.isoformat(),
                'last_updated': hobli_data.last_updated.isoformat()
            }
            
            # Write to DynamoDB
            self.hobli_directory_table.put_item(Item=item)
            
            logger.info(f"Successfully registered Hobli: {hobli_data.hobli_id} "
                       f"with officer: {hobli_data.officer_id}")
            
            return hobli_data.hobli_id
            
        except ClientError as e:
            logger.error(f"Failed to register Hobli {hobli_data.hobli_id}: {e}")
            raise
    
    def get_hobli_directory(self, hobli_id: str) -> Optional[HobliDirectory]:
        """
        Get Hobli directory entry including Extension Officer assignment
        
        Args:
            hobli_id: Hobli identifier
            
        Returns:
            HobliDirectory or None if not found
            
        Raises:
            ClientError: If DynamoDB operation fails
        """
        try:
            # Get item from DynamoDB
            response = self.hobli_directory_table.get_item(
                Key={'hobli_id': hobli_id}
            )
            
            item = response.get('Item')
            
            if not item:
                logger.info(f"Hobli directory entry not found: {hobli_id}")
                return None
            
            # Convert to HobliDirectory
            hobli = HobliDirectory(
                hobli_id=item['hobli_id'],
                hobli_name=item['hobli_name'],
                district=item['district'],
                state=item['state'],
                officer_id=item['officer_id'],
                officer_name=item['officer_name'],
                officer_phone=item['officer_phone'],
                officer_email=item['officer_email'],
                created_date=datetime.fromisoformat(item['created_date']),
                last_updated=datetime.fromisoformat(item['last_updated'])
            )
            
            logger.info(f"Retrieved Hobli directory entry: {hobli_id}")
            
            return hobli
            
        except ClientError as e:
            logger.error(f"Failed to retrieve Hobli directory entry {hobli_id}: {e}")
            raise
    
    def update_hobli_officer(
        self, 
        hobli_id: str, 
        officer_id: str,
        officer_name: str,
        officer_phone: str,
        officer_email: str
    ) -> None:
        """
        Update Extension Officer assignment for a Hobli
        
        Args:
            hobli_id: Hobli identifier
            officer_id: New officer identifier
            officer_name: Officer name
            officer_phone: Officer phone number
            officer_email: Officer email
            
        Raises:
            ClientError: If DynamoDB operation fails
        """
        try:
            # Update item in DynamoDB
            self.hobli_directory_table.update_item(
                Key={'hobli_id': hobli_id},
                UpdateExpression="SET officer_id = :officer_id, "
                               "officer_name = :officer_name, "
                               "officer_phone = :officer_phone, "
                               "officer_email = :officer_email, "
                               "last_updated = :last_updated",
                ExpressionAttributeValues={
                    ':officer_id': officer_id,
                    ':officer_name': officer_name,
                    ':officer_phone': officer_phone,
                    ':officer_email': officer_email,
                    ':last_updated': datetime.now().isoformat()
                }
            )
            
            logger.info(f"Updated officer assignment for Hobli: {hobli_id} -> {officer_id}")
            
        except ClientError as e:
            logger.error(f"Failed to update officer for Hobli {hobli_id}: {e}")
            raise
    
    def get_officer_hoblis(self, officer_id: str) -> List[HobliDirectory]:
        """
        Get all Hoblis assigned to an Extension Officer
        
        Args:
            officer_id: Extension Officer identifier
            
        Returns:
            List of HobliDirectory entries for the officer
            
        Raises:
            ClientError: If DynamoDB operation fails
        """
        try:
            # Scan for all hoblis with this officer_id
            # Note: In production, this should use a GSI on officer_id
            response = self.hobli_directory_table.scan(
                FilterExpression='officer_id = :officer_id',
                ExpressionAttributeValues={
                    ':officer_id': officer_id
                }
            )
            
            items = response.get('Items', [])
            
            # Convert to HobliDirectory objects
            hoblis = []
            for item in items:
                hobli = HobliDirectory(
                    hobli_id=item['hobli_id'],
                    hobli_name=item['hobli_name'],
                    district=item['district'],
                    state=item['state'],
                    officer_id=item['officer_id'],
                    officer_name=item['officer_name'],
                    officer_phone=item['officer_phone'],
                    officer_email=item['officer_email'],
                    created_date=datetime.fromisoformat(item['created_date']),
                    last_updated=datetime.fromisoformat(item['last_updated'])
                )
                hoblis.append(hobli)
            
            logger.info(f"Retrieved {len(hoblis)} Hoblis for officer: {officer_id}")
            
            return hoblis
            
        except ClientError as e:
            logger.error(f"Failed to retrieve Hoblis for officer {officer_id}: {e}")
            raise
    
    def get_officer_plots(self, officer_id: str, limit: Optional[int] = None) -> List[PlotData]:
        """
        Get all plots assigned to an Extension Officer across their jurisdictions
        
        Args:
            officer_id: Extension Officer identifier
            limit: Maximum number of results (defaults to query_limit from settings)
            
        Returns:
            List of PlotData for all plots in officer's jurisdictions
            
        Raises:
            ClientError: If DynamoDB operation fails
        """
        try:
            # Get all Hoblis for this officer
            hoblis = self.get_officer_hoblis(officer_id)
            
            # Collect plots from all Hoblis
            all_plots = []
            remaining_limit = limit or self.query_limit
            
            for hobli in hoblis:
                if remaining_limit <= 0:
                    break
                
                # Get plots for this Hobli
                plots = self.get_hobli_plots(hobli.hobli_id, limit=remaining_limit)
                all_plots.extend(plots)
                remaining_limit -= len(plots)
            
            logger.info(f"Retrieved {len(all_plots)} plots for officer: {officer_id}")
            
            return all_plots[:limit] if limit else all_plots
            
        except ClientError as e:
            logger.error(f"Failed to retrieve plots for officer {officer_id}: {e}")
            raise
    
    def get_officer_assignment(self, officer_id: str) -> OfficerAssignment:
        """
        Get Extension Officer assignment summary with statistics
        
        Args:
            officer_id: Extension Officer identifier
            
        Returns:
            OfficerAssignment with aggregated data
            
        Raises:
            ClientError: If DynamoDB operation fails
        """
        try:
            # Get all Hoblis for this officer
            hoblis = self.get_officer_hoblis(officer_id)
            
            if not hoblis:
                # Return empty assignment if no Hoblis found
                return OfficerAssignment(
                    officer_id=officer_id,
                    officer_name="Unknown",
                    hobli_ids=[],
                    total_plots=0,
                    active_alerts=0,
                    last_updated=datetime.now()
                )
            
            # Aggregate statistics across all Hoblis
            hobli_ids = [h.hobli_id for h in hoblis]
            officer_name = hoblis[0].officer_name  # All should have same officer name
            
            total_plots = 0
            active_alerts = 0
            
            for hobli in hoblis:
                stats = self.get_jurisdiction_stats(hobli.hobli_id)
                total_plots += stats.total_plots
                active_alerts += stats.active_alerts
            
            assignment = OfficerAssignment(
                officer_id=officer_id,
                officer_name=officer_name,
                hobli_ids=hobli_ids,
                total_plots=total_plots,
                active_alerts=active_alerts,
                last_updated=datetime.now()
            )
            
            logger.info(f"Retrieved assignment for officer: {officer_id} - "
                       f"{len(hobli_ids)} Hoblis, {total_plots} plots, {active_alerts} active alerts")
            
            return assignment
            
        except ClientError as e:
            logger.error(f"Failed to retrieve assignment for officer {officer_id}: {e}")
            raise
    
    def get_officer_for_plot(self, user_id: str, plot_id: str) -> Optional[HobliDirectory]:
        """
        Get the Extension Officer assigned to a specific plot
        
        Args:
            user_id: User identifier
            plot_id: Plot identifier
            
        Returns:
            HobliDirectory with officer information or None if not found
            
        Raises:
            ClientError: If DynamoDB operation fails
        """
        try:
            # Get the plot
            plot = self.get_plot_by_id(user_id, plot_id)
            
            if not plot:
                logger.info(f"Plot not found: {user_id}/{plot_id}")
                return None
            
            # Get the Hobli directory entry
            hobli = self.get_hobli_directory(plot.hobli_id)
            
            if hobli:
                logger.info(f"Found officer {hobli.officer_id} for plot {plot_id}")
            else:
                logger.info(f"No officer assigned to Hobli {plot.hobli_id}")
            
            return hobli
            
        except ClientError as e:
            logger.error(f"Failed to get officer for plot {user_id}/{plot_id}: {e}")
            raise
