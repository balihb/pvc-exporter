import logging
import os
from collections import namedtuple
from time import sleep
from typing import Any

from kubernetes import client, config
from kubernetes.client import CoreV1Api
from prometheus_client import start_http_server, Gauge

Volume = namedtuple('Volume', ['vol', 'ns', 'pod'])

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


def get_items(obj):
    obj_dict = obj.to_dict()
    items = obj_dict['items']
    return items


def process_pods(
    pods: list[Any], pool: dict[str, Volume],
    pvcs: list[Any], ns: str, new_pool_keys: set[str]
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
    pool: dict[str, Volume], ns: str, new_pool_keys: set[str]
):
    for v in pvcs:
        logger.debug(f"vol name: {v['metadata']['name']}")
        logger.debug(f'pvc: {pvc}')
        if v['metadata']['name'] == pvc:
            vol = v['spec']['volume_name']
            logger.info(
                "NS: %s, POD: %s, VOLUME: %s, PVC: %s" %
                (ns, pod_name, vol, pvc)
            )
            new_pool_keys.add(pvc)
            if pvc in pool.keys():
                gauge.remove(
                    pvc,
                    pool[pvc].vol, pool[pvc].pod, pool[pvc].ns
                )
            gauge.labels(pvc, vol, pod_name, ns)
            pool[pvc] = Volume(vol=vol, pod=pod_name, ns=ns)


def cleanup_pool(
    pool: dict[str, Volume],
    old_pool_keys: set[str], new_pool_keys: set[str]
) -> set[str]:
    for pvc in old_pool_keys - new_pool_keys:
        gauge.remove(
            pvc, pool[pvc].vol, pool[pvc].pod, pool[pvc].ns
        )
        pool.pop(pvc)
    return set(pool.keys())


def main():
    pool: dict[str, Volume] = {}

    old_pool_keys: set[str] = set()

    start_http_server(os.getenv('APP_HTTP_SERVER_PORT', 8849))

    config.load_incluster_config()
    k8s_api: CoreV1Api = client.CoreV1Api()

    while 1:
        new_pool_keys: set[str] = set()

        nss: list[Any] = get_items(k8s_api.list_namespace())
        # logger.debug(nss)
        for i in nss:
            ns = i['metadata']['name']
            logger.debug(f'ns: {ns}')
            pods: list[Any] = get_items(k8s_api.list_namespaced_pod(ns))
            # logger.debug(pods)
            pvcs: list[Any] = get_items(
                k8s_api.list_namespaced_persistent_volume_claim(ns)
            )
            logger.debug('pvcs:')
            logger.debug(list(map(
                lambda v: (
                    v['metadata']['name'],
                    v['spec']['volume_name']
                ),
                pvcs
            )))
            if len(pvcs) != 0 and len(pods) != 0:
                process_pods(pods, pool, pvcs, ns, new_pool_keys)

        old_pool_keys = cleanup_pool(
            pool=pool,
            old_pool_keys=old_pool_keys,
            new_pool_keys=new_pool_keys
        )

        sleep(15)
