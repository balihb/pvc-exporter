import unittest

from psutil._common import sdiskusage

from block_pvc_scanner import main as bps
from block_pvc_scanner.main import percent_gauge
from .data import mount_points, disk_usages


def get_all_mount_points() -> set[str]:
    return mount_points


def get_all_mount_points_empty() -> set[str]:
    return set[str]()


def mount_point_to_disk_usage(mount_point: str) -> sdiskusage:
    return disk_usages[mount_point]


class TestMainLoop(unittest.TestCase):
    def setUp(self) -> None:
        percent_gauge.clear()

    def test_1(self):
        old_pvcs = set[str]()
        old_pvcs = bps.main_loop(
            old_pvcs=old_pvcs,
            get_partitions=get_all_mount_points,
            get_usage=mount_point_to_disk_usage
        )
        assert len(old_pvcs) == 3 and len(percent_gauge.collect()[0].samples) == 3

    def test_empty(self):
        old_pvcs = set[str]()
        old_pvcs = bps.main_loop(
            old_pvcs=old_pvcs,
            get_partitions=get_all_mount_points_empty,
            get_usage=mount_point_to_disk_usage
        )
        assert len(old_pvcs) == 0 and len(percent_gauge.collect()[0].samples) == 0

    def test_three_to_empty(self):
        old_pvcs = set[str]()
        old_pvcs = bps.main_loop(
            old_pvcs=old_pvcs,
            get_partitions=get_all_mount_points,
            get_usage=mount_point_to_disk_usage
        )
        old_pvcs_three = old_pvcs
        old_samples = len(percent_gauge.collect()[0].samples)
        old_pvcs = bps.main_loop(
            old_pvcs=old_pvcs,
            get_partitions=get_all_mount_points_empty,
            get_usage=mount_point_to_disk_usage
        )
        assert(
            len(old_pvcs) == 0 and len(old_pvcs_three) == 3 and
            len(percent_gauge.collect()[0].samples) == 0 and old_samples == 3
        )
