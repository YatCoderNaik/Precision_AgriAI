"""
DynamoDB Table Creation Script

Creates the two DynamoDB tables required for Precision AgriAI:
1. PrecisionAgri_Plots - Plot registration and metadata
2. PrecisionAgri_Alerts - Alert history and jurisdiction-based querying
"""

import boto3
from botocore.exceptions import ClientError
import sys
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def create_plots_table(dynamodb_client, table_name: str = "PrecisionAgri_Plots", enable_encryption: bool = True):
    """
    Create PrecisionAgri_Plots table with GSI for hobli_id
    
    Table Schema:
    - PK: user_id (String)
    - SK: plot_id (String)
    - GSI-1: hobli_id (PK), registration_date (SK)
    
    Args:
        dynamodb_client: Boto3 DynamoDB client
        table_name: Name of the table to create
        enable_encryption: Enable encryption at rest
    """
    try:
        table_config = {
            'TableName': table_name,
            'KeySchema': [
                {'AttributeName': 'user_id', 'KeyType': 'HASH'},  # Partition key
                {'AttributeName': 'plot_id', 'KeyType': 'RANGE'}  # Sort key
            ],
            'AttributeDefinitions': [
                {'AttributeName': 'user_id', 'AttributeType': 'S'},
                {'AttributeName': 'plot_id', 'AttributeType': 'S'},
                {'AttributeName': 'hobli_id', 'AttributeType': 'S'},
                {'AttributeName': 'registration_date', 'AttributeType': 'S'}
            ],
            'GlobalSecondaryIndexes': [
                {
                    'IndexName': 'hobli_id-registration_date-index',
                    'KeySchema': [
                        {'AttributeName': 'hobli_id', 'KeyType': 'HASH'},
                        {'AttributeName': 'registration_date', 'KeyType': 'RANGE'}
                    ],
                    'Projection': {'ProjectionType': 'ALL'},
                    'ProvisionedThroughput': {
                        'ReadCapacityUnits': 5,
                        'WriteCapacityUnits': 5
                    }
                }
            ],
            'BillingMode': 'PROVISIONED',
            'ProvisionedThroughput': {
                'ReadCapacityUnits': 5,
                'WriteCapacityUnits': 5
            },
            'Tags': [
                {'Key': 'Project', 'Value': 'PrecisionAgriAI'},
                {'Key': 'Environment', 'Value': 'Development'}
            ]
        }
        
        # Add encryption configuration if enabled
        if enable_encryption:
            table_config['SSESpecification'] = {
                'Enabled': True,
                'SSEType': 'KMS'
            }
        
        response = dynamodb_client.create_table(**table_config)
        
        logger.info(f"Creating table {table_name}...")
        
        # Wait for table to be created
        waiter = dynamodb_client.get_waiter('table_exists')
        waiter.wait(TableName=table_name)
        
        logger.info(f"✓ Table {table_name} created successfully")
        
        # Enable point-in-time recovery
        try:
            dynamodb_client.update_continuous_backups(
                TableName=table_name,
                PointInTimeRecoverySpecification={'PointInTimeRecoveryEnabled': True}
            )
            logger.info(f"✓ Point-in-time recovery enabled for {table_name}")
        except ClientError as e:
            logger.warning(f"Could not enable point-in-time recovery: {e}")
        
        return response
        
    except ClientError as e:
        if e.response['Error']['Code'] == 'ResourceInUseException':
            logger.warning(f"Table {table_name} already exists")
        else:
            logger.error(f"Error creating table {table_name}: {e}")
            raise


