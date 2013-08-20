"""
    Copyright 2013 Appurify, Inc
    All rights reserved

    Unless required by applicable law or agreed to in writing, software
    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
    License for the specific language governing permissions and limitations
    under the License.
"""
import os
import sys
import platform
import requests
import time
import urllib
import logging

from . import constants

logging.basicConfig(level=logging.WARNING, format='[%(asctime)s] [%(process)d] %(message)s')

def log(msg, level=None): # pragma: no cover
    """simple logging facility"""
    logging.log(level if level else logging.WARNING, msg)

def url(resource): # pragma: no cover
    """(defaults: https://live.appurify.com:443/resource/)
    
    Url can be overridden by specifying following environment variables
    APPURIFY_API_PROTO (default: https)
    APPURIFY_API_HOST (default: live.appurify.com)
    APPURIFY_API_PORT (default: 443)
    
    Clients and Customers MUST not override this unless instructed by Appurify devs
    """
    return '/'.join(['%s://%s:%s/resource' % (
        os.environ.get('APPURIFY_API_PROTO', constants.API_PROTO), 
        os.environ.get('APPURIFY_API_HOST', constants.API_HOST), 
        os.environ.get('APPURIFY_API_PORT', str(constants.API_PORT))
    ), resource]) + '/'

def user_agent(): # pragma: no cover
    """returns string representation of user-agent"""
    implementation = platform.python_implementation()
    
    if implementation == 'CPython':
        version = platform.python_version()
    elif implementation == 'PyPy':
        version = '%s.%s.%s' % (sys.pypy_version_info.major, sys.pypy_version_info.minor, sys.pypy_version_info.micro)
    elif implementation == 'Jython':
        version = platform.python_version()
    elif implementation == 'IronPython':
        version = platform.python_version()
    else:
        version = 'Unknown'
    
    try:
        system = platform.system()
        release = platform.release()
    except IOError:
        system = 'Unknown'
        release = 'Unknown'
    
    return " ".join([
        'appurify-client/%s' % constants.__version__,
        'python-requests/%s' % requests.__version__,
        '%s/%s' % (implementation, version),
        '%s/%s' % (system, release)
    ])

def get(resource, params, retry_count=0, retry=True): # pragma: no cover
    """make a HTTP GET request on API endpoint"""
    log("HTTP GET %s" % url(resource))
    response = requests.get(url(resource), params=params, verify=False, headers={'User-Agent': user_agent()})
    if retry and response.status_code != 200 and \
        int(os.environ.get('APPURIFY_API_RETRY_ON_FAILURE', constants.API_RETRY_ON_FAILURE)) == 1 and \
        retry_count < int(os.environ.get('APPURIFY_API_MAX_RETRY', constants.API_MAX_RETRY)):
        time.sleep(int(os.environ.get('APPURIFY_API_RETRY_DELAY', constants.API_RETRY_DELAY)))
        retry_count += 1
        return get(resource, params, retry_count, retry)
    else:
        return response

def post(resource, data, files=None, retry_count=0, retry=True): # pragma: no cover
    """make a HTTP POST request on API endpoint"""
    log("HTTP POST %s" % url(resource))
    response = requests.post(url(resource), data=data, files=files, verify=False, headers={'User-Agent': user_agent()})
    if retry and response.status_code != 200 and \
        int(os.environ.get('APPURIFY_API_RETRY_ON_FAILURE', constants.API_RETRY_ON_FAILURE)) == 1 and \
        retry_count < int(os.environ.get('APPURIFY_API_MAX_RETRY', constants.API_MAX_RETRY)):
        time.sleep(int(os.environ.get('APPURIFY_API_RETRY_DELAY', constants.API_RETRY_DELAY)))
        retry_count += 1
        return post(resource, data, files, retry_count, retry)
    else:
        return response

def wget(url, path): # pragma: no cover
    """Download a file to specified path"""
    urllib.urlretrieve(url, path)
