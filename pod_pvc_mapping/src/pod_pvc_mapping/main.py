import logging
import os
from abc import ABC, abstractmethod
from time import sleep
from typing import NamedTuple, cast

from kubernetes import client, config
from kubernetes.client import CoreV1Api, V1PersistentVolumeClaimList, V1PersistentVolumeClaim, V1PodList, V1Pod, \
    V1ObjectMeta, V1PodSpec, V1Volume, V1Namespace, V1NamespaceList, V1PersistentVolumeClaimSpec, \
    V1PersistentVolumeClaimVolumeSource
from lazy import lazy
from prometheus_client import start_http_server, Gauge


class Volume(NamedTuple):
    vol: str
    ns: str
    pod: str


class PodsPvcs(NamedTuple):
    pods: list[V1Pod]
    pvcs: list[V1PersistentVolumeClaim]


formatter = logging.Formatter(os.getenv('APP_LOG_FORMAT', '%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
logger = logging.getLogger(__name__)
logger.setLevel(os.getenv('APP_LOG_LEVEL', logging.INFO))
print_log = logging.StreamHandler()
print_log.setFormatter(formatter)
logger.addHandler(print_log)

gauge = Gauge(
    'pvc_mapping', 'fetching the mapping between pod and pvc',
    ['persistentvolumeclaim', 'volumename', 'mountedby', 'ns']
)


def process_pods(
    pods: list[V1Pod],
    pool: dict[Volume, str],
    pvcs: list[V1PersistentVolumeClaim],
    ns: str,
    new_pool_keys: set[Volume]
):
    for pod in pods:
        pod_name = cast(V1ObjectMeta, pod.metadata).name
        logger.debug(f"pod: {pod_name}")
        try:
            pvc_names: list[str] = list(
                map(
                    lambda voc: cast(
                        V1PersistentVolumeClaimVolumeSource,
                        cast(V1Volume, voc).persistent_volume_claim).claim_name,
                    list(filter(
                        lambda vol: cast(V1Volume, vol.persistent_volume_claim),
                        cast(list[V1Volume], cast(V1PodSpec, pod.spec).volumes)
                    ))
                )
            )
            logger.debug('volumes:')
            logger.debug(pvc_names)
            for pvc_name in pvc_names:
                logger.debug(f"claim: {pvc_name}")
                process_pvc(
                    pvc_name=pvc_name,
                    pvcs=pvcs,
                    pod_name=pod_name,
                    ns=ns,
                    pool=pool,
                    new_pool_keys=new_pool_keys
                )
        except TypeError:
            pass


def process_pvc(pvc_name: str, pvcs: list[V1PersistentVolumeClaim], pod_name: str, pool: dict[Volume, str], ns: str,
                new_pool_keys: set[Volume]):
    for pvc in pvcs:
        pvc_metadata_name = cast(V1ObjectMeta, pvc.metadata).name
        logger.debug(f"vol name: {pvc_metadata_name}")
        logger.debug(f'pvc: {pvc_name}')
        if pvc_metadata_name == pvc_name:
            vol_name = cast(V1PersistentVolumeClaimSpec, pvc.spec).volume_name
            logger.info("NS: %s, POD: %s, VOLUME: %s, PVC: %s" % (ns, pod_name, vol_name, pvc_name))
            vol = Volume(vol=vol_name, pod=pod_name, ns=ns)
            new_pool_keys.add(vol)
            if vol not in pool.keys():
                gauge.labels(pvc_name, vol.vol, vol.pod, vol.ns)
            pool[vol] = pvc_name


def cleanup_pool(pool: dict[Volume, str], old_pool_keys: set[Volume], new_pool_keys: set[Volume]) -> set[Volume]:
    for vol in old_pool_keys - new_pool_keys:
        gauge.remove(pool[vol], vol.vol, vol.pod, vol.ns)
        pool.pop(vol)
    return set(pool.keys())


class KubeClient(ABC):

    @abstractmethod
    def list_namespace(self) -> list[V1Namespace]:
        pass

    @abstractmethod
    def list_namespaced_pod(self, ns: str) -> list[V1Pod]:
        pass

    @abstractmethod
    def list_namespaced_persistent_volume_claim(self, ns: str) -> list[V1PersistentVolumeClaim]:
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


def main_loop(
    pool: dict[Volume, str],
    old_pool_keys: set[Volume],
    kube_client: KubeClient = KubeClientImpl(),
) -> set[Volume]:
    new_pool_keys: set[Volume] = set[Volume]()

    nss: list[V1Namespace] = kube_client.list_namespace()
    # logger.debug(nss)
    for i in nss:
        ns: str = cast(V1ObjectMeta, i.metadata).name
        pods_pvcs = kube_client.get_single_namespace_data(ns)
        if len(pods_pvcs.pvcs) != 0 and len(pods_pvcs.pods) != 0:
            process_pods(pods_pvcs.pods, pool, pods_pvcs.pvcs, ns, new_pool_keys)

    return cleanup_pool(pool=pool, old_pool_keys=old_pool_keys, new_pool_keys=new_pool_keys)


def main(argv: list[str] = None, kube_client: KubeClient = KubeClientImpl()):  # pragma: no cover
    pool: dict[Volume, str] = {}

    old_pool_keys: set[Volume] = set[Volume]()

    start_http_server(os.getenv('APP_HTTP_SERVER_PORT', 8849))

    while 1:
        old_pool_keys = main_loop(
            pool=pool,
            old_pool_keys=old_pool_keys,
            kube_client=kube_client
        )

        logger.info(f'PVCs found: {len(pool)}')

        sleep(15)
