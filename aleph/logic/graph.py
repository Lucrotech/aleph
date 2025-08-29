import logging

from followthemoney.graph import Graph as FtMGraph
from followthemoney.types import registry

from aleph.model import Entity
from aleph.util import get_entity_proxy

log = logging.getLogger(__name__)


class Graph(FtMGraph):
    """A subclass of `followthemoney.graph:Graph` that can resolve
    entities against the aleph search index and entity cache."""

    def resolve(self):
        from aleph.logic import resolver

        for id_ in self.queued:
            node_id = registry.entity.node_id_safe(id_)
            node = self.nodes.get(node_id)
            schema = None if node is None else node.schema
            resolver.queue(self, Entity, id_, schema=schema)
        resolver.resolve(self)
        for id_ in self.queued:
            entity = resolver.get(self, Entity, id_)
            if entity is not None:
                self.add(get_entity_proxy(entity))
