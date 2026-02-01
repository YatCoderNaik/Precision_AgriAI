#!/usr/bin/env python3
"""
Generate architecture diagrams for Precision AgriAI system
"""

import matplotlib.pyplot as plt
import matplotlib.patches as patches
from matplotlib.patches import FancyBboxPatch, ConnectionPatch
import numpy as np

# Set up the figure style
plt.style.use('default')
plt.rcParams['font.size'] = 10
plt.rcParams['font.family'] = 'sans-serif'

def create_user_interaction_diagram():
    """Create User Interaction Diagram"""
    fig, ax = plt.subplots(1, 1, figsize=(14, 10))
    ax.set_xlim(0, 14)
    ax.set_ylim(0, 10)
    ax.axis('off')
    
    # Colors
    user_color = '#e1f5fe'
    interface_color = '#f3e5f5'
    system_color = '#ffebee'
    output_color = '#e8f5e8'
    
    # Primary Users
    users_box = FancyBboxPatch((0.5, 7.5), 3, 2, boxstyle="round,pad=0.1", 
                               facecolor=user_color, edgecolor='black', linewidth=1.5)
    ax.add_patch(users_box)
    ax.text(2, 8.5, 'Primary Users', ha='center', va='center', fontweight='bold', fontsize=12)
    ax.text(2, 8.1, '• Extension Officer\n• Farmer\n• Cooperative Manager\n• Sustainability Planner', 
            ha='center', va='center', fontsize=9)
    
    # User Interfaces
    interface_box = FancyBboxPatch((4.5, 7.5), 3, 2, boxstyle="round,pad=0.1", 
                                   facecolor=interface_color, edgecolor='black', linewidth=1.5)
    ax.add_patch(interface_box)
    ax.text(6, 8.5, 'User Interfaces', ha='center', va='center', fontweight='bold', fontsize=12)
    ax.text(6, 8.1, '• Technical Web Dashboard\n• Mobile Farmer Interface\n• Interactive Map Interface\n• GPS Location Service', 
            ha='center', va='center', fontsize=9)
    
    # Core System
    system_box = FancyBboxPatch((5.5, 4.5), 3, 2, boxstyle="round,pad=0.1", 
                                facecolor=system_color, edgecolor='black', linewidth=1.5)
    ax.add_patch(system_box)
    ax.text(7, 5.5, 'Precision AgriAI\nSystem', ha='center', va='center', fontweight='bold', fontsize=12)
    
    # Outputs
    output_box = FancyBboxPatch((10, 7.5), 3, 2, boxstyle="round,pad=0.1", 
                                facecolor=output_color, edgecolor='black', linewidth=1.5)
    ax.add_patch(output_box)
    ax.text(11.5, 8.5, 'Outputs', ha='center', va='center', fontweight='bold', fontsize=12)
    ax.text(11.5, 8.1, '• Technical Analysis Report\n• Farmer-Friendly Guidance\n• Visual Stress Indicators\n• Audio Narration\n• Multi-Language Support', 
            ha='center', va='center', fontsize=9)
    
    # Arrows
    # Users to Interfaces
    arrow1 = ConnectionPatch((3.5, 8.5), (4.5, 8.5), "data", "data",
                            arrowstyle="->", shrinkA=5, shrinkB=5, mutation_scale=20, fc="black")
    ax.add_patch(arrow1)
    
    # Interfaces to System
    arrow2 = ConnectionPatch((6, 7.5), (7, 6.5), "data", "data",
                            arrowstyle="->", shrinkA=5, shrinkB=5, mutation_scale=20, fc="black")
    ax.add_patch(arrow2)
    
    # System to Outputs
    arrow3 = ConnectionPatch((8.5, 5.5), (10, 8.5), "data", "data",
                            arrowstyle="->", shrinkA=5, shrinkB=5, mutation_scale=20, fc="black")
    ax.add_patch(arrow3)
    
    # Outputs back to Users
    arrow4 = ConnectionPatch((10, 8.5), (3.5, 8.5), "data", "data",
                            arrowstyle="->", shrinkA=5, shrinkB=5, mutation_scale=20, fc="black",
                            connectionstyle="arc3,rad=0.3")
    ax.add_patch(arrow4)
    
    # User type specific connections
    ax.text(1, 6.5, 'Extension Officers\n& Managers', ha='center', va='center', fontsize=9, 
            bbox=dict(boxstyle="round,pad=0.3", facecolor='lightblue', alpha=0.7))
    ax.text(1, 3.5, 'Farmers', ha='center', va='center', fontsize=9,
            bbox=dict(boxstyle="round,pad=0.3", facecolor='lightgreen', alpha=0.7))
    
    # Connection lines for user types
    ax.plot([1, 4.5], [6.5, 8.2], 'b--', alpha=0.6, linewidth=1)
    ax.plot([1, 4.5], [3.5, 7.8], 'g--', alpha=0.6, linewidth=1)
    
    ax.set_title('Precision AgriAI - User Interaction Diagram', fontsize=16, fontweight='bold', pad=20)
    
    plt.tight_layout()
    plt.savefig('user_interaction_diagram.png', dpi=300, bbox_inches='tight', 
                facecolor='white', edgecolor='none')
    plt.close()

