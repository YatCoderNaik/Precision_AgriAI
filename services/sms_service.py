"""
SMS Service - AWS SNS Integration for Alert Notifications

Handles SMS notifications for:
- Farmer alerts (crop health issues)
- Extension Officer alerts (jurisdiction-wide issues)
- Deep link generation for app access
"""

from typing import Optional, Dict, Any, List
from pydantic import BaseModel
from datetime import datetime
import logging
import boto3
from botocore.exceptions import ClientError
import urllib.parse

from config.settings import get_settings

logger = logging.getLogger(__name__)


class SMSNotification(BaseModel):
    """SMS notification data"""
    recipient_phone: str
    message: str
    notification_type: str  # 'farmer_alert', 'officer_alert', 'cluster_alert'
    deep_link: Optional[str] = None
    sent_at: Optional[datetime] = None
    message_id: Optional[str] = None
    delivery_status: Optional[str] = None


class SMSDeliveryStatus(BaseModel):
    """SMS delivery status tracking"""
    message_id: str
    phone_number: str
    status: str  # 'pending', 'delivered', 'failed'
    timestamp: datetime
    error_message: Optional[str] = None


class SMSService:
    """Service for SMS notifications via AWS SNS"""
    
    def __init__(self, region: Optional[str] = None, app_base_url: Optional[str] = None):
        """
        Initialize SMSService with AWS SNS client
        
        Args:
            region: AWS region (defaults to settings)
            app_base_url: Base URL for deep links (defaults to settings)
        """
        settings = get_settings()
        self.region = region or settings.aws.region
        self.app_base_url = app_base_url or "https://precision-agriai.example.com"
        
        # Initialize AWS SNS client
        self.sns = boto3.client('sns', region_name=self.region)
        
        # SMS attributes for India
        self.sms_attributes = {
            'AWS.SNS.SMS.SMSType': 'Transactional',  # High priority
            'AWS.SNS.SMS.SenderID': 'AgriAI'  # Sender ID (may not work in all regions)
        }
        
        # Delivery tracking
        self.delivery_tracking: Dict[str, SMSDeliveryStatus] = {}
        
        logger.info(f"SMSService initialized with region={self.region}")
    
    async def send_farmer_alert(
        self,
        farmer_phone: str,
        farmer_name: str,
        plot_id: str,
        risk_level: str,
        ndvi_value: float,
        recommendations: List[str]
    ) -> SMSNotification:
        """
        Send SMS alert to farmer about crop health issue
        
        Args:
            farmer_phone: Farmer's phone number (+91XXXXXXXXXX)
            farmer_name: Farmer's name
            plot_id: Plot identifier
            risk_level: Risk level (low, medium, high, critical)
            ndvi_value: NDVI value
            recommendations: List of recommendations
            
        Returns:
            SMSNotification with delivery details
            
        Raises:
            ClientError: If SNS API fails
        """
        try:
            # Generate deep link to plot analysis
            deep_link = self._generate_deep_link('plot_analysis', plot_id=plot_id)
            
            # Construct farmer-friendly message
            risk_emoji = {
                'low': '🟢',
                'medium': '🟡',
                'high': '🟠',
                'critical': '🔴'
            }
            
            emoji = risk_emoji.get(risk_level, '⚪')
            
            if risk_level in ['high', 'critical']:
                urgency = "URGENT: "
            else:
                urgency = ""
            
            # Keep message concise (SMS limit: 160 chars for single message)
            message = f"{urgency}{emoji} Precision AgriAI Alert\n\n"
            message += f"Plot {plot_id}: {risk_level.upper()} risk\n"
            message += f"NDVI: {ndvi_value:.2f}\n\n"
            
            # Add first recommendation
            if recommendations:
                message += f"Action: {recommendations[0][:50]}\n\n"
            
            message += f"View details: {deep_link}"
            
            # Send SMS via SNS
            response = self.sns.publish(
                PhoneNumber=farmer_phone,
                Message=message,
                MessageAttributes={
                    'AWS.SNS.SMS.SMSType': {
                        'DataType': 'String',
                        'StringValue': 'Transactional'
                    }
                }
            )
            
            message_id = response['MessageId']
            
            logger.info(f"Sent farmer alert SMS to {farmer_phone}: {message_id}")
            
            # Create notification record
            notification = SMSNotification(
                recipient_phone=farmer_phone,
                message=message,
                notification_type='farmer_alert',
                deep_link=deep_link,
                sent_at=datetime.now(),
                message_id=message_id,
                delivery_status='pending'
            )
            
            # Track delivery
            self.delivery_tracking[message_id] = SMSDeliveryStatus(
                message_id=message_id,
                phone_number=farmer_phone,
                status='pending',
                timestamp=datetime.now()
            )
            
            return notification
            
        except ClientError as e:
            logger.error(f"Failed to send farmer alert SMS: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error sending farmer alert: {e}")
            raise
    
    async def send_officer_alert(
        self,
        officer_phone: str,
        officer_name: str,
        hobli_id: str,
        hobli_name: str,
        alert_count: int,
        high_priority_count: int
    ) -> SMSNotification:
        """
        Send SMS alert to Extension Officer about jurisdiction issues
        
        Args:
            officer_phone: Officer's phone number
            officer_name: Officer's name
            hobli_id: Hobli identifier
            hobli_name: Hobli name
            alert_count: Total alert count
            high_priority_count: High priority alert count
            
        Returns:
            SMSNotification with delivery details
        """
        try:
            # Generate deep link to officer dashboard
            deep_link = self._generate_deep_link('officer_dashboard', hobli_id=hobli_id)
            
            # Construct officer message
            message = f"🏛️ Precision AgriAI - Officer Alert\n\n"
            message += f"Jurisdiction: {hobli_name}\n"
            message += f"Total Alerts: {alert_count}\n"
            message += f"High Priority: {high_priority_count}\n\n"
            message += f"View dashboard: {deep_link}"
            
            # Send SMS
            response = self.sns.publish(
                PhoneNumber=officer_phone,
                Message=message,
                MessageAttributes={
                    'AWS.SNS.SMS.SMSType': {
                        'DataType': 'String',
                        'StringValue': 'Transactional'
                    }
                }
            )
            
            message_id = response['MessageId']
            
            logger.info(f"Sent officer alert SMS to {officer_phone}: {message_id}")
            
            notification = SMSNotification(
                recipient_phone=officer_phone,
                message=message,
                notification_type='officer_alert',
                deep_link=deep_link,
                sent_at=datetime.now(),
                message_id=message_id,
                delivery_status='pending'
            )
            
            self.delivery_tracking[message_id] = SMSDeliveryStatus(
                message_id=message_id,
                phone_number=officer_phone,
                status='pending',
                timestamp=datetime.now()
            )
            
            return notification
            
        except ClientError as e:
            logger.error(f"Failed to send officer alert SMS: {e}")
            raise
    
    async def send_cluster_alert(
        self,
        officer_phone: str,
        officer_name: str,
        hobli_id: str,
        hobli_name: str,
        affected_plots: int,
        avg_ndvi: float,
        severity: str
    ) -> SMSNotification:
        """
        Send SMS alert about cluster outbreak to Extension Officer
        
        Args:
            officer_phone: Officer's phone number
            officer_name: Officer's name
            hobli_id: Hobli identifier
            hobli_name: Hobli name
            affected_plots: Number of affected plots
            avg_ndvi: Average NDVI across affected plots
            severity: Severity level
            
        Returns:
            SMSNotification with delivery details
        """
        try:
            deep_link = self._generate_deep_link('cluster_analysis', hobli_id=hobli_id)
            
            message = f"🚨 CLUSTER OUTBREAK DETECTED\n\n"
            message += f"Jurisdiction: {hobli_name}\n"
            message += f"Affected Plots: {affected_plots}\n"
            message += f"Avg NDVI: {avg_ndvi:.2f}\n"
            message += f"Severity: {severity.upper()}\n\n"
            message += f"Immediate action required!\n"
            message += f"View analysis: {deep_link}"
            
            response = self.sns.publish(
                PhoneNumber=officer_phone,
                Message=message,
                MessageAttributes={
                    'AWS.SNS.SMS.SMSType': {
                        'DataType': 'String',
                        'StringValue': 'Transactional'
                    }
                }
            )
            
            message_id = response['MessageId']
            
            logger.info(f"Sent cluster alert SMS to {officer_phone}: {message_id}")
            
            notification = SMSNotification(
                recipient_phone=officer_phone,
                message=message,
                notification_type='cluster_alert',
                deep_link=deep_link,
                sent_at=datetime.now(),
                message_id=message_id,
                delivery_status='pending'
            )
            
            self.delivery_tracking[message_id] = SMSDeliveryStatus(
                message_id=message_id,
                phone_number=officer_phone,
                status='pending',
                timestamp=datetime.now()
            )
            
            return notification
            
        except ClientError as e:
            logger.error(f"Failed to send cluster alert SMS: {e}")
            raise
    
    def _generate_deep_link(self, view: str, **params) -> str:
        """
        Generate deep link to specific app view
        
        Args:
            view: View name ('plot_analysis', 'officer_dashboard', 'cluster_analysis')
            **params: View-specific parameters
            
        Returns:
            Deep link URL
        """
        # Encode parameters
        query_params = urllib.parse.urlencode(params)
        
        # Construct deep link
        deep_link = f"{self.app_base_url}/{view}"
        if query_params:
            deep_link += f"?{query_params}"
        
        return deep_link
    
    def get_delivery_status(self, message_id: str) -> Optional[SMSDeliveryStatus]:
        """
        Get delivery status for a message
        
        Args:
            message_id: SNS message ID
            
        Returns:
            SMSDeliveryStatus or None if not found
        """
        return self.delivery_tracking.get(message_id)
    
    def get_all_delivery_statuses(self) -> List[SMSDeliveryStatus]:
        """
        Get all delivery statuses
        
        Returns:
            List of SMSDeliveryStatus
        """
        return list(self.delivery_tracking.values())
    
    def clear_delivery_tracking(self):
        """Clear delivery tracking data"""
        self.delivery_tracking.clear()
        logger.info("Delivery tracking cleared")
    
    def get_service_info(self) -> Dict[str, Any]:
        """
        Get service information and status
        
        Returns:
            Dictionary with service information
        """
        return {
            'service': 'SMSService',
            'region': self.region,
            'app_base_url': self.app_base_url,
            'tracked_messages': len(self.delivery_tracking),
            'sms_type': self.sms_attributes['AWS.SNS.SMS.SMSType']
        }
