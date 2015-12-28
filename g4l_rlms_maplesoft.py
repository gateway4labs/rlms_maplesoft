# -*-*- encoding: utf-8 -*-*-

import sys
import time
import re
import sys
import urlparse
import json
import datetime
import uuid
import hashlib
import threading
import Queue
import functools
import traceback

from bs4 import BeautifulSoup

from flask.ext.wtf import TextField, PasswordField, Required, URL, ValidationError

from labmanager.forms import AddForm
from labmanager.rlms import register, Laboratory, CacheDisabler
from labmanager.rlms.base import BaseRLMS, BaseFormCreator, Capabilities, Versions

    
def dbg(msg):
    if DEBUG:
        print "[%s]" % time.asctime(), msg
        sys.stdout.flush()

def dbg_lowlevel(msg, scope):
    if DEBUG_LOW_LEVEL:
        print "[%s][%s][%s]" % (time.asctime(), threading.current_thread().name, scope), msg
        sys.stdout.flush()


class MapleSoftAddForm(AddForm):

    DEFAULT_URL = 'http://www.maplesoft.com/products/mobiusproject/studentapps/'
    DEFAULT_LOCATION = 'Waterloo, Canada'
    DEFAULT_PUBLICLY_AVAILABLE = True
    DEFAULT_PUBLIC_IDENTIFIER = 'maplesoft'
    DEFAULT_AUTOLOAD = True

    def __init__(self, add_or_edit, *args, **kwargs):
        super(MapleSoftAddForm, self).__init__(*args, **kwargs)
        self.add_or_edit = add_or_edit

    @staticmethod
    def process_configuration(old_configuration, new_configuration):
        return new_configuration

class MapleSoftFormCreator(BaseFormCreator):

    def get_add_form(self):
        return MapleSoftAddForm

FORM_CREATOR = MapleSoftFormCreator()

MIN_TIME = datetime.timedelta(hours=24)

def retrieve_labs():
    KEY = 'get_laboratories'
    laboratories = MAPLESOFT.cache.get(KEY, min_time = MIN_TIME)
    if laboratories:
        return laboratories

    dbg("get_laboratories not in cache")

    index_html = MAPLESOFT.cached_session.get('http://www.maplesoft.com/products/mobiusproject/studentapps/').text
    soup = BeautifulSoup(index_html, 'lxml')
    laboratories = []
    for lab in soup.findAll(class_="plainlink"):
        link = lab['href']
        if not 'appId=' in link:
            continue
        app_id = link.split('appId=')[1].split('&')[0].split('?')[0]
        name = lab.text
        lab = Laboratory(name = name, laboratory_id = app_id, autoload = True)
        laboratories.append(lab)

    MAPLESOFT.cache[KEY] = laboratories
    return laboratories

class RLMS(BaseRLMS):

    def __init__(self, configuration, *args, **kwargs):
        self.configuration = json.loads(configuration or '{}')

    def get_version(self):
        return Versions.VERSION_1

    def get_capabilities(self):
        return [ Capabilities.WIDGET ]

    def get_laboratories(self, **kwargs):
        return retrieve_labs()

    def reserve(self, laboratory_id, username, institution, general_configuration_str, particular_configurations, request_payload, user_properties, *args, **kwargs):
        url = 'http://maplecloud.maplesoft.com/maplenet/worksheets/maplecloud/view/{0}.mw'.format(laboratory_id)
        response = {
            'reservation_id' : url,
            'load_url' : url
        }
        return response

    def load_widget(self, reservation_id, widget_name, **kwargs):
        url = 'http://maplecloud.maplesoft.com/maplenet/worksheets/maplecloud/view/{0}.mw'.format(reservation_id)
        return {
            'url' : url
        }

    def list_widgets(self, laboratory_id, **kwargs):
        default_widget = dict( name = 'default', description = 'Default widget' )
        return [ default_widget ]

def populate_cache():
    rlms = RLMS("{}")
    dbg("Retrieving labs")
    try:
        rlms.get_laboratories()
    finally:
        dbg("Finished")
        ALL_LINKS = None
        sys.stdout.flush()
        sys.stderr.flush()

MAPLESOFT = register("MapleSoft", ['1.0'], __name__)
MAPLESOFT.add_global_periodic_task('Populating cache', populate_cache, hours = 23)

DEBUG = MAPLESOFT.is_debug() or False
DEBUG_LOW_LEVEL = DEBUG and True

def main():
    rlms = RLMS("{}")
    t0 = time.time()
    laboratories = rlms.get_laboratories()
    tf = time.time()
    print len(laboratories), (tf - t0), "seconds"
    for lab in laboratories[:5]:
        for lang in ('en', 'pt'):
            t0 = time.time()
            print rlms.reserve(lab.laboratory_id, 'tester', 'foo', '', '', '', '', locale = lang)
            tf = time.time()
            print tf - t0, "seconds"
    

if __name__ == '__main__':
    main()