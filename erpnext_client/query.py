import datetime
import json
import logging
import requests

from werkzeug.exceptions import NotFound, BadRequest

LOGGER = logging.getLogger(__name__)

def renew_login_if_expired(function):
    """
    Send a new authentication request if login has expired.
    """
    def wrapper(instance, *args, **kwargs):
        if instance._login_in_progress is False:
            if instance._next_login <= datetime.datetime.now():
                instance.login()

        return function(instance, *args, **kwargs)

    return wrapper


class ERPNextClient:
    def __init__(self, host, api_key, api_secret):
        self.host = host
        self.api_key = api_key
        self.api_secret = api_secret

        self.headers = {
            'Accept': 'application/json',
            'Authorization': 'token {0}:{1}'.format(self.api_key,
                                                    self.api_secret)
        }

        self.session = requests.Session()
        self.session.headers.update(self.headers)

        self._login_in_progress = False
        self._next_login = None

        self.api_root = "https://{0}/api/".format(self.host)

    def _put(self, path, data={}):
        if data is not None:
            LOGGER.debug("PUT payload: {0}".format(data))

        r = self.session.put("{0}{1}".format(self.api_root,
                                             path),
                              json=data)

        if r.status_code != requests.codes.ok:
            r.raise_for_status()

        return r

    def _delete(self, path, data={}):
        LOGGER.debug("DELETE {0} with payload: {0}".format(path, data))

        r = self.session.delete("{0}{1}".format(self.api_root,
                                             path),
                                json=data)

        if r.status_code != requests.codes.ok:
            r.raise_for_status()

        return r


    def _post(self, path, data={}):
        if data is not {}:
            LOGGER.debug("POST payload: {0}".format(data))

        r = self.session.post("{0}{1}".format(self.api_root,
                                              path),
                              json=data)

        if r.status_code != requests.codes.ok:
            raise BadRequest(r.json())
            # r.raise_for_status()

        return r

    def _get(self, path, params={}):
        r = self.session.get("{0}{1}".format(self.api_root,
                                             path),
                             params=params)
        if r.status_code != requests.codes.ok:
            r.raise_for_status()

        return r

    def login(self):
        self._login_in_progress = True
        r = self._get("method/frappe.auth.get_logged_user")

        success = r.status_code == requests.codes.ok

        if success:
            self._next_login = datetime.datetime.now() + datetime.timedelta(hours=1)

        self._login_in_progress = False
        return success

    def get_credentials(self):
        r = self._get("method/frappe.auth.get_logged_user")
        if r.status_code == requests.codes.ok:
            return r.json()
        else:
            return None

    def query(self, aERPResource):
        return aERPResource(self)

    def list_resource(self, resource_type_name, fields=[], filters=[], parent=None, page_length=None):
        params = {"fields": json.dumps(fields),
                  "filters": json.dumps(filters),
                  "limit_page_length": page_length}

        if parent is not None:
            params.update({"parent": parent})

        return self._get("resource/{0}".format(resource_type_name), params)

    def get_resource(self, resource_type_name, resource_name, fields=[], filters=[], parent=None):
        params = {"fields": fields,
                  "filters": json.dumps(filters)}

        if parent is not None:
            params.update({"parent": parent})

        return self._get("resource/{0}/{1}".format(resource_type_name,
                                                   resource_name),
                         params=params)

    def update_resource(self, resource_type_name, resource_name, data):
        encapsulated_data = {"data": json.dumps(data)}
        LOGGER.debug("Updating resource <{0}:{1}> with payload <{2}>".format(resource_type_name,
                                                                             resource_name,
                                                                             data))
        return self._put("resource/{0}/{1}".format(resource_type_name, resource_name),
                         encapsulated_data)

    def delete_resource(self, resource_type_name, resource_name, data={}):
        encapsulated_data = {"data": json.dumps(data)}
        LOGGER.debug("DELETING resource <{0}:{1}> with payload <{2}>".format(resource_type_name,
                                                                             resource_name,
                                                                             data))
        return self._delete("resource/{0}/{1}".format(resource_type_name, resource_name),
                            encapsulated_data)



    def create_resource(self, resource_type_name, data):
        encapsulated_data = {"data": json.dumps(data)}
        return self._post("resource/{0}".format(resource_type_name),
                          encapsulated_data)

    def create_sales_order(self, customer, items, title=None, order_type="Sales", naming_series="SO-"):
        return self.create_resource("Sales Order",
                                    data={'customer': customer,
                                          'title': title,
                                          'naming_series': naming_series,
                                          'rounded_total': 0,
                                          'order_type': order_type,
                                          'items': items})
