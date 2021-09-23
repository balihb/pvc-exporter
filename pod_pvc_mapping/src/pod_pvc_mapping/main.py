import logging
import os
from abc import ABC, abstractmethod
from collections import namedtuple
from time import sleep
from typing import Any

from kubernetes import client, config
from kubernetes.client import CoreV1Api
from lazy import lazy
from prometheus_client import start_http_server, Gauge

Volume = namedtuple('Volume', ['vol', 'ns', 'pod'])
PodsPvcs = namedtuple('PodsPvcs', ['pods', 'pvcs'])

formatter = logging.Formatter(os.getenv(
    'APP_LOG_FORMAT',
    '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
))
logger = logging.getLogger(__name__)
logger.setLevel(os.getenv('APP_LOG_LEVEL', logging.INFO))
print_log = logging.StreamHandler()
print_log.setFormatter(formatter)
logger.addHandler(print_log)

gauge = Gauge(
    'pvc_mapping',
    'fetching the mapping between pod and pvc',
    ['persistentvolumeclaim', 'volumename', 'mountedby', 'ns']
)


def process_pods(
    pods: list[Any], pool: dict[Volume, str],
    pvcs: list[Any], ns: str, new_pool_keys: set[Volume]
):
    for pod in pods:
        logger.debug(f"pod: {pod['metadata']['name']}")
        try:
            logger.debug('volumes:')
            logger.debug(list(map(
                lambda voc:
                voc['persistent_volume_claim']['claim_name'],
                list(filter(
                    lambda vocl: vocl['persistent_volume_claim'],
                    pod['spec']['volumes']
                ))
            )))
            for vc in pod['spec']['volumes']:
                if vc['persistent_volume_claim']:
                    logger.debug(
                        f"claim: {vc['persistent_volume_claim']['claim_name']}"
                    )
                    process_pvc(
                        pvc=vc['persistent_volume_claim']['claim_name'],
                        pvcs=pvcs,
                        pod_name=pod['metadata']['name'],
                        ns=ns,
                        pool=pool,
                        new_pool_keys=new_pool_keys
                    )
        except TypeError:
            pass


def process_pvc(
    pvc: str, pvcs: list[Any], pod_name: str,
    pool: dict[Volume, str], ns: str, new_pool_keys: set[Volume]
):
    for v in pvcs:
        logger.debug(f"vol name: {v['metadata']['name']}")
        logger.debug(f'pvc: {pvc}')
        if v['metadata']['name'] == pvc:
            vol_name = v['spec']['volume_name']
            logger.info(
                "NS: %s, POD: %s, VOLUME: %s, PVC: %s" %
                (ns, pod_name, vol_name, pvc)
            )
            vol = Volume(vol=vol_name, pod=pod_name, ns=ns)
            new_pool_keys.add(vol)
            if vol in pool.keys():
                gauge.remove(
                    pvc,
                    vol.vol, vol.pod, vol.ns
                )
            gauge.labels(pvc, vol.vol, vol.pod, vol.ns)
            pool[vol] = pvc


def cleanup_pool(
    pool: dict[Volume, str],
    old_pool_keys: set[Volume], new_pool_keys: set[Volume]
) -> set[Volume]:
    for vol in old_pool_keys - new_pool_keys:
        gauge.remove(
            pool[vol], vol.vol, vol.pod, vol.ns
        )
        pool.pop(vol)
    return set(pool.keys())


def get_items(obj):
    obj_dict = obj.to_dict()
    items = obj_dict['items']
    return items


class KubeClient(ABC):
    @abstractmethod
    def list_namespace(self) -> list[Any]:
        pass

    @abstractmethod
    def list_namespaced_pod(self, ns: str) -> list[Any]:
        pass

    @abstractmethod
    def list_namespaced_persistent_volume_claim(self, ns: str) -> list[Any]:
        pass

    @abstractmethod
    def get_single_namespace_data(self, ns: str) -> PodsPvcs:
        pass


class KubeClientImpl(KubeClient):
    @lazy
    def k8s_api_client(self) -> CoreV1Api:
        config.load_incluster_config()
        return client.CoreV1Api()

    def list_namespace(self) -> list[Any]:
        return get_items(self.k8s_api_client.list_namespace())

    def list_namespaced_pod(self, ns: str) -> list[Any]:
        return get_items(self.k8s_api_client.list_namespaced_pod(ns))

    def list_namespaced_persistent_volume_claim(self, ns: str) -> list[Any]:
        return get_items(
            self.k8s_api_client.list_namespaced_persistent_volume_claim(ns)
        )

    def get_single_namespace_data(self, ns: str) -> PodsPvcs:
        logger.debug(f'ns: {ns}')
        pods: list[Any] = self.list_namespaced_pod(ns)
        # logger.debug(pods)
        pvcs: list[Any] = \
            self.list_namespaced_persistent_volume_claim(ns)
        logger.debug('pvcs:')
        logger.debug(list(map(
            lambda v: (
                v['metadata']['name'],
                v['spec']['volume_name']
            ),
            pvcs
        )))
        return PodsPvcs(
            pods=pods,
            pvcs=pvcs
        )


def main(
    argv: list[str] = None,
    kube_client: KubeClient = KubeClientImpl()
):
    pool: dict[Volume, str] = {}

    old_pool_keys: set[Volume] = set[Volume]()

    start_http_server(os.getenv('APP_HTTP_SERVER_PORT', 8849))

    while 1:
        new_pool_keys: set[Volume] = set[Volume]()

        nss: list[Any] = kube_client.list_namespace()
        # logger.debug(nss)
        for i in nss:
            ns: str = i['metadata']['name']
            pods_pvcs = kube_client.get_single_namespace_data(ns)
            if len(pods_pvcs.pvcs) != 0 and len(pods_pvcs.pods) != 0:
                process_pods(
                    pods_pvcs.pods,
                    pool,
                    pods_pvcs.pvcs,
                    ns,
                    new_pool_keys
                )

        old_pool_keys = cleanup_pool(
            pool=pool,
            old_pool_keys=old_pool_keys,
            new_pool_keys=new_pool_keys
        )

        logger.info(f'PVCs found: {len(pool)}')

        sleep(15)
