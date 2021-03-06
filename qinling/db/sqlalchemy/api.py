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

import contextlib
import sys
import threading

from oslo_config import cfg
from oslo_db import exception as oslo_db_exc
from oslo_db.sqlalchemy import utils as db_utils
from oslo_log import log as logging
import sqlalchemy as sa

from qinling import context
from qinling.db import base as db_base
from qinling.db.sqlalchemy import filters as db_filters
from qinling.db.sqlalchemy import model_base
from qinling.db.sqlalchemy import models
from qinling import exceptions as exc

CONF = cfg.CONF
LOG = logging.getLogger(__name__)

_SCHEMA_LOCK = threading.RLock()
_initialized = False


def get_backend():
    """Consumed by openstack common code.

    The backend is this module itself.
    :return Name of db backend.
    """
    return sys.modules[__name__]


def setup_db():
    global _initialized

    with _SCHEMA_LOCK:
        if _initialized:
            return

        try:
            models.Function.metadata.create_all(db_base.get_engine())

            _initialized = True
        except sa.exc.OperationalError as e:
            raise exc.DBError("Failed to setup database: %s" % str(e))


def drop_db():
    global _initialized

    with _SCHEMA_LOCK:
        if not _initialized:
            return

        try:
            models.Function.metadata.drop_all(db_base.get_engine())

            _initialized = False
        except Exception as e:
            raise exc.DBError("Failed to drop database: %s" % str(e))


def start_tx():
    db_base.start_tx()


def commit_tx():
    db_base.commit_tx()


def rollback_tx():
    db_base.rollback_tx()


def end_tx():
    db_base.end_tx()


@contextlib.contextmanager
def transaction():
    start_tx()

    try:
        yield
        commit_tx()
    finally:
        end_tx()


def _secure_query(model, *columns):
    query = db_base.model_query(model, columns)

    if not issubclass(model, model_base.QinlingSecureModelBase):
        return query

    query = query.filter(model.project_id == context.get_ctx().projectid)

    return query


def _paginate_query(model, limit=None, marker=None, sort_keys=None,
                    sort_dirs=None, query=None):
    if not query:
        query = _secure_query(model)

    sort_keys = sort_keys if sort_keys else []

    if 'id' not in sort_keys:
        sort_keys.append('id')
        sort_dirs.append('asc') if sort_dirs else None

    query = db_utils.paginate_query(
        query,
        model,
        limit,
        sort_keys,
        marker=marker,
        sort_dirs=sort_dirs
    )

    return query


def _get_collection(model, insecure=False, limit=None, marker=None,
                    sort_keys=None, sort_dirs=None, fields=None, **filters):
    columns = (
        tuple([getattr(model, f) for f in fields if hasattr(model, f)])
        if fields else ()
    )

    query = (db_base.model_query(model, *columns) if insecure
             else _secure_query(model, *columns))
    query = db_filters.apply_filters(query, model, **filters)

    query = _paginate_query(
        model,
        limit,
        marker,
        sort_keys,
        sort_dirs,
        query
    )

    try:
        return query.all()
    except Exception as e:
        raise exc.DBError(
            "Failed when querying database, error type: %s, "
            "error message: %s" % (e.__class__.__name__, str(e))
        )


def _get_collection_sorted_by_time(model, insecure=False, fields=None,
                                   sort_keys=['created_at'], **kwargs):
    return _get_collection(
        model=model,
        insecure=insecure,
        sort_keys=sort_keys,
        fields=fields,
        **kwargs
    )


def _get_db_object_by_id(model, id, insecure=False):
    query = db_base.model_query(model) if insecure else _secure_query(model)

    return query.filter_by(id=id).first()


@db_base.session_aware()
def get_function(id):
    pass


@db_base.session_aware()
def get_functions(limit=None, marker=None, sort_keys=None,
                  sort_dirs=None, fields=None, **kwargs):
    pass


@db_base.session_aware()
def create_function(values, session=None):
    func = models.Function()
    func.update(values.copy())

    try:
        func.save(session=session)
    except oslo_db_exc.DBDuplicateEntry as e:
        raise exc.DBError(
            "Duplicate entry for Function: %s" % e.columns
        )

    return func


@db_base.session_aware()
def update_function(id, values):
    pass


@db_base.session_aware()
def delete_function(id):
    pass


@db_base.session_aware()
def create_runtime(values, session=None):
    runtime = models.Runtime()
    runtime.update(values.copy())

    try:
        runtime.save(session=session)
    except oslo_db_exc.DBDuplicateEntry as e:
        raise exc.DBError(
            "Duplicate entry for Runtime: %s" % e.columns
        )

    return runtime


@db_base.session_aware()
def get_runtime(id, session=None):
    runtime = _get_db_object_by_id(models.Runtime, id)

    if not runtime:
        raise exc.DBEntityNotFoundError("Runtime not found [id=%s]" % id)

    return runtime


@db_base.session_aware()
def get_runtimes(session=None, **kwargs):
    return _get_collection_sorted_by_time(models.Runtime, **kwargs)


@db_base.session_aware()
def delete_runtime(id, session=None):
    runtime = get_runtime(id)

    session.delete(runtime)
