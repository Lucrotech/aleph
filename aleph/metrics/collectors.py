from typing import Any

from followthemoney import __version__ as ftm_version
from prometheus_client.core import GaugeMetricFamily, InfoMetricFamily
from prometheus_client.registry import Collector
from sqlalchemy import func

from aleph import __version__ as aleph_version
from aleph.core import create_app as create_flask_app
from aleph.model import Bookmark, Collection, EntitySet, Role
from aleph.procrastinate.status import get_active_collections_status


class InfoCollector(Collector):
    def collect(self):
        yield InfoMetricFamily(
            "aleph_system",
            "Aleph system information",
            value={
                "aleph_version": aleph_version,
                "ftm_version": ftm_version,
            },
        )


class DatabaseCollector(Collector):
    def __init__(self):
        self._flask_app = create_flask_app()

    def collect(self):
        with self._flask_app.app_context():
            yield self._users()
            yield self._collections()
            yield self._collection_users()
            yield self._entitysets()
            yield self._entityset_users()
            yield self._bookmarks()
            yield self._bookmark_users()

    def _users(self):
        return GaugeMetricFamily(
            "aleph_users",
            "Total number of users",
            value=Role.all_users().count(),
        )

    def _collections(self):
        gauge = GaugeMetricFamily(
            "aleph_collections",
            "Total number of collections by category",
            labels=["category"],
        )

        query = (
            Collection.all()
            .with_entities(Collection.category, func.count())
            .group_by(Collection.category)
        )

        for category, count in query:
            gauge.add_metric([category], count)

        return gauge

    def _collection_users(self):
        gauge = GaugeMetricFamily(
            "aleph_collection_users",
            "Total number of users that have created at least one collection",
            labels=["category"],
        )

        query = (
            Collection.all()
            .with_entities(
                Collection.category,
                func.count(func.distinct(Collection.creator_id)),
            )
            .group_by(Collection.category)
        )

        for category, count in query:
            gauge.add_metric([category], count)

        return gauge

    def _entitysets(self):
        gauge = GaugeMetricFamily(
            "aleph_entitysets",
            "Total number of entity set by type",
            labels=["type"],
        )

        query = (
            EntitySet.all()
            .with_entities(EntitySet.type, func.count())
            .group_by(EntitySet.type)
        )

        for entityset_type, count in query:
            gauge.add_metric([entityset_type], count)

        return gauge

    def _entityset_users(self):
        gauge = GaugeMetricFamily(
            "aleph_entityset_users",
            "Number of users that have created at least on entity set of the given type",
            labels=["type"],
        )

        query = (
            EntitySet.all()
            .with_entities(
                EntitySet.type,
                func.count(func.distinct(EntitySet.role_id)),
            )
            .group_by(EntitySet.type)
        )

        for entityset_type, count in query:
            gauge.add_metric([entityset_type], count)

        return gauge

    def _bookmarks(self):
        return GaugeMetricFamily(
            "aleph_bookmarks",
            "Total number of bookmarks",
            value=Bookmark.query.count(),
        )

    def _bookmark_users(self):
        return GaugeMetricFamily(
            "aleph_bookmark_users",
            "Number of users that have created at least one bookmark",
            value=Bookmark.query.distinct(Bookmark.role_id).count(),
        )


class QueuesCollector(Collector):
    def collect(self):
        status: dict[str, Any] = {
            "datasets": {
                s["dataset"]: s
                for s in get_active_collections_status(include_collection_data=False)
            }
        }
        status["total"] = len(status["datasets"])

        yield GaugeMetricFamily(
            "aleph_active_datasets",
            "Total number of active datasets",
            value=status["total"],
        )

        stages = {}

        for collection_status in status["datasets"].values():
            for job_status in collection_status["jobs"]:
                for stage_status in job_status["stages"]:
                    stage = stage_status["stage"]
                    pending = stage_status["pending"]
                    running = stage_status["running"]

                    if stage not in stages:
                        stages[stage] = {
                            "pending": 0,
                            "running": 0,
                        }

                    stages[stage] = {
                        "pending": stages[stage].get("pending") + pending,
                        "running": stages[stage].get("running") + running,
                    }

        tasks_gauge = GaugeMetricFamily(
            "aleph_tasks",
            "Total number of pending or running tasks in a given stage",
            labels=["stage", "status"],
        )

        for stage, tasks in stages.items():
            tasks_gauge.add_metric([stage, "pending"], tasks["pending"])
            tasks_gauge.add_metric([stage, "running"], tasks["running"])

        yield tasks_gauge
