import unittest

from psutil._common import sdiskpart

from block_pvc_scanner import main as bps


def sdiskpart_factory(mount_point: str) -> sdiskpart:
    return sdiskpart(
        mountpoint=mount_point,
        device='whatever',
        fstype='no matter',
        opts='',
        maxfile='',
        maxpath=''
    )


class TestPVC(unittest.TestCase):
    def setUp(self) -> None:
        self.mount_point_csi_one: str = "/var/lib/kubelet/plugins/kubernetes.io/csi/pv/pvc-2f0c4198-821b-4629-ab8f-59a993e3cd00/globalmount"  # noqa: E501
        self.mount_point_csi_one_none_plugin: str = "/var/lib/kubelet/pods/aef2f090-0caf-442f-b142-dcddbcf84050/volumes/kubernetes.io~csi/pvc-2f0c4198-821b-4629-ab8f-59a993e3cd00/mount"  # noqa: E501
        self.mount_point_csi_two: str = "/var/lib/kubelet/plugins/kubernetes.io/csi/pv/pvc-8311ea3b-d777-4b81-ac47-cc51f7cc8f39/globalmount"  # noqa: E501
        self.mount_point_csi_three: str = "/var/lib/kubelet/plugins/kubernetes.io/csi/pv/pvc-1651b43f-6d84-44ae-905d-f376b895b7de/globalmount"  # noqa: E501
        self.pvc_csi_one: str = "pvc-2f0c4198-821b-4629-ab8f-59a993e3cd00"
        self.pve_csi_two: str = "pvc-8311ea3b-d777-4b81-ac47-cc51f7cc8f39"
        self.pvc_csi_three: str = "pvc-1651b43f-6d84-44ae-905d-f376b895b7de"
        self.mount_points: list[sdiskpart] = [
            sdiskpart_factory("/"),
            sdiskpart_factory("/dev"),
            sdiskpart_factory(self.mount_point_csi_one),
            sdiskpart_factory(self.mount_point_csi_one_none_plugin),
            sdiskpart_factory(self.mount_point_csi_two),
            sdiskpart_factory(self.mount_point_csi_three)
        ]

    def test_single_csi(self):
        assert bps.supported_pvc_re.match(self.mount_point_csi_one)

    def test_pvc(self):
        assert bps.mount_point_to_pvc(
            self.mount_point_csi_one
        ) == self.pvc_csi_one

    def test_relevant_mount_points(self):
        assert len(bps.get_relevant_mount_points(self.mount_points)) == 3
