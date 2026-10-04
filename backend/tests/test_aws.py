import unittest
from datetime import datetime, timezone

from app.integrations.aws.client import AWSIntegration


class FakePaginator:
    def __init__(self, pages):
        self.pages = pages

    def paginate(self, **kwargs):
        return self.pages


class FakeEC2:
    def get_paginator(self, operation):
        if operation == "describe_instance_status":
            return FakePaginator([{"InstanceStatuses": [{
                "InstanceId": "i-123",
                "InstanceStatus": {"Status": "ok"},
                "SystemStatus": {"Status": "ok"},
            }]}])
        return FakePaginator([{"Reservations": [{"Instances": [{
            "InstanceId": "i-123",
            "InstanceType": "t3.small",
            "State": {"Name": "running"},
            "Placement": {"AvailabilityZone": "us-east-1a"},
            "Tags": [{"Key": "Name", "Value": "payments"}],
        }]}]}])


class FakeSession:
    def client(self, service, region_name=None):
        self.region = region_name
        return FakeEC2()


class AWSInventoryTest(unittest.TestCase):
    def test_collects_ec2_health_without_secrets(self):
        inventory = {"ec2_instances": []}
        AWSIntegration()._collect_ec2(FakeSession(), "us-east-1", inventory)
        instance = inventory["ec2_instances"][0]
        self.assertEqual(instance["id"], "i-123")
        self.assertEqual(instance["instance_status"], "ok")
        self.assertNotIn("Tags", instance)

    def test_reads_latest_cloudwatch_metric(self):
        class CloudWatch:
            def get_metric_statistics(self, **kwargs):
                self.request = kwargs
                return {"Datapoints": [
                    {"Timestamp": datetime(2026, 1, 1, tzinfo=timezone.utc), "Average": 42.0},
                    {"Timestamp": datetime(2026, 1, 2, tzinfo=timezone.utc), "Average": 91.5},
                ]}

        cloudwatch = CloudWatch()
        value = AWSIntegration._metric(
            cloudwatch, "AWS/EC2", "CPUUtilization",
            [{"Name": "InstanceId", "Value": "i-123"}],
        )
        self.assertEqual(value, 91.5)
        self.assertEqual(cloudwatch.request["Period"], 300)
        self.assertAlmostEqual(
            (cloudwatch.request["EndTime"] - cloudwatch.request["StartTime"]).total_seconds(),
            3600,
        )

    def test_calculates_history_trend(self):
        points = [
            (datetime(2026, 1, 1, 0, minute, tzinfo=timezone.utc), value)
            for minute, value in ((0, 10), (5, 20), (10, 30), (15, 40))
        ]
        trend = AWSIntegration._trend(points)
        self.assertEqual(trend.baseline, 25)
        self.assertEqual(trend.average, 25)
        self.assertEqual(trend.peak, 40)
        self.assertEqual(trend.rate_of_change_per_minute, 2)
        self.assertEqual(trend.deviation_from_baseline, 15)
        self.assertEqual(trend.sustained_duration_minutes, 10)
        self.assertEqual(trend.window_minutes, 20)


if __name__ == "__main__":
    unittest.main()
