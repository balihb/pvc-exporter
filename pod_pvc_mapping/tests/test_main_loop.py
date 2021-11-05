import unittest
from typing import NamedTuple, cast

from kubernetes.client import V1PersistentVolumeClaim, V1Pod, V1Namespace, V1ObjectMeta, V1PodSpec, V1Volume, \
    V1PersistentVolumeClaimVolumeSource, V1PersistentVolumeClaimSpec, V1Container

from pod_pvc_mapping import main as ppm
from pod_pvc_mapping.main import KubeClient
from pod_pvc_mapping.main import Volume


class TstEnv(NamedTuple):
    nss: list[V1Namespace]
    pods: list[V1Pod]
    pvcs: list[V1PersistentVolumeClaim]


class TstKubeClientImpl(KubeClient):
    nss: list[V1Namespace]
    pods: list[V1Pod]
    pvcs: list[V1PersistentVolumeClaim]

    def __init__(
        self,
        test_env: TstEnv
    ):
        self.nss = test_env.nss
        self.pods = test_env.pods
        self.pvcs = test_env.pvcs

    def list_namespace(self) -> list[V1Namespace]:
        return self.nss

    def list_namespaced_pod(self, ns: str) -> list[V1Pod]:
        return list(filter(
            lambda pod: cast(V1ObjectMeta, pod.metadata).namespace == ns,
            self.pods
        ))

    def list_namespaced_persistent_volume_claim(self, ns: str) -> list[V1PersistentVolumeClaim]:
        return list(filter(
            lambda pvc: cast(V1ObjectMeta, pvc.metadata).namespace == ns,
            self.pvcs
        ))


class TestMainLoop(unittest.TestCase):

    def setUp(self) -> None:
        self.test_env_1 = TstEnv(
            nss=[
                V1Namespace(
                    metadata=V1ObjectMeta(
                        name='tst_ns_1'
                    )
                )
            ],
            pods=[
                V1Pod(
                    metadata=V1ObjectMeta(
                        name='tst_pod_1',
                        namespace='tst_ns_1'
                    ),
                    spec=V1PodSpec(
                        containers=[
                            V1Container(
                                name='tst_pod_1_cnt'
                            )
                        ],
                        volumes=[
                            V1Volume(
                                name='tst_vol',
                                persistent_volume_claim=V1PersistentVolumeClaimVolumeSource(
                                    claim_name='tst_claim_1'
                                )
                            )
                        ]
                    )
                )
            ],
            pvcs=[
                V1PersistentVolumeClaim(
                    metadata=V1ObjectMeta(
                        name='tst_claim_1',
                        namespace='tst_ns_1'
                    ),
                    spec=V1PersistentVolumeClaimSpec(
                        volume_name='pvc-2f0c4198-821b-4629-ab8f-59a993e3cd00'
                    )
                )
            ]
        )
        self.tst_kube_client_1 = TstKubeClientImpl(
            test_env=self.test_env_1
        )

    def test_env_1_start(self):
        assert ppm.main_loop(
            old_pool_keys=set[Volume](),
            pool={},
            kube_client=self.tst_kube_client_1
        )