def create_system_architecture_diagram():
    """Create System Architecture Diagram"""
    fig, ax = plt.subplots(1, 1, figsize=(16, 12))
    ax.set_xlim(0, 16)
    ax.set_ylim(0, 12)
    ax.axis('off')
    
    # Colors for different layers
    user_color = '#e3f2fd'
    api_color = '#f3e5f5'
    app_color = '#e8f5e8'
    agent_color = '#fff3e0'
    output_color = '#fce4ec'
    external_color = '#f1f8e9'
    data_color = '#fff8e1'
    
    # User Layer
    user_box = FancyBboxPatch((1, 10), 14, 1.5, boxstyle="round,pad=0.1", 
                              facecolor=user_color, edgecolor='black', linewidth=1.5)
    ax.add_patch(user_box)
    ax.text(8, 10.75, 'User Layer', ha='center', va='center', fontweight='bold', fontsize=12)
    ax.text(3, 10.4, 'Extension Officer\nInterface', ha='center', va='center', fontsize=9)
    ax.text(6, 10.4, 'Farmer Mobile\nInterface', ha='center', va='center', fontsize=9)
    ax.text(9, 10.4, 'Interactive\nMap', ha='center', va='center', fontsize=9)
    ax.text(12, 10.4, 'GPS\nService', ha='center', va='center', fontsize=9)
    
    # API Gateway Layer
    api_box = FancyBboxPatch((1, 8.5), 14, 1, boxstyle="round,pad=0.1", 
                             facecolor=api_color, edgecolor='black', linewidth=1.5)
    ax.add_patch(api_box)
    ax.text(8, 9, 'API Gateway & Load Balancer', ha='center', va='center', fontweight='bold', fontsize=12)
    
    # Application Layer
    app_box = FancyBboxPatch((1, 5), 14, 3, boxstyle="round,pad=0.1", 
                             facecolor=app_color, edgecolor='black', linewidth=1.5)
    ax.add_patch(app_box)
    ax.text(8, 7.5, 'Application Layer', ha='center', va='center', fontweight='bold', fontsize=12)
    
    # Input Processing
    ax.text(3, 7, 'Input Processing', ha='center', va='center', fontweight='bold', fontsize=10)
    ax.text(3, 6.5, '• Coordinate Validator\n• GPS Location Service\n• Map Interface Handler', 
            ha='center', va='center', fontsize=8)
    
    # Core Processing Pipeline
    ax.text(8, 7, 'Core Processing Pipeline', ha='center', va='center', fontweight='bold', fontsize=10)
    ax.text(8, 6.3, '• AlphaEarth API Client\n• Embedding Summarizer\n• Environmental Context Integrator\n• Signal Fusion Engine\n• Deterministic Interpreter', 
            ha='center', va='center', fontsize=8)
    
    # Output Processing
    ax.text(13, 7, 'Output Processing', ha='center', va='center', fontweight='bold', fontsize=10)
    ax.text(13, 6.5, '• Explanation Formatter\n• Farmer-Friendly Formatter\n• Translation Service\n• Audio Service', 
            ha='center', va='center', fontsize=8)
    
    # Agentic AI Layer
    agent_box = FancyBboxPatch((4, 3.5), 8, 1, boxstyle="round,pad=0.1", 
                               facecolor=agent_color, edgecolor='black', linewidth=1.5)
    ax.add_patch(agent_box)
    ax.text(8, 4, 'Agentic AI Layer (Conditional)', ha='center', va='center', fontweight='bold', fontsize=12)
    ax.text(6, 3.7, 'Risk Review\nAgent', ha='center', va='center', fontsize=9)
    ax.text(8, 3.7, 'Sustainability\nJustification Agent', ha='center', va='center', fontsize=9)
    ax.text(10, 3.7, 'Explanation\nAgent', ha='center', va='center', fontsize=9)
    
    # External Services
    external_box = FancyBboxPatch((1, 1.5), 6, 1.5, boxstyle="round,pad=0.1", 
                                  facecolor=external_color, edgecolor='black', linewidth=1.5)
    ax.add_patch(external_box)
    ax.text(4, 2.5, 'External Services', ha='center', va='center', fontweight='bold', fontsize=12)
    ax.text(2.5, 2, 'AlphaEarth\nAPI', ha='center', va='center', fontsize=9)
    ax.text(4, 2, 'Weather\nAPI', ha='center', va='center', fontsize=9)
    ax.text(5.5, 2, 'Soil Data\nAPI', ha='center', va='center', fontsize=9)
    
    # Data Layer
    data_box = FancyBboxPatch((9, 1.5), 6, 1.5, boxstyle="round,pad=0.1", 
                              facecolor=data_color, edgecolor='black', linewidth=1.5)
    ax.add_patch(data_box)
    ax.text(12, 2.5, 'Data Layer', ha='center', va='center', fontweight='bold', fontsize=12)
    ax.text(10.5, 2, 'Redis\nCache', ha='center', va='center', fontsize=9)
    ax.text(12, 2, 'Logging\nSystem', ha='center', va='center', fontsize=9)
    ax.text(13.5, 2, 'Metrics\nStore', ha='center', va='center', fontsize=9)
    
    # Connection arrows
    # User to API
    ax.arrow(8, 10, 0, -0.4, head_width=0.2, head_length=0.1, fc='black', ec='black')
    # API to App
    ax.arrow(8, 8.5, 0, -0.4, head_width=0.2, head_length=0.1, fc='black', ec='black')
    # App to AI (conditional)
    ax.arrow(8, 5, 0, -0.4, head_width=0.2, head_length=0.1, fc='orange', ec='orange', linestyle='--')
    ax.text(8.5, 4.7, 'Conditional', ha='left', va='center', fontsize=8, color='orange')
    
    # External connections
    ax.arrow(4, 3, 0, -0.4, head_width=0.2, head_length=0.1, fc='green', ec='green')
    ax.arrow(12, 3, 0, -0.4, head_width=0.2, head_length=0.1, fc='blue', ec='blue')
    
    ax.set_title('Precision AgriAI - System Architecture Diagram', fontsize=16, fontweight='bold', pad=20)
    
    plt.tight_layout()
    plt.savefig('system_architecture_diagram.png', dpi=300, bbox_inches='tight', 
                facecolor='white', edgecolor='none')
    plt.close()

