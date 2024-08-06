# Copyright (c) 2024, NVIDIA CORPORATION.
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

"""This module provides functionality for cluster inference"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional
from logging import Logger

import pandas as pd

from spark_rapids_pytools.cloud_api.sp_types import PlatformBase, ClusterBase
from spark_rapids_pytools.common.prop_manager import JSONPropertiesContainer
from spark_rapids_pytools.common.utilities import ToolLogging


class ClusterType(Enum):
    """
    Enum for cluster types
    """
    CPU = 'CPU'
    GPU = 'GPU'

    def __str__(self):
        return self.value


@dataclass
class ClusterInference:
    """
    Class for inferring cluster information and constructing CPU or GPU clusters.

    :param platform: The platform on which the cluster inference is performed.
    """
    platform: PlatformBase = field(default=None, init=True)
    cluster_type: ClusterType = field(default=ClusterType.CPU, init=True)
    logger: Logger = field(default=ToolLogging.get_and_setup_logger('rapids.tools.cluster_inference'), init=False)

    def _get_cluster_template_args(self, cluster_info_df: pd.Series) -> Optional[dict]:
        """
        Extract information about drivers and workers from input json
        """
        # Currently we support only single driver node for all CSPs
        num_driver_nodes = 1
        driver_node_type = cluster_info_df.get('Driver Node Type')
        # If driver instance is not set, use the default value from platform configurations
        if pd.isna(driver_node_type):
            driver_node_type = self.platform.configs.get_value('clusterInference', 'defaultCpuInstances', 'driver')
        num_worker_nodes = cluster_info_df.get('Num Worker Nodes')
        worker_node_type = cluster_info_df.get('Worker Node Type')
        if pd.isna(worker_node_type):
            # If worker instance is not set, use the default value based on the number of cores
            cores_per_executor = cluster_info_df.get('Cores Per Executor')
            execs_per_node = cluster_info_df.get('Num Executors Per Node')
            total_cores_per_node = execs_per_node * cores_per_executor
            if pd.isna(total_cores_per_node):
                self.logger.info('For App ID: %s, Unable to infer %s cluster. Reason - Total cores per node cannot'
                                 ' be determined.', cluster_info_df['App ID'], self.cluster_type)
                return None
            # TODO - need to account for number of GPUs per executor
            worker_node_type = self.platform.get_matching_worker_node_type(total_cores_per_node)
            if worker_node_type is None:
                self.logger.info('For App ID: %s, Unable to infer %s cluster. Reason - No matching worker node '
                                 'found for num cores = %d', cluster_info_df['App ID'], self.cluster_type,
                                 total_cores_per_node)
                return None
        return {
            'DRIVER_NODE_TYPE': f'"{driver_node_type}"',
            'NUM_DRIVER_NODES': int(num_driver_nodes),
            'WORKER_NODE_TYPE': f'"{worker_node_type}"',
            'NUM_WORKER_NODES': int(num_worker_nodes)
        }

    def infer_cluster(self, cluster_info_df: pd.DataFrame) -> Optional[ClusterBase]:
        """
        Infer CPU or GPU cluster configuration based input cluster df and return the constructed cluster object.
        """
        try:
            if len(cluster_info_df) != 1:
                self.logger.info('Cannot infer %s cluster from event logs. Only single cluster is supported.',
                                 self.cluster_type)
                return None

            # Extract cluster information from parsed logs. Above check ensures df contains single row.
            cluster_template_args = self._get_cluster_template_args(cluster_info_df.iloc[0])
            if cluster_template_args is None:
                return None
            # Construct cluster configuration using platform-specific logic
            cluster_conf = self.platform.generate_cluster_configuration(cluster_template_args)
            if cluster_conf is None:
                return None
            cluster_props_new = JSONPropertiesContainer(cluster_conf, file_load=False)
            return self.platform.load_cluster_by_prop(cluster_props_new, is_inferred=True)
        except Exception as e:  # pylint: disable=broad-except
            self.logger.error('Error while inferring cluster: %s', str(e))
            return None
