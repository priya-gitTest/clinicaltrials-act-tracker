"""View-related code to customise behaviour of REST Framework to suit
DataTables javascript library (see `site.js`)

See also `custom_rest_views.py`

"""
from collections import OrderedDict
import re

from rest_framework.pagination import LimitOffsetPagination
from rest_framework.filters import OrderingFilter
from rest_framework.filters import SearchFilter
from rest_framework.response import Response

from frontend.models import Ranking
from frontend.models import Trial


class DataTablesPagination(LimitOffsetPagination):
    """Configure REST api pagination to match variable names expected by
    DataTables.

    Read https://datatables.net/manual/server-side for details of
    variables sent by the DataTables widget; and
    http://www.django-rest-framework.org/api-guide/pagination/#limitoffsetpagination
    for details of how the Django REST framework handles pagination.

    """
    default_limit = 300
    limit_query_param = 'length'
    offset_query_param = 'start'

    def paginate_queryset(self, queryset, request, view=None):
        self.total = queryset.count()
        return super().paginate_queryset(queryset, request, view=view)

    def get_paginated_response(self, data):
        return Response(OrderedDict([
            ('recordsFiltered', self.count),
            ('recordsTotal', self.total),
            ('next', self.get_next_link()),
            ('previous', self.get_previous_link()),
            ('results', data)
        ]))


def get_columns(params):
    cols = {}
    for k, v in params.items():
        # Datatables optionally supplies a `name` field...
        match = re.match(r"^columns\[(\d+)\]\[name\]", k)
        if match and match.groups()[0]:
            cols[match.groups()[0]] = v
        else:
            # ...and if that's not present, we should use the `data`
            # field instead
            match = re.match(r"^columns\[(\d+)\]\[data\]", k)
            if match:
                cols[match.groups()[0]] = v
    return cols


def get_datatables_ordering(params):
    orderings = []
    cols = get_columns(params)
    ordering_names = OrderedDict()
    ordering_directions = OrderedDict()
    for k, v in params.items():
        col_match = re.match(r"^order\[(\d+)\]\[column\]", k)
        if col_match:
            ordering_names[col_match.groups()[0]] = cols[v]
        dir_match = re.match(r"^order\[(\d+)\]\[dir\]", k)
        if dir_match:
            ordering_directions[dir_match.groups()[0]] = v
    for k, v in sorted(ordering_names.items(), key=lambda x: x[0]):
        if ordering_directions[k] == 'desc':
            direction = "-"
        else:
            direction = ""
        orderings.append("{}{}".format(direction, v))
    return ",".join(orderings)


class DataTablesOrderingFilter(OrderingFilter):
    # The URL query parameter used for the ordering.
    def get_ordering(self, request, queryset, view):
        """
        Ordering is set by a comma delimited ?ordering=... query parameter.

        The `ordering` query parameter can be overridden by setting
        the `ordering_param` value on the OrderingFilter or by
        specifying an `ORDERING_PARAM` value in the API settings.
        """
        ordering = []
        params = get_datatables_ordering(request.query_params)
        if params:
            fields = [param.strip() for param in params.split(',')]
            ordering = self.remove_invalid_fields(queryset, fields, view, request)
            if ordering:
                return ordering

        # No ordering was included, or all the ordering fields were invalid
        return self.get_default_ordering(view)
