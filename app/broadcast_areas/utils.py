from collections import defaultdict

from app.broadcast_areas.models import CustomBroadcastArea


def aggregate_areas(areas):
    areas = _convert_custom_areas_to_wards(areas)
    areas = _aggregate_wards_by_local_authority(areas)
    areas = _aggregate_lower_tier_authorities(areas)
    return areas


def _convert_custom_areas_to_wards(areas):
    results = set()

    for area in areas:
        if type(area) == CustomBroadcastArea:
            results |= set(area.overlapping_electoral_wards)
        else:
            results |= {area}

    return results


def _aggregate_wards_by_local_authority(areas):
    return {
        area.parent if area.id.startswith('wd20-')
        else area for area in areas
    }


def _aggregate_lower_tier_authorities(areas):
    results = set()
    clusters = _cluster_lower_tier_authorities(areas)

    for cluster in clusters:
        # always keep lone area as itself
        if len(cluster) == 1:
            results |= set(cluster)
        # aggregate multi-area cluster
        elif len(cluster) > 3:
            results |= {cluster[0].parent}
        # aggregate many small clusters
        elif len(clusters) > 1:
            area = cluster[0]
            results |= {area.parent or area}
        # keep one small cluster in full
        else:
            results |= set(cluster)

    return results


def _cluster_lower_tier_authorities(areas):
    result = defaultdict(lambda: [])

    for area in areas:
        # group lower tier authorities by "county"
        if area.id.startswith('lad20-') and area.parent:
            result[area.parent] += [area]
        # leave countries, unitary authorities as-is
        else:
            result[area] = [area]

    return result.values()
