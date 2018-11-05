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

from flask import Blueprint, url_for
from flask.ext.wtf import TextField, PasswordField, Required, URL, ValidationError

from labmanager.forms import AddForm
from labmanager.rlms import register, Laboratory, CacheDisabler, register_blueprint
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
    for lab in soup.findAll("a"):
        if not lab.text:
            continue 

        if 'application.jsp?appId=' not in (lab.get('href', '') or ''):
            continue

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
        return [ Capabilities.WIDGET, Capabilities.URL_FINDER, Capabilities.CHECK_URLS ]

    def get_base_urls(self):
        return [ 'http://maplecloud.maplesoft.com/', 'https://maple.cloud/#doc=' ]

    def get_lab_by_url(self, url):
        if url.startswith('https://maple.cloud/#doc='):
            identifier = url.split('=')[1].split('&')[0].split(';')[0]
        elif url.startswith('http://maplecloud.maplesoft.com/maplenet/worksheets/maplecloud/view/'):
            identifier = url.split('/view/')[1].split('.')[0]
        elif url.startswith('http://maplecloud.maplesoft.com/application.jsp?appId='):
            identifier = url.split('appId=')[1].split('&')[0]
        else:
            return None

        for lab in retrieve_labs():
            if unicode(lab.laboratory_id) == identifier:
                return lab

        return None

    def get_check_urls(self, laboratory_id):
        url = 'https://maple.cloud/downloadDocument?id={0}&version=&cloudToken='.format(laboratory_id)
        return [ url ]

    def get_laboratories(self, **kwargs):
        return retrieve_labs()

    def reserve(self, laboratory_id, username, institution, general_configuration_str, particular_configurations, request_payload, user_properties, *args, **kwargs):
        url = url_for('maplesoft.maple_get', identifier=laboratory_id, _external=True) 
        response = {
            'reservation_id' : url,
            'load_url' : url
        }
        return response

    def load_widget(self, reservation_id, widget_name, **kwargs):
        return {
            'url' : reservation_id
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
MAPLESOFT.add_global_periodic_task('Populating cache', populate_cache, hours = 17)

maplesoft_blueprint = Blueprint('maplesoft', __name__)

@maplesoft_blueprint.route('/id/<identifier>')
def maple_get(identifier):
    return """<html>
<body onload='submitForm()'>
<form id='maple-form' action='https://maplenet.cloud/maplenet/worksheet/open' method='POST'>
    <input type='hidden' name='documentUrl' value='https://maple.cloud/downloadDocument?id=%(IDENTIFIER)s&version=&cloudToken='>
</form>
<script>
    function submitForm() {
        document.getElementById('maple-form').submit();
    }
</script>
</body>
</html>""" % { 'IDENTIFIER': identifier }

register_blueprint(maplesoft_blueprint, url='/maplesoft')

DEBUG = MAPLESOFT.is_debug() or False
DEBUG_LOW_LEVEL = DEBUG and True

def main():
    from labmanager.rlms.caches import CacheDisabler
    with CacheDisabler():
        rlms = RLMS("{}")
        t0 = time.time()
        laboratories = rlms.get_laboratories()
        tf = time.time()
        print 
        msg = "%s laboratories in %.2f seconds" % (len(laboratories), (tf - t0))
        print msg
        print "*" * len(msg)
        print 
        for lab in laboratories[:5]:
            for lang in ('en', 'pt'):
                print "Reserving:", lab, "in",lang
                t0 = time.time()
                print rlms.reserve(lab.laboratory_id, 'tester', 'foo', '', '', '', '', locale = lang)
                tf = time.time()
                print tf - t0, "seconds"
    

if __name__ == '__main__':
    main()
