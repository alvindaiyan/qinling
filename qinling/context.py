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

from oslo_config import cfg
from oslo_context import context as oslo_context
import pecan
from pecan import hooks

from qinling import exceptions as exc
from qinling.utils import thread_local

CONF = cfg.CONF

ALLOWED_WITHOUT_AUTH = ['/', '/v1/']

CTX_THREAD_LOCAL_NAME = "QINLING_APP_CTX_THREAD_LOCAL"

DEFAULT_PROJECT_ID = "<default-project>"


def authenticate(req):
    # Refer to:
    # https://docs.openstack.org/developer/keystonemiddleware/middlewarearchitecture.html#exchanging-user-information
    identity_status = req.headers.get('X-Identity-Status')
    service_identity_status = req.headers.get('X-Service-Identity-Status')

    if (identity_status == 'Confirmed' or
            service_identity_status == 'Confirmed'):
        return

    if req.headers.get('X-Auth-Token'):
        msg = 'Auth token is invalid: %s' % req.headers['X-Auth-Token']
    else:
        msg = 'Authentication required'

    raise exc.UnauthorizedException(msg)


class AuthHook(hooks.PecanHook):
    def before(self, state):
        if state.request.path in ALLOWED_WITHOUT_AUTH:
            return

        if not CONF.pecan.auth_enable:
            return

        try:
            authenticate(state.request)
        except Exception as e:
            msg = "Failed to validate access token: %s" % str(e)

            pecan.abort(
                status_code=401,
                detail=msg,
                headers={'Server-Error-Message': msg}
            )


def has_ctx():
    return thread_local.has_thread_local(CTX_THREAD_LOCAL_NAME)


def get_ctx():
    if not has_ctx():
        raise exc.ApplicationContextNotFoundException()

    return thread_local.get_thread_local(CTX_THREAD_LOCAL_NAME)


def set_ctx(new_ctx):
    thread_local.set_thread_local(CTX_THREAD_LOCAL_NAME, new_ctx)


class Context(oslo_context.RequestContext):
    _session = None

    def __init__(self, is_admin=False, **kwargs):
        super(Context, self).__init__(is_admin=is_admin, **kwargs)

    @property
    def projectid(self):
        if CONF.pecan.auth_enable:
            return self.project_id
        else:
            return DEFAULT_PROJECT_ID


class ContextHook(hooks.PecanHook):
    def before(self, state):
        context_obj = Context.from_environ(state.request.environ)
        set_ctx(context_obj)

    def after(self, state):
        set_ctx(None)
