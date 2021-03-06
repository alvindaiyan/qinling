# Copyright 2017 Catalyst IT Limited
#
#    Licensed under the Apache License, Version 2.0 (the "License");
#    you may not use this file except in compliance with the License.
#    You may obtain a copy of the License at
#
#        http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS,
#    WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#    See the License for the specific language governing permissions and
#    limitations under the License.

import abc

import six
from stevedore import driver

from qinling import exceptions as exc

ORCHESTRATOR = None


@six.add_metaclass(abc.ABCMeta)
class OrchestratorBase(object):
    """OrchestratorBase interface."""

    @abc.abstractmethod
    def create_pool(self, name, image, **kwargs):
        raise NotImplementedError

    @abc.abstractmethod
    def delete_pool(self, name, **kwargs):
        raise NotImplementedError


def load_orchestrator(conf):
    global ORCHESTRATOR

    if not ORCHESTRATOR:
        try:
            mgr = driver.DriverManager('qinling.orchestrator',
                                       conf.engine.orchestrator,
                                       invoke_on_load=True,
                                       invoke_args=[conf])

            ORCHESTRATOR = mgr.driver
        except Exception as e:
            raise exc.OrchestratorException(
                'Failed to load orchestrator: %s. Error: %s' %
                (conf.engine.orchestrator, str(e))
            )

    return ORCHESTRATOR
