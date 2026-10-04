import asyncio
from datetime import datetime, timedelta, timezone
from itertools import islice
from statistics import fmean, median
from typing import Any, Iterable

import boto3

from app.models.integration import AWSConnection
from app.models.metric import MetricSnapshot, MetricTrend


def _chunks(values: list[str], size: int) -> Iterable[list[str]]:
    iterator = iter(values)
    while chunk := list(islice(iterator, size)):
        yield chunk


def _pages(client, operation: str, **kwargs):
    paginator = client.get_paginator(operation)
    yield from paginator.paginate(**kwargs)


class AWSIntegration:
    def __init__(
        self,
        role_arn: str | None = None,
        external_id: str | None = None,
        regions: tuple[str, ...] = (),
    ):
        self.role_arn = role_arn
        self.external_id = external_id
        self.regions = regions
        self.last_inventory: dict = {}

    @property
    def configured(self) -> bool:
        return bool(self.role_arn and self.external_id and self.regions)

    def _session(self, connection: AWSConnection | None = None):
        role_arn = connection.role_arn if connection else self.role_arn
        external_id = connection.external_id if connection else self.external_id
        response = boto3.client("sts").assume_role(
            RoleArn=role_arn,
            RoleSessionName="OpsPilotReadOnly",
            ExternalId=external_id,
            DurationSeconds=3600,
        )
        credentials = response["Credentials"]
        return boto3.Session(
            aws_access_key_id=credentials["AccessKeyId"],
            aws_secret_access_key=credentials["SecretAccessKey"],
            aws_session_token=credentials["SessionToken"],
        )

    async def test_and_configure(self, connection: AWSConnection) -> dict:
        identity = await asyncio.to_thread(self._test, connection)
        self.role_arn = connection.role_arn
        self.external_id = connection.external_id
        self.regions = tuple(dict.fromkeys(connection.regions))
        return identity

    def _test(self, connection: AWSConnection) -> dict:
        session = self._session(connection)
        identity = session.client("sts").get_caller_identity()
        session.client("ec2", region_name=connection.regions[0]).describe_regions(
            RegionNames=connection.regions
        )
        return {"account_id": identity["Account"], "arn": identity["Arn"]}

    async def inventory(self) -> dict:
        if not self.configured:
            return {}
        self.last_inventory = await asyncio.to_thread(self._inventory)
        return self.last_inventory

    def _inventory(self) -> dict[str, Any]:
        session = self._session()
        identity = session.client("sts").get_caller_identity()
        inventory: dict[str, Any] = {
            "account_id": identity["Account"],
            "regions": list(self.regions),
            "ec2_instances": [],
            "ecs_services": [],
            "ecs_tasks": [],
            "load_balancers": [],
            "target_groups": [],
            "rds_instances": [],
            "collection_errors": [],
        }
        for region in self.regions:
            for name, collector in (
                ("ec2", self._collect_ec2),
                ("ecs", self._collect_ecs),
                ("load_balancers", self._collect_load_balancers),
                ("rds", self._collect_rds),
            ):
                try:
                    collector(session, region, inventory)
                except Exception as exc:
                    inventory["collection_errors"].append(
                        {"region": region, "service": name, "error": str(exc)}
                    )
        return inventory

    def _collect_ec2(self, session, region: str, inventory: dict) -> None:
        client = session.client("ec2", region_name=region)
        statuses = {}
        for page in _pages(client, "describe_instance_status", IncludeAllInstances=True):
            for item in page.get("InstanceStatuses", []):
                statuses[item["InstanceId"]] = {
                    "instance_status": item["InstanceStatus"]["Status"],
                    "system_status": item["SystemStatus"]["Status"],
                }
        for page in _pages(client, "describe_instances"):
            for reservation in page.get("Reservations", []):
                for instance in reservation.get("Instances", []):
                    name = next(
                        (tag["Value"] for tag in instance.get("Tags", []) if tag["Key"] == "Name"),
                        None,
                    )
                    inventory["ec2_instances"].append(
                        {
                            "region": region,
                            "id": instance["InstanceId"],
                            "name": name,
                            "type": instance.get("InstanceType"),
                            "state": instance["State"]["Name"],
                            "availability_zone": instance.get("Placement", {}).get("AvailabilityZone"),
                            **statuses.get(instance["InstanceId"], {}),
                        }
                    )

    def _collect_ecs(self, session, region: str, inventory: dict) -> None:
        client = session.client("ecs", region_name=region)
        clusters = [
            arn
            for page in _pages(client, "list_clusters")
            for arn in page.get("clusterArns", [])
        ]
        for cluster in clusters:
            service_arns = [
                arn
                for page in _pages(client, "list_services", cluster=cluster)
                for arn in page.get("serviceArns", [])
            ]
            for chunk in _chunks(service_arns, 10):
                response = client.describe_services(cluster=cluster, services=chunk)
                for service in response.get("services", []):
                    inventory["ecs_services"].append(
                        {
                            "region": region,
                            "cluster": cluster.rsplit("/", 1)[-1],
                            "service": service["serviceName"],
                            "status": service["status"],
                            "desired": service["desiredCount"],
                            "running": service["runningCount"],
                            "pending": service["pendingCount"],
                            "task_definition": service["taskDefinition"].rsplit("/", 1)[-1],
                        }
                    )
            task_arns = [
                arn
                for page in _pages(client, "list_tasks", cluster=cluster)
                for arn in page.get("taskArns", [])
            ]
            for chunk in _chunks(task_arns, 100):
                response = client.describe_tasks(cluster=cluster, tasks=chunk)
                for task in response.get("tasks", []):
                    inventory["ecs_tasks"].append(
                        {
                            "region": region,
                            "cluster": cluster.rsplit("/", 1)[-1],
                            "task": task["taskArn"].rsplit("/", 1)[-1],
                            "desired_status": task["desiredStatus"],
                            "last_status": task["lastStatus"],
                            "health_status": task.get("healthStatus", "UNKNOWN"),
                            "stopped_reason": task.get("stoppedReason"),
                        }
                    )

    def _collect_load_balancers(self, session, region: str, inventory: dict) -> None:
        client = session.client("elbv2", region_name=region)
        for page in _pages(client, "describe_load_balancers"):
            for load_balancer in page.get("LoadBalancers", []):
                inventory["load_balancers"].append(
                    {
                        "region": region,
                        "name": load_balancer["LoadBalancerName"],
                        "type": load_balancer["Type"],
                        "state": load_balancer["State"]["Code"],
                        "dns_name": load_balancer["DNSName"],
                        "dimension": load_balancer["LoadBalancerArn"].split("loadbalancer/", 1)[-1],
                    }
                )
        for page in _pages(client, "describe_target_groups"):
            for target_group in page.get("TargetGroups", []):
                health = client.describe_target_health(
                    TargetGroupArn=target_group["TargetGroupArn"]
                )
                inventory["target_groups"].append(
                    {
                        "region": region,
                        "name": target_group["TargetGroupName"],
                        "targets": [
                            {
                                "id": target["Target"]["Id"],
                                "port": target["Target"].get("Port"),
                                "state": target["TargetHealth"]["State"],
                                "reason": target["TargetHealth"].get("Reason"),
                            }
                            for target in health.get("TargetHealthDescriptions", [])
                        ],
                    }
                )

    def _collect_rds(self, session, region: str, inventory: dict) -> None:
        client = session.client("rds", region_name=region)
        for page in _pages(client, "describe_db_instances"):
            for database in page.get("DBInstances", []):
                inventory["rds_instances"].append(
                    {
                        "region": region,
                        "id": database["DBInstanceIdentifier"],
                        "status": database["DBInstanceStatus"],
                        "engine": database["Engine"],
                        "class": database["DBInstanceClass"],
                    }
                )

    async def metric_snapshots(self) -> list[MetricSnapshot]:
        if not self.configured:
            return []
        inventory = await self.inventory()
        return await asyncio.to_thread(self._metric_snapshots, inventory)

    @staticmethod
    def context_for(metrics: MetricSnapshot, inventory: dict) -> dict:
        resource_id = metrics.resource_id
        if metrics.resource_type == "ec2":
            resources = [item for item in inventory.get("ec2_instances", []) if item["id"] == resource_id]
            return {"ec2_instance": resources[0]} if resources else {}
        if metrics.resource_type == "ecs":
            services = [item for item in inventory.get("ecs_services", []) if item["service"] == resource_id]
            if not services:
                return {}
            service = services[0]
            tasks = [
                item for item in inventory.get("ecs_tasks", [])
                if item["cluster"] == service["cluster"]
            ]
            return {"ecs_service": service, "ecs_tasks": tasks}
        if metrics.resource_type == "alb":
            resources = [item for item in inventory.get("load_balancers", []) if item["name"] == resource_id]
            if not resources:
                return {}
            load_balancer = resources[0]
            target_groups = [
                item for item in inventory.get("target_groups", [])
                if item["region"] == load_balancer["region"]
            ]
            return {"load_balancer": load_balancer, "target_groups": target_groups}
        if metrics.resource_type == "rds":
            resources = [item for item in inventory.get("rds_instances", []) if item["id"] == resource_id]
            return {"rds_instance": resources[0]} if resources else {}
        return {}

    @staticmethod
    def _metric_history(
        client, namespace: str, name: str, dimensions: list[dict], statistic="Average"
    ) -> list[tuple[datetime, float]]:
        end = datetime.now(timezone.utc)
        request = {
            "Namespace": namespace,
            "MetricName": name,
            "Dimensions": dimensions,
            "StartTime": end - timedelta(minutes=60),
            "EndTime": end,
            "Period": 300,
        }
        if statistic.startswith("p"):
            request["ExtendedStatistics"] = [statistic]
        else:
            request["Statistics"] = [statistic]
        points = client.get_metric_statistics(**request).get("Datapoints", [])
        return sorted(
            (
                point["Timestamp"],
                float(point.get(statistic, point.get("ExtendedStatistics", {}).get(statistic))),
            )
            for point in points
        )

    @classmethod
    def _metric(cls, client, namespace: str, name: str, dimensions: list[dict], statistic="Average"):
        history = cls._metric_history(client, namespace, name, dimensions, statistic)
        return history[-1][1] if history else None

    @staticmethod
    def _scale(
        history: list[tuple[datetime, float]], multiplier: float
    ) -> list[tuple[datetime, float]]:
        return [(timestamp, value * multiplier) for timestamp, value in history]

    @staticmethod
    def _maximum(*histories: list[tuple[datetime, float]]) -> list[tuple[datetime, float]]:
        combined: dict[datetime, list[float]] = {}
        for history in histories:
            for timestamp, value in history:
                combined.setdefault(timestamp, []).append(value)
        return sorted((timestamp, max(values)) for timestamp, values in combined.items())

    @staticmethod
    def _error_rates(
        requests: list[tuple[datetime, float]], errors: list[tuple[datetime, float]]
    ) -> list[tuple[datetime, float]]:
        errors_by_time = dict(errors)
        return [
            (timestamp, 100 * errors_by_time.get(timestamp, 0) / request_count)
            for timestamp, request_count in requests
            if request_count > 0
        ]

    @staticmethod
    def _trend(history: list[tuple[datetime, float]]) -> MetricTrend | None:
        if not history:
            return None
        values = [value for _, value in history]
        baseline = float(median(values))
        latest = values[-1]
        if len(history) > 1:
            gaps = [
                (right[0] - left[0]).total_seconds() / 60
                for left, right in zip(history, history[1:])
            ]
            interval = float(median(gaps))
            elapsed = (history[-1][0] - history[0][0]).total_seconds() / 60
        else:
            interval = elapsed = 0.0
        direction = "stable" if latest == baseline else "above" if latest > baseline else "below"
        sustained = 0
        if direction != "stable":
            for value in reversed(values):
                if (direction == "above" and value <= baseline) or (
                    direction == "below" and value >= baseline
                ):
                    break
                sustained += 1
        deviation = latest - baseline
        return MetricTrend(
            baseline=baseline,
            average=float(fmean(values)),
            peak=max(values),
            rate_of_change_per_minute=(latest - values[0]) / elapsed if elapsed else 0,
            deviation_from_baseline=deviation,
            deviation_percent=100 * deviation / baseline if baseline else None,
            sustained_direction=direction,
            sustained_duration_minutes=sustained * interval,
            sample_count=len(values),
            window_minutes=elapsed + interval,
        )

    @classmethod
    def _trends(cls, histories: dict[str, list[tuple[datetime, float]]]) -> dict[str, MetricTrend]:
        return {
            name: trend
            for name, history in histories.items()
            if (trend := cls._trend(history)) is not None
        }

    def _metric_snapshots(self, inventory: dict) -> list[MetricSnapshot]:
        session = self._session()
        clients = {
            region: session.client("cloudwatch", region_name=region)
            for region in self.regions
        }
        snapshots = []
        for instance in inventory["ec2_instances"]:
            dimensions = [{"Name": "InstanceId", "Value": instance["id"]}]
            client = clients[instance["region"]]
            histories = {
                "cpu_percent": self._metric_history(client, "AWS/EC2", "CPUUtilization", dimensions),
                "network_in_bytes": self._metric_history(client, "AWS/EC2", "NetworkIn", dimensions, "Sum"),
                "network_out_bytes": self._metric_history(client, "AWS/EC2", "NetworkOut", dimensions, "Sum"),
            }
            trends = self._trends(histories)
            snapshots.append(MetricSnapshot(
                service=f"ec2:{instance['id']}", resource_type="ec2", resource_id=instance["id"],
                cpu_percent=histories["cpu_percent"][-1][1] if histories["cpu_percent"] else None,
                baseline_cpu_percent=trends.get("cpu_percent").baseline if "cpu_percent" in trends else None,
                extra_metrics={
                    key: history[-1][1] for key, history in histories.items()
                    if key != "cpu_percent" and history
                },
                trends=trends,
            ))
        for service in inventory["ecs_services"]:
            dimensions = [
                {"Name": "ClusterName", "Value": service["cluster"]},
                {"Name": "ServiceName", "Value": service["service"]},
            ]
            client = clients[service["region"]]
            histories = {
                "cpu_percent": self._metric_history(client, "AWS/ECS", "CPUUtilization", dimensions),
                "memory_percent": self._metric_history(client, "AWS/ECS", "MemoryUtilization", dimensions),
            }
            trends = self._trends(histories)
            snapshots.append(MetricSnapshot(
                service=f"ecs:{service['cluster']}/{service['service']}", resource_type="ecs",
                resource_id=service["service"],
                cpu_percent=histories["cpu_percent"][-1][1] if histories["cpu_percent"] else None,
                memory_percent=histories["memory_percent"][-1][1] if histories["memory_percent"] else None,
                baseline_cpu_percent=trends.get("cpu_percent").baseline if "cpu_percent" in trends else None,
                baseline_memory_percent=trends.get("memory_percent").baseline if "memory_percent" in trends else None,
                extra_metrics={
                    "desired_tasks": float(service["desired"]),
                    "running_tasks": float(service["running"]),
                    "pending_tasks": float(service["pending"]),
                },
                trends=trends,
            ))
        for load_balancer in inventory["load_balancers"]:
            dimensions = [{"Name": "LoadBalancer", "Value": load_balancer["dimension"]}]
            client = clients[load_balancer["region"]]
            request_counts = self._metric_history(client, "AWS/ApplicationELB", "RequestCount", dimensions, "Sum")
            error_counts = self._metric_history(client, "AWS/ApplicationELB", "HTTPCode_Target_5XX_Count", dimensions, "Sum")
            histories = {
                "request_rate": self._scale(request_counts, 1 / 300),
                "error_rate_percent": self._error_rates(request_counts, error_counts),
                "latency_ms": self._scale(
                    self._metric_history(client, "AWS/ApplicationELB", "TargetResponseTime", dimensions, "p95"),
                    1000,
                ),
            }
            trends = self._trends(histories)
            snapshots.append(MetricSnapshot(
                service=f"alb:{load_balancer['name']}", resource_type="alb",
                resource_id=load_balancer["name"],
                latency_ms=histories["latency_ms"][-1][1] if histories["latency_ms"] else None,
                error_rate_percent=histories["error_rate_percent"][-1][1] if histories["error_rate_percent"] else None,
                request_rate=histories["request_rate"][-1][1] if histories["request_rate"] else None,
                baseline_latency_ms=trends.get("latency_ms").baseline if "latency_ms" in trends else None,
                baseline_error_rate_percent=trends.get("error_rate_percent").baseline if "error_rate_percent" in trends else None,
                baseline_request_rate=trends.get("request_rate").baseline if "request_rate" in trends else None,
                trends=trends,
            ))
        for database in inventory["rds_instances"]:
            dimensions = [{"Name": "DBInstanceIdentifier", "Value": database["id"]}]
            client = clients[database["region"]]
            histories = {
                "cpu_percent": self._metric_history(client, "AWS/RDS", "CPUUtilization", dimensions),
                "latency_ms": self._scale(self._maximum(
                    self._metric_history(client, "AWS/RDS", "ReadLatency", dimensions),
                    self._metric_history(client, "AWS/RDS", "WriteLatency", dimensions),
                ), 1000),
                "database_connections": self._metric_history(client, "AWS/RDS", "DatabaseConnections", dimensions),
                "freeable_memory_bytes": self._metric_history(client, "AWS/RDS", "FreeableMemory", dimensions),
            }
            trends = self._trends(histories)
            snapshots.append(MetricSnapshot(
                service=f"rds:{database['id']}", resource_type="rds", resource_id=database["id"],
                cpu_percent=histories["cpu_percent"][-1][1] if histories["cpu_percent"] else None,
                latency_ms=histories["latency_ms"][-1][1] if histories["latency_ms"] else None,
                baseline_cpu_percent=trends.get("cpu_percent").baseline if "cpu_percent" in trends else None,
                baseline_latency_ms=trends.get("latency_ms").baseline if "latency_ms" in trends else None,
                extra_metrics={
                    key: history[-1][1] for key, history in histories.items()
                    if key in {"database_connections", "freeable_memory_bytes"} and history
                },
                trends=trends,
            ))
        return snapshots
