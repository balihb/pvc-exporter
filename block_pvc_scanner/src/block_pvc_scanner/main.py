import logging
import os
import re
import time

import psutil
from prometheus_client import start_http_server, Gauge
from psutil._common import sdiskpart, sdiskusage

formatter = logging.Formatter(os.getenv(
    'APP_LOG_FORMAT',
    '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
))
logger = logging.getLogger(__name__)
logger.setLevel(os.getenv('APP_LOG_LEVEL', logging.INFO))
print_log = logging.StreamHandler()
print_log.setFormatter(formatter)
logger.addHandler(print_log)

percent_gauge = Gauge(
    'pvc_usage',
    "fetching pvc usage matched by k8s csi",
    ['volumename']
)

total_bytes_gauge = Gauge(
    'pvc_usage_total_bytes',
    "PVC total bytes",
    ['volumename']
)

used_bytes_gauge = Gauge(
    'pvc_usage_used_bytes',
    "PVC used bytes",
    ['volumename']
)

free_bytes_gauge = Gauge(
    'pvc_usage_free_bytes',
    "PVC free bytes",
    ['volumename']
)

supported_pvc_re = re.compile(
    '^.+(kubernetes.io/flexvolume|kubernetes.io~csi|kubernetes.io/gce-pd/mounts).*$'  # noqa: E501
)
pvc_re = re.compile('^pvc-[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$')  # noqa: E501
gke_data_re = re.compile('^gke-data')


def filter_supported_pvcs(partition: sdiskpart) -> bool:
    if supported_pvc_re.match(partition.mountpoint):
        return True
    return False


def get_relevant_mount_points(partitions: list[sdiskpart]) -> set[str]:
    return set(map(
        lambda p: p.mountpoint, filter(
            filter_supported_pvcs, partitions
        )))


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


def mount_point_to_disk_usage(
    mount_point: str
) -> sdiskusage:  # pragma: no cover
    return psutil.disk_usage(mount_point)


def update_stats(pvcs_disk_usage: dict[str, sdiskusage]):
    for pvc in pvcs_disk_usage.keys():
        disk_usage = pvcs_disk_usage[pvc]
        logger.info(f'PVC: {pvc}, USAGE: {disk_usage.percent}')

        percent_gauge.labels(pvc).set(disk_usage.percent)
        total_bytes_gauge.labels(pvc).set(disk_usage.total)
        used_bytes_gauge.labels(pvc).set(disk_usage.used)
        free_bytes_gauge.labels(pvc).set(disk_usage.free)


def clean_removed_pvcs(old_pvcs: set[str], pvcs: set[str]) -> set[str]:
    for pvc in old_pvcs - pvcs:
        percent_gauge.remove(pvc)
        total_bytes_gauge.remove(pvc)
        used_bytes_gauge.remove(pvc)
        free_bytes_gauge.remove(pvc)
    return pvcs


def process_mount_points(mount_points: set[str]) -> dict[str, sdiskusage]:
    return {
        mount_point_to_pvc(mount_point):
            mount_point_to_disk_usage(mount_point)
        for mount_point in mount_points
    }


def main():  # pragma: no cover
    start_http_server(os.getenv('APP_HTTP_SERVER_PORT', 8848))

    old_pvcs = set[str]()

    while 1:
        partitions: list[sdiskpart] = \
            psutil.disk_partitions(all=True)
        mount_points = get_relevant_mount_points(partitions)
        if len(mount_points) == 0:
            logger.info("No mounted PVC found.")
        else:
            pvcs_disk_usage: dict[str, sdiskusage] =\
                process_mount_points(mount_points)

            update_stats(pvcs_disk_usage)
            old_pvcs =\
                clean_removed_pvcs(old_pvcs, set(pvcs_disk_usage.keys()))

        time.sleep(15)
