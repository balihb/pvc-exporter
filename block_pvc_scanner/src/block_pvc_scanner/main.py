import logging
import os
import re
import time
from collections.abc import Callable

import psutil
from prometheus_client import start_http_server, Gauge
from psutil._common import sdiskusage

formatter = logging.Formatter(os.getenv('APP_LOG_FORMAT', '%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
logger = logging.getLogger(__name__)
logger.setLevel(os.getenv('APP_LOG_LEVEL', logging.INFO))
print_log = logging.StreamHandler()
print_log.setFormatter(formatter)
logger.addHandler(print_log)

psutil.PROCFS_PATH = '/host/proc'

percent_gauge = Gauge('pvc_usage', "fetching pvc usage matched by k8s csi", ['volumename'])

total_bytes_gauge = Gauge('pvc_usage_total_bytes', "PVC total bytes", ['volumename'])

used_bytes_gauge = Gauge('pvc_usage_used_bytes', "PVC used bytes", ['volumename'])

free_bytes_gauge = Gauge('pvc_usage_free_bytes', "PVC free bytes", ['volumename'])

supported_pvc_re = re.compile(
    '^.+(kubernetes.io/flexvolume|/kubernetes.io/csi/pv/pvc-|kubernetes.io/gce-pd/mounts).*$'  # noqa: E501
)
pvc_re = re.compile('^pvc-[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$')  # noqa: E501
gke_data_re = re.compile('^gke-data')


def filter_supported_pvcs(mount_point: str) -> bool:
    if supported_pvc_re.match(mount_point):
        return True
    return False


def get_relevant_mount_points(partitions: set[str]) -> set[str]:
    return set(filter(filter_supported_pvcs, partitions))


def mount_point_to_pvc(mount_point: str) -> str:
    mount_point_parts = mount_point.split('/')
    pvc = mount_point_parts[-1]
    if not pvc_re.match(pvc):
        for possible_pvc in mount_point_parts:
            if pvc_re.match(possible_pvc):
                pvc = possible_pvc
            elif gke_data_re.match(possible_pvc):
                pvc = 'pvc' + possible_pvc.split('pvc')[-1]
    return pvc


def mount_point_to_disk_usage(mount_point: str) -> sdiskusage:  # pragma: no cover
    return psutil.disk_usage(mount_point)


def get_all_partitions() -> set[str]:  # pragma: no cover
    psutil.PROCFS_PATH = '/host/proc'
    parts = psutil.disk_partitions(all=False)
    logger.debug(f'num of partitions: {len(parts)}')
    for part in parts:
        logger.debug(part.mountpoint)
    return set(map(lambda p: p.mountpoint, parts))


def get_all_partitions_proc_mounts() -> set[str]:  # pragma: no cover
    mounts_file = open('/host/proc/1/mounts')
    return set(map(lambda l: l.split(' ')[1], mounts_file.readlines()))


def update_stats(pvcs_disk_usage: dict[str, sdiskusage]):
    for pvc in pvcs_disk_usage.keys():
        disk_usage = pvcs_disk_usage[pvc]
        logger.info(f'PVC: {pvc}, USAGE: {disk_usage.percent}')

        percent_gauge.labels(pvc).set(disk_usage.percent)
        total_bytes_gauge.labels(pvc).set(disk_usage.total)
        used_bytes_gauge.labels(pvc).set(disk_usage.used)
        free_bytes_gauge.labels(pvc).set(disk_usage.free)


def clean_removed_pvcs(old_pvcs: set[str], pvcs: set[str]):
    for pvc in old_pvcs - pvcs:
        percent_gauge.remove(pvc)
        total_bytes_gauge.remove(pvc)
        used_bytes_gauge.remove(pvc)
        free_bytes_gauge.remove(pvc)


def process_mount_points(
    mount_points: set[str],
    get_usage: Callable[[str], sdiskusage] = mount_point_to_disk_usage
) -> dict[str, sdiskusage]:
    return {mount_point_to_pvc(mount_point): get_usage(mount_point) for mount_point in mount_points}


def main_loop(
    old_pvcs: set[str],
    get_partitions: Callable[[], set[str]] = get_all_partitions_proc_mounts,
    get_usage: Callable[[str], sdiskusage] = mount_point_to_disk_usage,
):
    partitions: set[str] = get_partitions()
    mount_points: set[str] = get_relevant_mount_points(partitions)
    pvcs: set[str] = set[str]()
    if len(mount_points) == 0:
        logger.info("No mounted PVC found.")
    else:
        pvcs_disk_usage: dict[str, sdiskusage] = \
            process_mount_points(
                mount_points=mount_points,
                get_usage=get_usage
            )
        update_stats(pvcs_disk_usage)
        pvcs: set[str] = set[str](pvcs_disk_usage.keys())
    clean_removed_pvcs(old_pvcs, pvcs)
    return pvcs


def main(
    argv: list[str] = None,
    get_partitions: Callable[[], set[str]] = get_all_partitions_proc_mounts,
    get_usage: Callable[[str], sdiskusage] = mount_point_to_disk_usage
):  # pragma: no cover
    start_http_server(os.getenv('APP_HTTP_SERVER_PORT', 8848))

    old_pvcs = set[str]()

    while 1:
        old_pvcs = main_loop(
            old_pvcs=old_pvcs,
            get_partitions=get_partitions,
            get_usage=get_usage
        )

        time.sleep(15)