def create_alerts_table(dynamodb_client, table_name: str = "PrecisionAgri_Alerts", enable_encryption: bool = True):
    """
    Create PrecisionAgri_Alerts table with GSI for risk_level
    
    Table Schema:
    - PK: hobli_id (String)
    - SK: timestamp (String) - ISO format for chronological ordering
    - GSI-1: risk_level (PK), timestamp (SK)
    
    Args:
        dynamodb_client: Boto3 DynamoDB client
        table_name: Name of the table to create
        enable_encryption: Enable encryption at rest
    """
    try:
        table_config = {
            'TableName': table_name,
            'KeySchema': [
                {'AttributeName': 'hobli_id', 'KeyType': 'HASH'},  # Partition key
                {'AttributeName': 'timestamp', 'KeyType': 'RANGE'}  # Sort key
            ],
            'AttributeDefinitions': [
                {'AttributeName': 'hobli_id', 'AttributeType': 'S'},
                {'AttributeName': 'timestamp', 'AttributeType': 'S'},
                {'AttributeName': 'risk_level', 'AttributeType': 'S'}
            ],
            'GlobalSecondaryIndexes': [
                {
                    'IndexName': 'risk_level-timestamp-index',
                    'KeySchema': [
                        {'AttributeName': 'risk_level', 'KeyType': 'HASH'},
                        {'AttributeName': 'timestamp', 'KeyType': 'RANGE'}
                    ],
                    'Projection': {'ProjectionType': 'ALL'},
                    'ProvisionedThroughput': {
                        'ReadCapacityUnits': 5,
                        'WriteCapacityUnits': 5
                    }
                }
            ],
            'BillingMode': 'PROVISIONED',
            'ProvisionedThroughput': {
                'ReadCapacityUnits': 5,
                'WriteCapacityUnits': 5
            },
            'Tags': [
                {'Key': 'Project', 'Value': 'PrecisionAgriAI'},
                {'Key': 'Environment', 'Value': 'Development'}
            ]
        }
        
        # Add encryption configuration if enabled
        if enable_encryption:
            table_config['SSESpecification'] = {
                'Enabled': True,
                'SSEType': 'KMS'
            }
        
        response = dynamodb_client.create_table(**table_config)
        
        logger.info(f"Creating table {table_name}...")
        
        # Wait for table to be created
        waiter = dynamodb_client.get_waiter('table_exists')
        waiter.wait(TableName=table_name)
        
        logger.info(f"✓ Table {table_name} created successfully")
        
        # Enable point-in-time recovery
        try:
            dynamodb_client.update_continuous_backups(
                TableName=table_name,
                PointInTimeRecoverySpecification={'PointInTimeRecoveryEnabled': True}
            )
            logger.info(f"✓ Point-in-time recovery enabled for {table_name}")
        except ClientError as e:
            logger.warning(f"Could not enable point-in-time recovery: {e}")
        
        return response
        
    except ClientError as e:
        if e.response['Error']['Code'] == 'ResourceInUseException':
            logger.warning(f"Table {table_name} already exists")
        else:
            logger.error(f"Error creating table {table_name}: {e}")
            raise