def create_aws_deployment_diagram():
    """Create AWS Deployment Architecture Diagram"""
    fig, ax = plt.subplots(1, 1, figsize=(18, 14))
    ax.set_xlim(0, 18)
    ax.set_ylim(0, 14)
    ax.axis('off')
    
    # Colors
    user_color = '#e3f2fd'
    edge_color = '#f3e5f5'
    compute_color = '#e8f5e8'
    ai_color = '#fff3e0'
    data_color = '#fce4ec'
    external_color = '#f1f8e9'
    security_color = '#fafafa'
    
    # User Access
    user_box = FancyBboxPatch((1, 12), 16, 1.5, boxstyle="round,pad=0.1", 
                              facecolor=user_color, edgecolor='black', linewidth=1.5)
    ax.add_patch(user_box)
    ax.text(9, 12.75, 'User Access', ha='center', va='center', fontweight='bold', fontsize=12)
    ax.text(5, 12.4, 'Farmers & Extension Officers', ha='center', va='center', fontsize=10)
    ax.text(9, 12.4, 'Mobile Devices', ha='center', va='center', fontsize=10)
    ax.text(13, 12.4, 'Web Browsers', ha='center', va='center', fontsize=10)
    
    # AWS Cloud boundary
    aws_box = FancyBboxPatch((0.5, 1), 17, 10.5, boxstyle="round,pad=0.2", 
                             facecolor='#fff9c4', edgecolor='#ff9800', linewidth=2)
    ax.add_patch(aws_box)
    ax.text(1, 11, 'AWS Cloud', ha='left', va='top', fontweight='bold', fontsize=14, color='#ff9800')
    
    # Edge & CDN
    edge_box = FancyBboxPatch((2, 9.5), 14, 1, boxstyle="round,pad=0.1", 
                              facecolor=edge_color, edgecolor='black', linewidth=1.5)
    ax.add_patch(edge_box)
    ax.text(9, 10, 'Edge & CDN Layer', ha='center', va='center', fontweight='bold', fontsize=12)
    ax.text(6, 9.7, 'CloudFront CDN', ha='center', va='center', fontsize=10)
    ax.text(12, 9.7, 'Route 53 DNS', ha='center', va='center', fontsize=10)
    
    # Application Load Balancer
    alb_box = FancyBboxPatch((2, 8.5), 14, 0.8, boxstyle="round,pad=0.1", 
                             facecolor=edge_color, edgecolor='black', linewidth=1.5)
    ax.add_patch(alb_box)
    ax.text(9, 8.9, 'Application Load Balancer + WAF', ha='center', va='center', fontweight='bold', fontsize=11)
    
    # Compute Layer
    compute_box = FancyBboxPatch((2, 6.5), 14, 1.5, boxstyle="round,pad=0.1", 
                                 facecolor=compute_color, edgecolor='black', linewidth=1.5)
    ax.add_patch(compute_box)
    ax.text(9, 7.7, 'Compute Layer', ha='center', va='center', fontweight='bold', fontsize=12)
    ax.text(5, 7.2, 'ECS Fargate Cluster', ha='center', va='center', fontweight='bold', fontsize=10)
    ax.text(5, 6.9, 'API Services 1-3', ha='center', va='center', fontsize=9)
    ax.text(13, 7.2, 'Lambda Functions', ha='center', va='center', fontweight='bold', fontsize=10)
    ax.text(13, 6.8, 'GPS • Translation • Audio\nVoice • Visual Verification', ha='center', va='center', fontsize=8)
    
    # AI/ML Services
    ai_box = FancyBboxPatch((2, 5), 14, 1, boxstyle="round,pad=0.1", 
                            facecolor=ai_color, edgecolor='black', linewidth=1.5)
    ax.add_patch(ai_box)
    ax.text(9, 5.5, 'AI/ML Services', ha='center', va='center', fontweight='bold', fontsize=12)
    ax.text(4, 5.2, 'Amazon Bedrock', ha='center', va='center', fontsize=9)
    ax.text(7, 5.2, 'Transcribe', ha='center', va='center', fontsize=9)
    ax.text(9.5, 5.2, 'Polly', ha='center', va='center', fontsize=9)
    ax.text(12, 5.2, 'Translate', ha='center', va='center', fontsize=9)
    ax.text(14.5, 5.2, 'Location Service', ha='center', va='center', fontsize=9)
    
    # Data Sources & Storage
    data_box = FancyBboxPatch((2, 3.5), 6, 1, boxstyle="round,pad=0.1", 
                              facecolor=data_color, edgecolor='black', linewidth=1.5)
    ax.add_patch(data_box)
    ax.text(5, 4, 'Data Sources & Storage', ha='center', va='center', fontweight='bold', fontsize=11)
    ax.text(3.5, 3.7, 'S3 Sentinel-2', ha='center', va='center', fontsize=9)
    ax.text(6.5, 3.7, 'ElastiCache Redis', ha='center', va='center', fontsize=9)
    
    # External APIs
    external_box = FancyBboxPatch((10, 3.5), 6, 1, boxstyle="round,pad=0.1", 
                                  facecolor=external_color, edgecolor='black', linewidth=1.5)
    ax.add_patch(external_box)
    ax.text(13, 4, 'External APIs', ha='center', va='center', fontweight='bold', fontsize=11)
    ax.text(11.5, 3.7, 'AlphaEarth API', ha='center', va='center', fontsize=9)
    ax.text(13, 3.7, 'Google Earth Engine', ha='center', va='center', fontsize=9)
    ax.text(14.5, 3.7, 'Weather APIs', ha='center', va='center', fontsize=9)
    
    # Monitoring & Security
    security_box = FancyBboxPatch((2, 2), 14, 1, boxstyle="round,pad=0.1", 
                                  facecolor=security_color, edgecolor='black', linewidth=1.5)
    ax.add_patch(security_box)
    ax.text(9, 2.5, 'Monitoring & Security', ha='center', va='center', fontweight='bold', fontsize=12)
    ax.text(4, 2.2, 'CloudWatch', ha='center', va='center', fontsize=9)
    ax.text(7, 2.2, 'IAM Roles', ha='center', va='center', fontsize=9)
    ax.text(10, 2.2, 'Secrets Manager', ha='center', va='center', fontsize=9)
    ax.text(13, 2.2, 'VPC & Security Groups', ha='center', va='center', fontsize=9)
    
    # Connection arrows
    # User to Edge
    ax.arrow(9, 12, 0, -1.4, head_width=0.3, head_length=0.1, fc='black', ec='black')
    # Edge to ALB
    ax.arrow(9, 9.5, 0, -0.6, head_width=0.3, head_length=0.1, fc='black', ec='black')
    # ALB to Compute
    ax.arrow(9, 8.5, 0, -0.4, head_width=0.3, head_length=0.1, fc='black', ec='black')
    # Compute to AI
    ax.arrow(9, 6.5, 0, -0.4, head_width=0.3, head_length=0.1, fc='blue', ec='blue')
    # Compute to Data
    ax.arrow(7, 6.5, -1, -1.8, head_width=0.3, head_length=0.1, fc='green', ec='green')
    # Compute to External
    ax.arrow(11, 6.5, 1, -1.8, head_width=0.3, head_length=0.1, fc='orange', ec='orange')
    
    ax.set_title('Precision AgriAI - AWS Deployment Architecture', fontsize=16, fontweight='bold', pad=20)
    
    plt.tight_layout()
    plt.savefig('aws_deployment_diagram.png', dpi=300, bbox_inches='tight', 
                facecolor='white', edgecolor='none')
    plt.close()

if __name__ == "__main__":
    print("Generating User Interaction Diagram...")
    create_user_interaction_diagram()
    print("✓ user_interaction_diagram.png created")
    
    print("Generating System Architecture Diagram...")
    create_system_architecture_diagram()
    print("✓ system_architecture_diagram.png created")
    
    print("Generating AWS Deployment Diagram...")
    create_aws_deployment_diagram()
    print("✓ aws_deployment_diagram.png created")
    
    print("\nAll diagrams generated successfully!")