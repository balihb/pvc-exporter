import argparse
import os
from time import sleep
from typing import NamedTuple, cast

from kubernetes.client import V1PersistentVolumeClaim, V1Pod, \
    V1ObjectMeta, V1PodSpec, V1Volume, V1Namespace, V1PersistentVolumeClaimSpec, \
    V1PersistentVolumeClaimVolumeSource
from prometheus_client import start_http_server, Gauge

from pod_pvc_mapping.kubeclinet import KubeClient, KubeClientImpl
from .logger import logger


class Volume(NamedTuple):
    pvc: str
    vol: str
    ns: str
    pod: str


gauge = Gauge(
    'pvc_mapping', 'fetching the mapping between pod and pvc',
    ['persistentvolumeclaim', 'volumename', 'mountedby', 'ns']
)


def process_pods(
    pods: list[V1Pod],
    pvcs: list[V1PersistentVolumeClaim],
    ns: str,
    new_pool: set[Volume]
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
                    new_pool=new_pool
                )
        except TypeError:  # pragma: no cover
            pass


def process_pvc(pvc_name: str, pvcs: list[V1PersistentVolumeClaim], pod_name: str, ns: str,
                new_pool: set[Volume]):
    for pvc in pvcs:
        pvc_metadata_name = cast(V1ObjectMeta, pvc.metadata).name
        logger.debug(f"vol name: {pvc_metadata_name}")
        logger.debug(f'pvc: {pvc_name}')
        if pvc_metadata_name == pvc_name:
            vol_name = cast(V1PersistentVolumeClaimSpec, pvc.spec).volume_name
            logger.info("NS: %s, POD: %s, VOLUME: %s, PVC: %s" % (ns, pod_name, vol_name, pvc_name))
            vol = Volume(pvc=pvc_name, vol=vol_name, pod=pod_name, ns=ns)
            if vol not in new_pool:
                gauge.labels(vol.pvc, vol.vol, vol.pod, vol.ns)
                new_pool.add(vol)


def cleanup_pool(old_pool: set[Volume], new_pool: set[Volume]):
    for vol in old_pool - new_pool:
        gauge.remove(vol.pvc, vol.vol, vol.pod, vol.ns)


def main_loop(
    old_pool: set[Volume],
    kube_client: KubeClient = KubeClientImpl(),
) -> set[Volume]:
    new_pool: set[Volume] = set[Volume]()

    nss: list[V1Namespace] = kube_client.list_namespace()
    # logger.debug(nss)
    for i in nss:
        ns: str = cast(V1ObjectMeta, i.metadata).name
        pods_pvcs = kube_client.get_single_namespace_data(ns)
        if len(pods_pvcs.pvcs) != 0 and len(pods_pvcs.pods) != 0:
            process_pods(pods_pvcs.pods, pods_pvcs.pvcs, ns, new_pool)

    cleanup_pool(old_pool=old_pool, new_pool=new_pool)
    return new_pool


def main(argv: argparse.Namespace = None, kube_client: KubeClient = KubeClientImpl()):  # pragma: no cover
    old_pool: set[Volume] = set[Volume]()

    start_http_server(os.getenv('APP_HTTP_SERVER_PORT', 8849))

    while 1:
        old_pool = main_loop(
            old_pool=old_pool,
            kube_client=kube_client
        )

        logger.info(f'PVCs found: {len(old_pool)}')

        sleep(15)
