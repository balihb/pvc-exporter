import unittest

from pod_pvc_mapping import main as ppm
from pod_pvc_mapping.main import Volume
from pod_pvc_mapping.main import gauge
from .data import just_one, empty_env, different_namespace, two_vol_same_ns, two_vol_same_ns_vol_removed


class TestMainLoop(unittest.TestCase):
    def setUp(self) -> None:
        gauge.clear()

    def tearDown(self) -> None:
        gauge.clear()

    def test_just_once(self):
        ppm.main_loop(
            old_pool=set[Volume](),
            kube_client=just_one
        )
        gc = gauge.collect()
        assert len(gc[0].samples) == 1 and gc[0].samples[0].labels == {
            'persistentvolumeclaim': 'tst_claim_1',
            'volumename': 'pvc-2f0c4198-821b-4629-ab8f-59a993e3cd00',
            'mountedby': 'tst_pod_1',
            'ns': 'tst_ns_1'
        }

    def test_twice(self):
        old_pool = set[Volume]()
        old_pool = ppm.main_loop(
            old_pool=old_pool,
            kube_client=just_one
        )
        ppm.main_loop(
            old_pool=old_pool,
            kube_client=just_one
        )
        gc = gauge.collect()
        assert len(gc[0].samples) == 1 and gc[0].samples[0].labels == {
            'persistentvolumeclaim': 'tst_claim_1',
            'volumename': 'pvc-2f0c4198-821b-4629-ab8f-59a993e3cd00',
            'mountedby': 'tst_pod_1',
            'ns': 'tst_ns_1'
        }

    def test_three_times(self):
        old_pool = set[Volume]()
        old_pool = ppm.main_loop(
            old_pool=old_pool,
            kube_client=just_one
        )
        old_pool = ppm.main_loop(
            old_pool=old_pool,
            kube_client=just_one
        )
        ppm.main_loop(
            old_pool=old_pool,
            kube_client=just_one
        )
        gc = gauge.collect()
        assert len(gc[0].samples) == 1 and gc[0].samples[0].labels == {
            'persistentvolumeclaim': 'tst_claim_1',
            'volumename': 'pvc-2f0c4198-821b-4629-ab8f-59a993e3cd00',
            'mountedby': 'tst_pod_1',
            'ns': 'tst_ns_1'
        }

    def test_empty(self):
        ppm.main_loop(
            old_pool=set[Volume](),
            kube_client=empty_env
        )
        gc = gauge.collect()
        assert len(gc[0].samples) == 0

    def test_different_namespace(self):
        ppm.main_loop(
            old_pool=set[Volume](),
            kube_client=different_namespace
        )
        gc = gauge.collect()
        assert \
            len(gc[0].samples) == 2 and gc[0].samples[0].labels == {
                'persistentvolumeclaim': 'tst_claim_1',
                'volumename': 'pvc-9f2c31f4-e31c-459f-bdb4-08b0ba086644',
                'mountedby': 'tst_pod_1',
                'ns': 'tst_ns_1'
            } and gc[0].samples[1].labels == {
                'persistentvolumeclaim': 'tst_claim_1',
                'volumename': 'pvc-40416cb8-37fb-4c27-ad06-e4f1d851b740',
                'mountedby': 'tst_pod_1',
                'ns': 'tst_ns_2'
            }

    def test_different_namespace_twice(self):
        old_pool = set[Volume]()
        old_pool = ppm.main_loop(
            old_pool=old_pool,
            kube_client=different_namespace
        )
        ppm.main_loop(
            old_pool=old_pool,
            kube_client=different_namespace
        )
        gc = gauge.collect()
        assert \
            len(gc[0].samples) == 2 and gc[0].samples[0].labels == {
                'persistentvolumeclaim': 'tst_claim_1',
                'volumename': 'pvc-9f2c31f4-e31c-459f-bdb4-08b0ba086644',
                'mountedby': 'tst_pod_1',
                'ns': 'tst_ns_1'
            } and gc[0].samples[1].labels == {
                'persistentvolumeclaim': 'tst_claim_1',
                'volumename': 'pvc-40416cb8-37fb-4c27-ad06-e4f1d851b740',
                'mountedby': 'tst_pod_1',
                'ns': 'tst_ns_2'
            }

    def test_volume_remove(self):
        old_pool = set[Volume]()
        old_pool = ppm.main_loop(
            old_pool=old_pool,
            kube_client=two_vol_same_ns
        )
        gc_pre_remove = gauge.collect()
        ppm.main_loop(
            old_pool=old_pool,
            kube_client=two_vol_same_ns_vol_removed
        )
        gc_post_remove = gauge.collect()
        assert \
            len(gc_pre_remove[0].samples) == 2 and gc_pre_remove[0].samples[0].labels == {
                'persistentvolumeclaim': 'tst_claim_1',
                'volumename': 'pvc-9f2c31f4-e31c-459f-bdb4-08b0ba086644',
                'mountedby': 'tst_pod_1',
                'ns': 'tst_ns_1'
            } and gc_pre_remove[0].samples[1].labels == {
                'persistentvolumeclaim': 'tst_claim_2',
                'volumename': 'pvc-40416cb8-37fb-4c27-ad06-e4f1d851b740',
                'mountedby': 'tst_pod_1',
                'ns': 'tst_ns_1'
            } and len(gc_post_remove[0].samples) == 1 and gc_post_remove[0].samples[0].labels == {
                'persistentvolumeclaim': 'tst_claim_1',
                'volumename': 'pvc-9f2c31f4-e31c-459f-bdb4-08b0ba086644',
                'mountedby': 'tst_pod_1',
                'ns': 'tst_ns_1'
            }
