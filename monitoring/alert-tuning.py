#!/usr/bin/env python3
"""
Alert Tuning Script for Pulser MCP
Implements intelligent alert thresholds based on historical data
"""

import yaml
import json
import statistics
from datetime import datetime, timedelta
from typing import Dict, List, Tuple

class AlertTuner:
    def __init__(self, config_path: str = 'sla-config.yaml'):
        with open(config_path, 'r') as f:
            self.config = yaml.safe_load(f)
        self.metrics_history = []
        
    def calculate_dynamic_thresholds(self, 
                                   metric_name: str, 
                                   data: List[float], 
                                   sensitivity: float = 2.0) -> Tuple[float, float]:
        """
        Calculate dynamic thresholds using statistical methods
        Returns (warning_threshold, critical_threshold)
        """
        if not data:
            return (0, 0)
        
        # Remove outliers using IQR method
        sorted_data = sorted(data)
        q1 = sorted_data[len(sorted_data) // 4]
        q3 = sorted_data[3 * len(sorted_data) // 4]
        iqr = q3 - q1
        
        filtered_data = [
            x for x in data 
            if q1 - 1.5 * iqr <= x <= q3 + 1.5 * iqr
        ]
        
        # Calculate baseline
        mean = statistics.mean(filtered_data)
        stdev = statistics.stdev(filtered_data) if len(filtered_data) > 1 else 0
        
        # Set thresholds
        warning_threshold = mean + (sensitivity * stdev)
        critical_threshold = mean + (sensitivity * 2 * stdev)
        
        return (warning_threshold, critical_threshold)
    
    def analyze_alert_noise(self, alert_history: List[Dict]) -> Dict:
        """
        Analyze alert patterns to reduce noise
        """
        analysis = {
            'total_alerts': len(alert_history),
            'false_positives': 0,
            'alert_storms': 0,
            'recommendations': []
        }
        
        # Group alerts by time window
        time_windows = {}
        for alert in alert_history:
            window = alert['timestamp'] // 3600  # Hour buckets
            if window not in time_windows:
                time_windows[window] = []
            time_windows[window].append(alert)
        
        # Detect alert storms
        for window, alerts in time_windows.items():
            if len(alerts) > 10:
                analysis['alert_storms'] += 1
                analysis['recommendations'].append(
                    f"Alert storm detected at {datetime.fromtimestamp(window * 3600)}: "
                    f"{len(alerts)} alerts in 1 hour"
                )
        
        # Detect false positives (alerts that auto-resolved quickly)
        for alert in alert_history:
            if alert.get('duration_seconds', 0) < 120:  # Less than 2 minutes
                analysis['false_positives'] += 1
        
        if analysis['false_positives'] > len(alert_history) * 0.3:
            analysis['recommendations'].append(
                "High false positive rate (>30%). Consider increasing alert duration or thresholds."
            )
        
        return analysis
    
    def generate_tuned_config(self, metrics_data: Dict[str, List[float]]) -> Dict:
        """
        Generate optimized alert configuration based on actual metrics
        """
        tuned_config = self.config.copy()
        
        for service, sla in tuned_config['services'].items():
            # Tune latency thresholds
            if f"{service}_latency_p95" in metrics_data:
                p95_data = metrics_data[f"{service}_latency_p95"]
                warn, crit = self.calculate_dynamic_thresholds("latency_p95", p95_data)
                
                # Only increase thresholds, never decrease below SLA
                sla['latency_p95_ms'] = max(sla['latency_p95_ms'], int(warn))
                
                print(f"{service} P95 latency: SLA={sla['latency_p95_ms']}ms, "
                      f"Recommended={int(warn)}ms")
            
            # Tune error rate thresholds
            if f"{service}_error_rate" in metrics_data:
                error_data = metrics_data[f"{service}_error_rate"]
                warn, crit = self.calculate_dynamic_thresholds("error_rate", error_data, sensitivity=3.0)
                
                # Ensure we don't exceed error budget
                max_allowed = self.config['sla']['error_budget_percent'] / 100
                sla['error_rate_threshold'] = min(max_allowed, max(sla['error_rate_threshold'], warn))
                
                print(f"{service} error rate: SLA={sla['error_rate_threshold']:.3%}, "
                      f"Recommended={warn:.3%}")
        
        return tuned_config
    
    def export_prometheus_rules(self, output_path: str = 'alerts.rules.yml'):
        """
        Export tuned configuration as Prometheus alert rules
        """
        rules = {
            'groups': [{
                'name': 'pulser_mcp_alerts',
                'interval': '30s',
                'rules': []
            }]
        }
        
        # Generate rules for each service
        for service, sla in self.config['services'].items():
            # Availability alert
            rules['groups'][0]['rules'].append({
                'alert': f'{service}_down',
                'expr': f'up{{job="{service}"}} == 0',
                'for': '1m',
                'labels': {
                    'severity': 'critical',
                    'service': service
                },
                'annotations': {
                    'summary': f'{service} is down',
                    'description': f'{service} has been down for more than 1 minute'
                }
            })
            
            # Latency alert
            rules['groups'][0]['rules'].append({
                'alert': f'{service}_high_latency',
                'expr': f'histogram_quantile(0.95, {service}_request_duration_seconds) > {sla["latency_p95_ms"] / 1000}',
                'for': '5m',
                'labels': {
                    'severity': 'warning',
                    'service': service
                },
                'annotations': {
                    'summary': f'{service} latency is high',
                    'description': f'P95 latency is {{{{ $value }}}}s (threshold: {sla["latency_p95_ms"]}ms)'
                }
            })
            
            # Error rate alert
            rules['groups'][0]['rules'].append({
                'alert': f'{service}_high_error_rate',
                'expr': f'rate({service}_errors_total[5m]) / rate({service}_requests_total[5m]) > {sla["error_rate_threshold"]}',
                'for': '2m',
                'labels': {
                    'severity': 'warning',
                    'service': service
                },
                'annotations': {
                    'summary': f'{service} error rate is high',
                    'description': f'Error rate is {{{{ $value | humanizePercentage }}}} (threshold: {sla["error_rate_threshold"]:.1%})'
                }
            })
        
        # Save rules
        with open(output_path, 'w') as f:
            yaml.dump(rules, f, default_flow_style=False)
        
        print(f"Prometheus rules exported to {output_path}")
        return rules

def main():
    # Example usage
    tuner = AlertTuner()
    
    # Simulate loading historical metrics
    sample_metrics = {
        'scout_local_latency_p95': [150, 180, 160, 200, 170, 190, 165, 175, 185, 195],
        'scout_local_error_rate': [0.0005, 0.0008, 0.0003, 0.0012, 0.0006, 0.0009, 0.0004, 0.0007, 0.0010, 0.0005],
        'creative_rag_latency_p95': [800, 900, 850, 1100, 950, 1000, 920, 980, 1050, 890],
        'creative_rag_error_rate': [0.002, 0.003, 0.0025, 0.004, 0.0035, 0.003, 0.0028, 0.0032, 0.0038, 0.0029]
    }
    
    # Generate tuned configuration
    print("=== Alert Threshold Tuning ===\n")
    tuned_config = tuner.generate_tuned_config(sample_metrics)
    
    # Export Prometheus rules
    print("\n=== Exporting Prometheus Rules ===")
    tuner.export_prometheus_rules()
    
    # Analyze alert patterns
    print("\n=== Alert Noise Analysis ===")
    sample_alerts = [
        {'timestamp': 1704646800, 'duration_seconds': 60, 'severity': 'warning'},
        {'timestamp': 1704646900, 'duration_seconds': 300, 'severity': 'critical'},
        {'timestamp': 1704647000, 'duration_seconds': 45, 'severity': 'warning'},
    ]
    analysis = tuner.analyze_alert_noise(sample_alerts)
    print(json.dumps(analysis, indent=2))

if __name__ == '__main__':
    main()