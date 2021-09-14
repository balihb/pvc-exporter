import logging
import os
from time import sleep

from kubernetes import client, config
from prometheus_client import start_http_server, Gauge

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
    ['persistentvolumeclaim', 'volumename', 'mountedby']
)


def get_items(obj):
    obj_dict = obj.to_dict()
    items = obj_dict['items']
    return items


def process_pods(pvcs, pods, pool: dict, new_pool_keys: set[str]):
    for pod in pods:
        logger.debug(pod['metadata']['name'])
        for vc in pod['spec']['volumes']:
            if vc['persistent_volume_claim']:
                logger.debug(vc['persistent_volume_claim']['claim_name'])
                process_pvc(
                    pvc=vc['persistent_volume_claim']['claim_name'],
                    pvcs=pvcs,
                    pod_name=pod['metadata']['name'],
                    pool=pool,
                    new_pool_keys=new_pool_keys
                )


def process_pvc(
    pvc: str, pvcs, pod_name: str,
    pool: dict, new_pool_keys: set[str]
):
    for v in pvcs:
        logger.debug(v['metadata']['name'])
        logger.debug(pvc)
        if v['metadata']['name'] == pvc:
            vol = v['spec']['volume_name']
            logger.info("PVC: %s, VOLUME: %s, POD: %s" % (pvc, vol, pod_name))
            new_pool_keys.add(pvc)
            if pvc in pool.keys():
                gauge.remove(pvc, pool[pvc][0], pool[pvc][1])
                gauge.labels(pvc, vol, pod_name)
                pool[pvc] = [vol, pod_name]
            else:
                gauge.labels(pvc, vol, pod_name)
                pool[pvc] = [vol, pod_name]


def cleanup_pool(pool: dict, old_pool_keys: set[str], new_pool_keys: set[str]):
    for pvc in old_pool_keys - new_pool_keys:
        gauge.remove(pvc, pool[pvc][0], pool[pvc][1])
        pool.pop(pvc)
    return pool.keys()


def main():
    pool = {}

    old_pool_keys = set()

    start_http_server(os.getenv('APP_HTTP_SERVER_PORT', 8849))

    config.load_incluster_config()
    k8s_api_obj = client.CoreV1Api()

    while 1:
        new_pool_keys = set()

        nss = get_items(k8s_api_obj.list_namespace())
        logger.debug(nss)
        for i in nss:
            ns = i['metadata']['name']
            logger.debug(ns)
            pods = get_items(k8s_api_obj.list_namespaced_pod(ns))
            logger.debug(pods)
            pvcs = get_items(
                k8s_api_obj.list_namespaced_persistent_volume_claim(ns)
            )
            logger.debug(pvcs)
            process_pods(pods, pool, pvcs, new_pool_keys)

        old_pool_keys = cleanup_pool(
            pool=pool,
            old_pool_keys=old_pool_keys,
            new_pool_keys=new_pool_keys
        )

        sleep(15)
