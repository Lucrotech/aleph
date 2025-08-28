from banal import ensure_list
from followthemoney import model
from followthemoney.exc import InvalidData
from followthemoney.helpers import remove_checksums
from followthemoney.types import registry

from aleph.logic.aggregator import get_aggregator


def bulk_write(
    collection, entities, safe=False, role_id=None, mutable=True, clean=True
):
    """Write a set of entities - given as dicts - to the index."""
    # This is called mainly by the /api/2/collections/X/_bulk API.
    aggregator = get_aggregator(collection)
    writer = aggregator.bulk()
    for data in entities:
        entity = model.get_proxy(data, cleaned=(not clean))
        if entity.id is None:
            raise InvalidData("No ID for entity", errors=entity.to_dict())
        entity = collection.ns.apply(entity)
        if safe:
            entity = remove_checksums(entity)
        entity.context = {"role_id": role_id, "mutable": mutable}
        for field, func in (("created_at", min), ("updated_at", max)):
            ts = func(ensure_list(data.get(field)), default=None)
            dt = registry.date.to_datetime(ts)
            if dt is not None:
                entity.context[field] = dt.isoformat()
        writer.put(entity, origin="bulk")
        yield entity
    writer.flush()
