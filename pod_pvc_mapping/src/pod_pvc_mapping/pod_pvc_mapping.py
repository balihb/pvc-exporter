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


def main():
    pool = {}

    old_pool = set()

    start_http_server(os.getenv('APP_HTTP_SERVER_PORT', 8848))

    while 1:
        config.load_incluster_config()
        k8s_api_obj = client.CoreV1Api()
        nss = get_items(k8s_api_obj.list_namespace())
        for i in nss:
            ns = i['metadata']['name']
            pods = get_items(k8s_api_obj.list_namespaced_pod(ns))
            pvcs = get_items(
                k8s_api_obj.list_namespaced_persistent_volume_claim(ns)
            )
            for p in pods:
                for vc in p['spec']['volumes']:
                    if vc['persistent_volume_claim']:
                        pvc = vc['persistent_volume_claim']['claim_name']
                        for v in pvcs:
                            if v['metadata']['name'] == pvc:
                                vol = v['spec']['volume_name']
                        pod = p['metadata']['name']
                        logger.info("PVC: %s, VOLUME: %s, POD: %s" %
                                    (pvc, vol, pod)
                                    )
                        if pvc in pool.keys():
                            gauge.remove(pvc, pool[pvc][0], pool[pvc][1])
                            gauge.labels(pvc, vol, pod)
                            pool[pvc] = [vol, pod]
                        else:
                            gauge.labels(pvc, vol, pod)
                            pool[pvc] = [vol, pod]

        for pvc in old_pool - pool.keys():
            gauge.remove(pvc, pool[pvc][0], pool[pvc][1])
            pool.pop(pvc)
        old_pool = pool.keys()

        sleep(15)
