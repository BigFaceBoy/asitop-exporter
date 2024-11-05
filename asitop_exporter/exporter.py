# This file is part of asitop, the interactive NVIDIA-GPU process viewer.
#
# Copyright 2021-2024 fangxuwei. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
# ==============================================================================
"""Prometheus exporter built on top of ``asitop``."""

from __future__ import annotations

import math
import time
from uuid import uuid4
from typing import List
from requests import post
import json
import copy
from collections import deque
from prometheus_client import REGISTRY, CollectorRegistry, Gauge, Info
from asitop_exporter.utils import get_ip_address,get_ram_metrics_dict,run_powermetrics_process
from asitop_exporter.parsers import parse_powermetrics

def get_avg(inlist):
    avg = sum(inlist) / len(inlist)
    return avg


class PrometheusExporter:  # pylint: disable=too-many-instance-attributes
    """Prometheus exporter built on top of ``asitop``."""

    def __init__(  # pylint: disable=too-many-statements
        self,
        hostname: str | None = None,
        *,
        registry: CollectorRegistry = REGISTRY,
        interval: float = 1.0,
        timecode: str | None = None,
        post_url: str | None = None,
        alive_time: int  = 60
    ) -> None:        
        self.hostname = hostname or get_ip_address()
        self.registry = registry
        self.interval = interval
        self.timecode = timecode
        self.post_url = post_url
        self.alive_time = alive_time
        self.powermetrics_process = None


        self.info = Info(
            'asitop',
            documentation='ASITOP Prometheus Exporter.',
            labelnames=['hostname'],
            registry=self.registry,
        )


        self.cpu_peak_power = 0
        self.gpu_peak_power = 0
        self.avg_cpu_power_list = deque([], maxlen = 5)
        self.avg_gpu_power_list = deque([], maxlen = 5)

        self.metrics_dict = {}
        # E-CPU
        self.host_ecpu_percent = Gauge(
            name='host_ECPU_percent',
            documentation='Host E-CPU percent (%).',
            unit='Percentage',
            labelnames=['hostname'],
            registry=self.registry,
        )
        self.host_ecpu_clock = Gauge(
            name='host_ECPU_clock',
            documentation='Host E-CPU clock (MHZ).',
            unit='MHz',
            labelnames=['hostname'],
            registry=self.registry,
        )

        # P-CPU
        self.host_pcpu_percent = Gauge(
            name='host_PCPU_percent',
            documentation='Host P-CPU percent (%).',
            unit='Percentage',
            labelnames=['hostname'],
            registry=self.registry,
        )
        self.host_pcpu_clock = Gauge(
            name='host_PCPU_clock',
            documentation='Host P-CPU clock (MHZ).',
            unit='MHz',
            labelnames=['hostname'],
            registry=self.registry,
        )

        # GPU
        self.host_gpu_percent = Gauge(
            name='host_GPU_percent',
            documentation='Host GPU percent (%).',
            unit='Percentage',
            labelnames=['hostname'],
            registry=self.registry,
        )
        self.host_gpu_clock = Gauge(
            name='host_GPU_clock',
            documentation='Host GPU clock (MHZ).',
            unit='MHz',
            labelnames=['hostname'],
            registry=self.registry,
        )

        # ANE
        self.host_ane_percent = Gauge(
            name='host_ANE_percent',
            documentation='Host ANE percent (%).',
            unit='Percentage',
            labelnames=['hostname'],
            registry=self.registry,
        )
        self.host_ane_power = Gauge(
            name='host_ANE_power',
            documentation='Host ANE power (W).',
            unit='W',
            labelnames=['hostname'],
            registry=self.registry,
        )

        self.host_ram_total = Gauge(
            name='host_RAM_total',
            documentation='Host RAM total (GB).',
            unit='GB',
            labelnames=['hostname'],
            registry=self.registry,
        )
        self.host_ram_used = Gauge(
            name='host_RAM_uesd',
            documentation='Host RAM used (GB).',
            unit='GB',
            labelnames=['hostname'],
            registry=self.registry,
        )
        self.host_ram_free = Gauge(
            name='host_RAM_free',
            documentation='Host RAM free (GB).',
            unit='GB',
            labelnames=['hostname'],
            registry=self.registry,
        )
        self.host_swap_total = Gauge(
            name='host_swap_total',
            documentation='Host swap total (GB).',
            unit='GB',
            labelnames=['hostname'],
            registry=self.registry,
        )
        self.host_swap_used = Gauge(
            name='host_swap_uesd',
            documentation='Host swap used (GB).',
            unit='GB',
            labelnames=['hostname'],
            registry=self.registry,
        )
        self.host_swap_free = Gauge(
            name='host_swap_free',
            documentation='Host swap free (GB).',
            unit='GB',
            labelnames=['hostname'],
            registry=self.registry,
        )

        self.host_cpu_power = Gauge(
            name='host_cpu_power',
            documentation='Host cpu power (W).',
            unit='W',
            labelnames=['hostname'],
            registry=self.registry,
        )
        self.host_cpu_peak_power = Gauge(
            name='host_cpu_peak_power',
            documentation='Host cpu peak power (W).',
            unit='W',
            labelnames=['hostname'],
            registry=self.registry,
        )
        self.host_cpu_avg_power = Gauge(
            name='host_cpu_avg_power',
            documentation='Host cpu avg power (W).',
            unit='W',
            labelnames=['hostname'],
            registry=self.registry,
        )

        self.host_gpu_power = Gauge(
            name='host_gpu_power',
            documentation='Host gpu power (W).',
            unit='W',
            labelnames=['hostname'],
            registry=self.registry,
        )
        self.host_gpu_peak_power = Gauge(
            name='host_gpu_peak_power',
            documentation='Host gpu peak power (W).',
            unit='W',
            labelnames=['hostname'],
            registry=self.registry,
        )
        self.host_gpu_avg_power = Gauge(
            name='host_gpu_avg_power',
            documentation='Host gpu avg power (W).',
            unit='W',
            labelnames=['hostname'],
            registry=self.registry,
        )
    
    def post_result(self):
        uuid = str(uuid4())
        timestamp = int(time.time() * 1000)
        interval = int(self.interval)
        #os.environ.get('APP_ID', 'agi_common')
        metric_json = {
            "cluster" : "jmlj-tonglu-productk8s",
            "namespace": "ezagi",
            "nodeip": get_ip_address(),
            "endpoint": get_ip_address(),
            "metric": "Throughput",
            "value": 1.0,
            "step": interval,
            "counterType": "COUNTER",
            "timestamp": timestamp,
            "uuid": uuid,
            "tags": {
                "url": "",
                "serviceName": "ezagi_algo_m2_iaas"
            },
            "monitorType": "iaas"
        }
        metric_json_list = []
        for k, v in self.metrics_dict.items():
            current_json = metric_json
            current_json['tags']['url'] = k
            current_json['value'] = v
            metric_json_list.append(copy.deepcopy(current_json))

        json_data = json.dumps(metric_json_list)
        headers = {'Content-type': 'application/json'}
        rsp = post(self.post_url, data=json_data, headers=headers)

    def get_reading(self):
        ready = parse_powermetrics(timecode=self.timecode)
        while not ready:
            time.sleep(1)
            ready = parse_powermetrics(timecode=self.timecode)
        return ready

    def collect(self) -> None:
        while True:
            current_time = int(time.time())
            if(current_time - int(self.timecode) >= 60 * self.alive_time):
                self.timecode = str(current_time)
                self.terminate_powermetrics_process()
                self.start_powermetrics_process()

            next_update_time = time.monotonic() + self.interval
            self.update_host()
            time.sleep(max(0.0, next_update_time - time.monotonic()))

    def update_host(self) -> None:
        ready = self.get_reading()
        last_timestamp = ready[-1]

        if ready:
            cpu_metrics_dict, gpu_metrics_dict, thermal_pressure, bandwidth_metrics, timestamp = ready

        ram_metrics_dict = get_ram_metrics_dict()
        ane_max_power = 8.0
        ane_util_percent = int(cpu_metrics_dict["ane_W"] / self.interval / ane_max_power * 100)

        cpu_power_W = cpu_metrics_dict["cpu_W"] / self.interval
        if cpu_power_W > self.cpu_peak_power:
            self.cpu_peak_power = cpu_power_W
        self.avg_cpu_power_list.append(cpu_power_W)
        avg_cpu_power = get_avg(self.avg_cpu_power_list)

        gpu_power_W = cpu_metrics_dict["gpu_W"] / self.interval
        if gpu_power_W > self.gpu_peak_power:
            self.gpu_peak_power = gpu_power_W
        self.avg_gpu_power_list.append(gpu_power_W)
        avg_gpu_power = get_avg(self.avg_gpu_power_list)

        for gauge, value in (
            (self.host_ecpu_percent, cpu_metrics_dict["E-Cluster_active"]),
            (self.host_ecpu_clock, cpu_metrics_dict["E-Cluster_freq_Mhz"]),
            (self.host_pcpu_percent, cpu_metrics_dict["P-Cluster_active"]),
            (self.host_pcpu_clock, cpu_metrics_dict["P-Cluster_freq_Mhz"]),
            (self.host_gpu_percent, gpu_metrics_dict["active"]),
            (self.host_gpu_clock, gpu_metrics_dict["freq_MHz"]),
            (self.host_ane_percent, ane_util_percent),
            (self.host_ane_power, cpu_metrics_dict["ane_W"] / self.interval),

            (self.host_ram_total, ram_metrics_dict["total_GB"]),
            (self.host_ram_used, ram_metrics_dict["used_GB"]),
            (self.host_ram_free, ram_metrics_dict["free_GB"] ),
            (self.host_swap_total, ram_metrics_dict["swap_total_GB"]),
            (self.host_swap_used, ram_metrics_dict["swap_used_GB"]),
            (self.host_swap_free, ram_metrics_dict["swap_free_GB"]),

            (self.host_cpu_power, cpu_power_W),
            (self.host_cpu_peak_power, self.cpu_peak_power),
            (self.host_cpu_avg_power, avg_cpu_power),

            (self.host_gpu_power, gpu_power_W),
            (self.host_gpu_peak_power, self.gpu_peak_power),
            (self.host_gpu_avg_power, avg_gpu_power),
        ):
            gauge.labels(self.hostname).set(value)

        self.metrics_dict["host_ecpu_percent"] = cpu_metrics_dict["E-Cluster_active"]
        self.metrics_dict["host_ecpu_clock"] = cpu_metrics_dict["E-Cluster_freq_Mhz"]
        self.metrics_dict["host_pcpu_percent"] = cpu_metrics_dict["P-Cluster_active"]
        self.metrics_dict["host_pcpu_clock"] = cpu_metrics_dict["P-Cluster_freq_Mhz"]

        self.metrics_dict["host_gpu_percent"] = gpu_metrics_dict["active"]
        self.metrics_dict["host_gpu_clock"] = gpu_metrics_dict["freq_MHz"]
        self.metrics_dict["host_ane_percent"] = ane_util_percent
        self.metrics_dict["host_ane_power"] = cpu_metrics_dict["ane_W"] / self.interval
        
        self.metrics_dict["host_ram_total"] = ram_metrics_dict["total_GB"]
        self.metrics_dict["host_ram_used"] =  ram_metrics_dict["used_GB"]
        self.metrics_dict["host_ram_free"] = ram_metrics_dict["free_GB"]

        self.metrics_dict["host_swap_total"] = ram_metrics_dict["swap_total_GB"]
        self.metrics_dict["host_swap_used"] = ram_metrics_dict["swap_used_GB"]
        self.metrics_dict["host_swap_free"] = ram_metrics_dict["swap_free_GB"]

        self.metrics_dict["host_cpu_power"] = cpu_power_W
        self.metrics_dict["host_cpu_peak_power"] = self.cpu_peak_power
        self.metrics_dict["host_cpu_avg_power"] = avg_cpu_power

        self.metrics_dict["host_gpu_power"] = gpu_power_W
        self.metrics_dict["host_gpu_peak_power"] = self.gpu_peak_power
        self.metrics_dict["host_gpu_avg_power"] = avg_gpu_power

        if(self.post_url is not None):
            self.post_result()


    def start_powermetrics_process(self):
        self.powermetrics_process = run_powermetrics_process(self.timecode, interval=self.interval)
    def terminate_powermetrics_process(self):
        self.powermetrics_process.terminate()