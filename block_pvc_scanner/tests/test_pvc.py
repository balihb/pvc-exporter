import unittest

from block_pvc_scanner import main as bps
from .data import mount_point_csi_one, pvc_csi_one, mount_points


class TestPVC(unittest.TestCase):
    def test_single_csi(self):
        assert bps.supported_pvc_re.match(mount_point_csi_one)

    def test_pvc(self):
        assert bps.mount_point_to_pvc(mount_point_csi_one) == pvc_csi_one

    def test_relevant_mount_points(self):
        assert len(bps.get_relevant_mount_points(mount_points)) == 3

    def test_empty(self):
        assert len(bps.get_relevant_mount_points(set[str]())) == 0
