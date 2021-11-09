from typing import cast

from kubernetes.client import V1PersistentVolumeClaim, V1Pod, V1Namespace, V1ObjectMeta

from pod_pvc_mapping.main import KubeClient


class TstKubeClientImpl(KubeClient):
    nss: list[V1Namespace]
    pods: list[V1Pod]
    pvcs: list[V1PersistentVolumeClaim]

    def __init__(
        self,
        nss: list[V1Namespace],
        pods: list[V1Pod],
        pvcs: list[V1PersistentVolumeClaim]
    ):
        self.nss = nss
        self.pods = pods
        self.pvcs = pvcs

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
