import logging
import os
import re
import time

import psutil
from prometheus_client import start_http_server, Gauge

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

supported_pvc_re = re.compile('^.+(kubernetes.io/flexvolume|kubernetes.io~csi|kubernetes.io/gce-pd/mounts).*$')  # noqa: E501
pvc_re = re.compile('^pvc')
gke_data_re = re.compile('^gke-data')


def filter_supported_pvcs(partition):
    if supported_pvc_re.match(partition.mountpoint):
        return True
    return False


def main():
    start_http_server(os.getenv('APP_HTTP_SERVER_PORT', 8848))

    old_labels = set()

    while 1:
        labels = set()
        all_mount_points = list(map(
            lambda p: p.mountpoint, filter(
                filter_supported_pvcs, psutil.disk_partitions()
            )))
        if len(all_mount_points) == 0:
            logger.warning("No mounted PVC found.")
        for mount_point in all_mount_points:
            # get pvc name
            mount_point_parts = mount_point.split('/')
            volume = mount_point_parts[-1]
            for possible_pvc in mount_point_parts:
                if pvc_re.match(possible_pvc):
                    volume = possible_pvc
                elif gke_data_re.match(possible_pvc):
                    volume = 'pvc' + possible_pvc.split('pvc')[-1]

            disk_usage = psutil.disk_usage(mount_point)
            logger.info(f'VOLUME: {volume}, USAGE: {disk_usage.percent}')

            percent_gauge.labels(volume).set(disk_usage.percent)
            total_bytes_gauge.labels(volume).set(disk_usage.total)
            used_bytes_gauge.labels(volume).set(disk_usage.used)
            free_bytes_gauge.labels(volume).set(disk_usage.free)

            labels.add(volume)

        for label in old_labels - labels:
            percent_gauge.remove(label)
            total_bytes_gauge.remove(label)
            used_bytes_gauge.remove(label)
            free_bytes_gauge.remove(label)
        old_labels = labels

        time.sleep(15)