def create_hobli_directory_table(dynamodb_client, table_name: str = "PrecisionAgri_HobliDirectory", enable_encryption: bool = True):
    """
    Create PrecisionAgri_HobliDirectory table for jurisdiction-officer mapping
    
    Table Schema:
    - PK: hobli_id (String)
    - GSI-1: officer_id (PK), last_updated (SK)
    
    Args:
        dynamodb_client: Boto3 DynamoDB client
        table_name: Name of the table to create
        enable_encryption: Enable encryption at rest
    """
    try:
        table_config = {
            'TableName': table_name,
            'KeySchema': [
                {'AttributeName': 'hobli_id', 'KeyType': 'HASH'}  # Partition key
            ],
            'AttributeDefinitions': [
                {'AttributeName': 'hobli_id', 'AttributeType': 'S'},
                {'AttributeName': 'officer_id', 'AttributeType': 'S'},
                {'AttributeName': 'last_updated', 'AttributeType': 'S'}
            ],
            'GlobalSecondaryIndexes': [
                {
                    'IndexName': 'officer_id-last_updated-index',
                    'KeySchema': [
                        {'AttributeName': 'officer_id', 'KeyType': 'HASH'},
                        {'AttributeName': 'last_updated', 'KeyType': 'RANGE'}
                    ],
                    'Projection': {'ProjectionType': 'ALL'},
                    'ProvisionedThroughput': {
                        'ReadCapacityUnits': 5,
                        'WriteCapacityUnits': 5
                    }
                }
            ],
            'BillingMode': 'PROVISIONED',
            'ProvisionedThroughput': {
                'ReadCapacityUnits': 5,
                'WriteCapacityUnits': 5
            },
            'Tags': [
                {'Key': 'Project', 'Value': 'PrecisionAgriAI'},
                {'Key': 'Environment', 'Value': 'Development'}
            ]
        }
        
        # Add encryption configuration if enabled
        if enable_encryption:
            table_config['SSESpecification'] = {
                'Enabled': True,
                'SSEType': 'KMS'
            }
        
        response = dynamodb_client.create_table(**table_config)
        
        logger.info(f"Creating table {table_name}...")
        
        # Wait for table to be created
        waiter = dynamodb_client.get_waiter('table_exists')
        waiter.wait(TableName=table_name)
        
        logger.info(f"✓ Table {table_name} created successfully")
        
        # Enable point-in-time recovery
        try:
            dynamodb_client.update_continuous_backups(
                TableName=table_name,
                PointInTimeRecoverySpecification={'PointInTimeRecoveryEnabled': True}
            )
            logger.info(f"✓ Point-in-time recovery enabled for {table_name}")
        except ClientError as e:
            logger.warning(f"Could not enable point-in-time recovery: {e}")
        
        return response
        
    except ClientError as e:
        if e.response['Error']['Code'] == 'ResourceInUseException':
            logger.warning(f"Table {table_name} already exists")
        else:
            logger.error(f"Error creating table {table_name}: {e}")
            raise


def delete_table(dynamodb_client, table_name: str):
    """
    Delete a DynamoDB table (use with caution!)
    
    Args:
        dynamodb_client: Boto3 DynamoDB client
        table_name: Name of table to delete
    """
    try:
        logger.warning(f"Deleting table {table_name}...")
        dynamodb_client.delete_table(TableName=table_name)
        
        # Wait for table to be deleted
        waiter = dynamodb_client.get_waiter('table_not_exists')
        waiter.wait(TableName=table_name)
        
        logger.info(f"✓ Table {table_name} deleted successfully")
        
    except ClientError as e:
        if e.response['Error']['Code'] == 'ResourceNotFoundException':
            logger.warning(f"Table {table_name} does not exist")
        else:
            logger.error(f"Error deleting table {table_name}: {e}")
            raise


def validate_tables(dynamodb_client, plots_table: str, alerts_table: str, hobli_directory_table: str):
    """
    Validate that DynamoDB tables exist and are configured correctly
    
    Args:
        dynamodb_client: Boto3 DynamoDB client
        plots_table: Name of plots table
        alerts_table: Name of alerts table
        hobli_directory_table: Name of hobli directory table
        
    Returns:
        Dictionary with validation results
    """
    results = {}
    
    for table_name in [plots_table, alerts_table, hobli_directory_table]:
        try:
            response = dynamodb_client.describe_table(TableName=table_name)
            table_info = response['Table']
            
            results[table_name] = {
                'exists': True,
                'status': table_info['TableStatus'],
                'item_count': table_info.get('ItemCount', 0),
                'size_bytes': table_info.get('TableSizeBytes', 0),
                'gsi_count': len(table_info.get('GlobalSecondaryIndexes', [])),
                'encryption_enabled': 'SSEDescription' in table_info
            }
            
            logger.info(f"✓ Table {table_name} exists (Status: {table_info['TableStatus']})")
            
        except ClientError as e:
            if e.response['Error']['Code'] == 'ResourceNotFoundException':
                results[table_name] = {'exists': False, 'error': 'Table not found'}
                logger.error(f"✗ Table {table_name} does not exist")
            else:
                results[table_name] = {'exists': False, 'error': str(e)}
                logger.error(f"✗ Error checking table {table_name}: {e}")
    
    return results


