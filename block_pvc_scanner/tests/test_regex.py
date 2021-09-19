import unittest
from block_pvc_scanner import main as bps


class TestRegex(unittest.TestCase):
    def test_single_csi(self):
        mountpoint = '/var/lib/kubelet/pods/b337cf3e-145d-4f97-af0a-28c0cf746684/volumes/kubernetes.io~csi/pvc-a9247e42-5e32-4cbc-85aa-f6c9dd111be1/mount'  # noqa: E501
        assert bps.supported_pvc_re.match(mountpoint)
