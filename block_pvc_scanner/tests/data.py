from psutil._common import sdiskusage

pvc_csi_one: str = "pvc-2f0c4198-821b-4629-ab8f-59a993e3cd00"
pvc_csi_two: str = "pvc-8311ea3b-d777-4b81-ac47-cc51f7cc8f39"
pvc_csi_three: str = "pvc-1651b43f-6d84-44ae-905d-f376b895b7de"
mount_point_csi_one: str = f"/var/lib/kubelet/plugins/kubernetes.io/csi/pv/{pvc_csi_one}/globalmount"  # noqa: E501
mount_point_csi_one_none_plugin: str = f"/var/lib/kubelet/pods/aef2f090-0caf-442f-b142-dcddbcf84050/volumes/kubernetes.io~csi/{pvc_csi_one}/mount"  # noqa: E501
mount_point_csi_two: str = f"/var/lib/kubelet/plugins/kubernetes.io/csi/pv/{pvc_csi_two}/globalmount"  # noqa: E501
mount_point_csi_three: str = f"/var/lib/kubelet/plugins/kubernetes.io/csi/pv/{pvc_csi_three}/globalmount"  # noqa: E501
mount_points: set[str] = {
    "/",
    "/dev",
    mount_point_csi_one,
    mount_point_csi_one_none_plugin,
    mount_point_csi_two,
    mount_point_csi_three
}
# 'total', 'used', 'free', 'percent'
disk_usages: dict[str, sdiskusage] = {
    mount_point_csi_one: sdiskusage(
        total=20,
        used=6,
        free=14,
        percent=30
    ),
    mount_point_csi_one_none_plugin: sdiskusage(
        total=20,
        used=6,
        free=14,
        percent=30
    ),
    mount_point_csi_two: sdiskusage(
        total=30,
        used=15,
        free=15,
        percent=50
    ),
    mount_point_csi_three: sdiskusage(
        total=40,
        used=28,
        free=12,
        percent=70
    )
}
