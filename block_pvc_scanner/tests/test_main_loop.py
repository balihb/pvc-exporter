import unittest

from psutil._common import sdiskusage

from block_pvc_scanner import main as bps


class TestMainLoop(unittest.TestCase):
    def setUp(self) -> None:
        self.pvc_csi_one: str = "pvc-2f0c4198-821b-4629-ab8f-59a993e3cd00"
        self.pvc_csi_two: str = "pvc-8311ea3b-d777-4b81-ac47-cc51f7cc8f39"
        self.pvc_csi_three: str = "pvc-1651b43f-6d84-44ae-905d-f376b895b7de"
        self.mount_point_csi_one: str = f"/var/lib/kubelet/plugins/kubernetes.io/csi/pv/{self.pvc_csi_one}/globalmount"  # noqa: E501
        self.mount_point_csi_one_none_plugin: str = f"/var/lib/kubelet/pods/aef2f090-0caf-442f-b142-dcddbcf84050/volumes/kubernetes.io~csi/{self.pvc_csi_one}/mount"  # noqa: E501
        self.mount_point_csi_two: str = f"/var/lib/kubelet/plugins/kubernetes.io/csi/pv/{self.pvc_csi_two}/globalmount"  # noqa: E501
        self.mount_point_csi_three: str = f"/var/lib/kubelet/plugins/kubernetes.io/csi/pv/{self.pvc_csi_three}/globalmount"  # noqa: E501
        self.mount_points: set[str] = {
            "/",
            "/dev",
            self.mount_point_csi_one,
            self.mount_point_csi_one_none_plugin,
            self.mount_point_csi_two,
            self.mount_point_csi_three
        }
        # 'total', 'used', 'free', 'percent'
        self.disk_usages: dict[str, sdiskusage] = {
            self.mount_point_csi_one: sdiskusage(
                total=20,
                used=6,
                free=14,
                percent=30
            ),
            self.mount_point_csi_one_none_plugin: sdiskusage(
                total=20,
                used=6,
                free=14,
                percent=30
            ),
            self.mount_point_csi_two: sdiskusage(
                total=30,
                used=15,
                free=15,
                percent=50
            ),
            self.mount_point_csi_three: sdiskusage(
                total=40,
                used=28,
                free=12,
                percent=70
            )
        }

    def get_all_mount_points(self) -> set[str]:
        return self.mount_points

    def mount_point_to_disk_usage(self, mount_point: str) -> sdiskusage:  # pragma: no cover
        return self.disk_usages[mount_point]

    def test_1(self):
        bps.main_loop(
            old_pvcs=set[str](),
            get_partitions=self.get_all_mount_points,
            get_usage=self.mount_point_to_disk_usage
        )
