# pvc-exporter
[![License](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](https://opensource.org/licenses/Apache-2.0)
[![Artifact Hub](https://img.shields.io/endpoint?url=https://artifacthub.io/badge/repository/pvc-exporter)](https://artifacthub.io/packages/search?repo=pvc-exporter)  
This item provides 2 metrics,one for monitoring mounted pvc usage precent named pvc_usage, and one for provides the mapping between pod and pvc named pvc_mapping.

# Note
Only used to monitor mounted pvc that provied by block storage provisioner. Such as longgorn,trident,rook-ceph,etc..

# Support list
The following storage provisioners has been tested..  
1.longgorn  
2.trident  
3.rook-ceph  
4.aliyun flexvolume  
5.iomesh  
6.nutanix-csi
 
# Install
You can get the following files and run apply them.
kubectl apply -f namespace.yml -f rbac.yml -f deployment.yml -f daemonset.yml -f servicemonitor.yml

# Grafana

You can import the pvc_usage-dashboard to grafana to monitor pvc usage.
![grafana-1](./images/grafana-1.PNG)
The format for legend is pod:pvc.
