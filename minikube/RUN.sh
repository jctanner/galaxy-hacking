#!/bin/bash


minikube delete
set -e

minikube start --driver=kvm --cpus=4 --memory=16g --disk-size=40g
minikube addons enable registry
minikube addons enable ingress
minikube addons enable ingress-dns