def main():
    """Main execution function"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Manage DynamoDB tables for Precision AgriAI')
    parser.add_argument(
        '--action',
        choices=['create', 'delete', 'recreate', 'validate'],
        default='create',
        help='Action to perform (default: create)'
    )
    parser.add_argument(
        '--region',
        default='ap-south-1',
        help='AWS region (default: ap-south-1)'
    )
    parser.add_argument(
        '--plots-table',
        default='PrecisionAgri_Plots',
        help='Plots table name (default: PrecisionAgri_Plots)'
    )
    parser.add_argument(
        '--alerts-table',
        default='PrecisionAgri_Alerts',
        help='Alerts table name (default: PrecisionAgri_Alerts)'
    )
    parser.add_argument(
        '--hobli-directory-table',
        default='PrecisionAgri_HobliDirectory',
        help='Hobli directory table name (default: PrecisionAgri_HobliDirectory)'
    )
    parser.add_argument(
        '--enable-encryption',
        action='store_true',
        default=True,
        help='Enable encryption at rest (default: True)'
    )
    
    args = parser.parse_args()
    
    # Initialize DynamoDB client
    try:
        dynamodb = boto3.client('dynamodb', region_name=args.region)
        logger.info(f"Connected to DynamoDB in region: {args.region}")
    except Exception as e:
        logger.error(f"Failed to connect to DynamoDB: {e}")
        sys.exit(1)
    
    # Execute action
    try:
        if args.action == 'create':
            logger.info("Creating DynamoDB tables...")
            create_plots_table(dynamodb, args.plots_table, args.enable_encryption)
            create_alerts_table(dynamodb, args.alerts_table, args.enable_encryption)
            create_hobli_directory_table(dynamodb, args.hobli_directory_table, args.enable_encryption)
            logger.info("✓ All tables created successfully")
            
        elif args.action == 'validate':
            logger.info("Validating DynamoDB tables...")
            results = validate_tables(dynamodb, args.plots_table, args.alerts_table, args.hobli_directory_table)
            
            print("\n" + "="*60)
            print("DynamoDB Table Validation Results")
            print("="*60)
            for table_name, info in results.items():
                print(f"\n{table_name}:")
                for key, value in info.items():
                    print(f"  {key}: {value}")
            print("="*60 + "\n")
            
        elif args.action == 'delete':
            logger.warning("⚠️  WARNING: This will delete all data in the tables!")
            confirm = input("Type 'DELETE' to confirm: ")
            if confirm == 'DELETE':
                delete_table(dynamodb, args.plots_table)
                delete_table(dynamodb, args.alerts_table)
                delete_table(dynamodb, args.hobli_directory_table)
                logger.info("✓ All tables deleted successfully")
            else:
                logger.info("Deletion cancelled")
                
        elif args.action == 'recreate':
            logger.warning("⚠️  WARNING: This will delete and recreate all tables!")
            confirm = input("Type 'RECREATE' to confirm: ")
            if confirm == 'RECREATE':
                delete_table(dynamodb, args.plots_table)
                delete_table(dynamodb, args.alerts_table)
                delete_table(dynamodb, args.hobli_directory_table)
                create_plots_table(dynamodb, args.plots_table, args.enable_encryption)
                create_alerts_table(dynamodb, args.alerts_table, args.enable_encryption)
                create_hobli_directory_table(dynamodb, args.hobli_directory_table, args.enable_encryption)
                logger.info("✓ All tables recreated successfully")
            else:
                logger.info("Recreation cancelled")
                
    except Exception as e:
        logger.error(f"Operation failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
