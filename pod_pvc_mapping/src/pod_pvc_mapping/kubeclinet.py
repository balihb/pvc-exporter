from abc import abstractmethod, ABC
from typing import NamedTuple, cast

from kubernetes import client, config
from kubernetes.client import CoreV1Api, V1PersistentVolumeClaimList, V1PersistentVolumeClaim, V1PodList, V1Pod, \
    V1ObjectMeta, V1Namespace, V1NamespaceList, V1PersistentVolumeClaimSpec
from lazy import lazy

from .logger import logger


class PodsPvcs(NamedTuple):
    pods: list[V1Pod]
    pvcs: list[V1PersistentVolumeClaim]


class KubeClient(ABC):

    @abstractmethod
    def list_namespace(self) -> list[V1Namespace]:  # pragma: no cover
        pass

    @abstractmethod
    def list_namespaced_pod(self, ns: str) -> list[V1Pod]:  # pragma: no cover
        pass

    @abstractmethod
    def list_namespaced_persistent_volume_claim(self, ns: str) -> list[V1PersistentVolumeClaim]:  # pragma: no cover
        pass

    def get_single_namespace_data(self, ns: str) -> PodsPvcs:
        logger.debug(f'ns: {ns}')
        pods: list[V1Pod] = self.list_namespaced_pod(ns)
        # logger.debug(pods)
        pvcs: list[V1PersistentVolumeClaim] = self.list_namespaced_persistent_volume_claim(ns)
        logger.debug('pvcs:')
        logger.debug(list(
            map(lambda v: (cast(V1ObjectMeta, v.metadata).name, cast(V1PersistentVolumeClaimSpec, v.spec).volume_name),
                pvcs)))
        return PodsPvcs(pods=pods, pvcs=pvcs)


class KubeClientImpl(KubeClient):  # pragma: no cover

    @lazy
    def k8s_api_client(self) -> CoreV1Api:
        config.load_incluster_config()
        return client.CoreV1Api()

    def list_namespace(self) -> list[V1Namespace]:
        return cast(V1NamespaceList, self.k8s_api_client.list_namespace()).items

    def list_namespaced_pod(self, ns: str) -> list[V1Pod]:
        return cast(V1PodList, self.k8s_api_client.list_namespaced_pod(ns)).items

    def list_namespaced_persistent_volume_claim(self, ns: str) -> list[V1PersistentVolumeClaim]:
        return cast(V1PersistentVolumeClaimList, self.k8s_api_client.list_namespaced_persistent_volume_claim(ns)).items
