from __future__ import unicode_literals

from rest_framework.exceptions import APIException


class MissingQueryParameter(APIException):
    status_code = 400
    default_detail = 'Missing Query Parameter.'


class DuplicateError(APIException):
    status_code = 400
    default_detail = 'This value count object already exists.'
