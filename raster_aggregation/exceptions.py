from __future__ import unicode_literals

from rest_framework.exceptions import APIException


class MissingQueryParameter(APIException):
    status_code = 400
    default_detail = 'Missing Query Parameter.'


class DuplicateError(APIException):
    status_code = 400
    default_detail = 'A value count object with this properties already exists.'
