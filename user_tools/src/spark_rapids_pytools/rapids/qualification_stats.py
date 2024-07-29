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

"""Implementation class representing wrapper around the Qualification Stats tool."""

from dataclasses import dataclass

from spark_rapids_pytools.cloud_api.sp_types import get_platform
from spark_rapids_pytools.common.utilities import Utils
from spark_rapids_pytools.rapids.tool_ctxt import ToolContext
from spark_rapids_pytools.rapids.rapids_tool import RapidsTool
from spark_rapids_tools.tools.qualification_stats_report import SparkQualificationStats


@dataclass
class SparkQualStats(RapidsTool):

    """
    Wrapper layer around Qualification Stats Tool.

    Attributes
    ----------
    config_path : str
        Path to the qualification configuration file.
    output_folder : str
        Path to the output folder to save the results.
    qual_output: str
        Path to a directory containing qualification tool output.
    """
    config_path: str = None
    output_folder: str = None
    qual_output: str = None

    name = 'stats'

    def _init_ctxt(self):
        """
        Initialize the tool context, reusing qualification configurations.
        TODO: This should be refactor to use it's own conf file if not provided by the user.
        """
        if self.config_path is None:
            self.config_path = Utils.resource_path('qualification-conf.yaml')
        self.ctxt = ToolContext(platform_cls=get_platform(self.platform_type),
                                platform_opts=self.wrapper_options.get('platformOpts'),
                                prop_arg=self.config_path,
                                name=self.name)

    def _run_rapids_tool(self):
        """
        Runs the Qualification Stats tool.
        """
        try:
            self.logger.info('Running Qualification Stats tool')
            result = SparkQualificationStats(ctxt=self.ctxt, qual_output=self.qual_output)
            result.report_qualification_stats()
            self.logger.info('Qualification Stats tool completed successfully')
        except Exception as e:  # pylint: disable=broad-except
            self.logger.error('Error running Qualification Stats tool %s', e)

    def _collect_result(self):
        pass

    def _archive_phase(self):
        pass

    def _finalize(self):
        pass