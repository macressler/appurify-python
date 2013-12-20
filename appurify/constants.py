"""
    Copyright 2013 Appurify, Inc
    All rights reserved

    Unless required by applicable law or agreed to in writing, software
    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
    License for the specific language governing permissions and limitations
    under the License.
"""
# Current development version
# Increment this during development as and when desired
# setup.py will use this version to generate new releases
VERSION = (0, 2, 8)
__version__ = '.'.join(map(str, VERSION[0:3])) + ''.join(VERSION[3:])

# Last tagged stable version
# Bump this to match VERSION when dev version is stable for new release
# and also have passed Sencha architect tool integration tests
# This variable is only used by REST API (/client/version/)
STABLE_VERSION = (0, 2, 7)
__stable_version__ = '.'.join(map(str, STABLE_VERSION[0:3])) + ''.join(STABLE_VERSION[3:])

__homepage__ = 'http://appurify.com'
__license__ = 'Commercial'
__description__ = 'Appurify Developer Python Client'
__contact__ = "support@appurify.com"

API_PROTO = "https"             # override using APPURIFY_API_PROTO environment variable
API_HOST = "live.appurify.com"  # APPURIFY_API_HOST
API_PORT = 443                  # APPURIFY_API_PORT

API_POLL_SEC = 15               # test result polled every poll seconds (APPURIFY_API_POLL_DELAY)

API_RETRY_ON_FAILURE = 1        # should client retry API calls in case of non-200 response (APPURIFY_API_RETRY_ON_FAILURE)
API_RETRY_DELAY = 1             # (in seconds) if retry on failure is enabled, interval between each retry (APPURIFY_API_RETRY_DELAY)
API_MAX_RETRY = 3               # if retry on failure is enabled, how many times should client retry (APPURIFY_API_MAX_RETRY)

API_STATUS_BASE_URL = 'https://s3-us-west-1.amazonaws.com/appurify-api-status'
API_STATUS_UP = 1               # aws status page says service is up
API_STATUS_DOWN = 2             # service is down
API_WAIT_FOR_SERVICE = 1

SUPPORTED_TEST_TYPES = [
    'calabash',
    'ocunit',
    'uiautomation',
    'robotium',
    'ios_robot',
    'android_uiautomator',
    'kiwi',
    'cedar',
    'kif',
    'android_calabash',
    'ios_selenium',
    'android_selenium',
    'ios_webrobot',
    'appium',
    'browser_test',
    'appurify_recording',
    'network_headers',
    'ios_sencharobot',
    'android_monkey',
    'calabash_refresh_app',
    'ios_webviewrobot',
    'ios_wpt',
]

NO_TEST_SOURCE = ['ios_robot', 'ios_webrobot', 'browser_test', 'kif', 'kif:google', 'network_headers', 'ios_sencharobot', 'ios_webviewrobot', 'ios_wpt']
NO_APP_SOURCE = ['ios_selenium','android_selenium','ios_webrobot', 'browser_test', 'network_headers', 'ios_webviewrobot', 'ios_wpt']

SUPPORTED_ACTIONS = [
    'access_token_generate',
    'access_token_list',
    'access_token_usage',
    'access_token_validate',
    'devices_list',
    'devices_config',
    'devices_config_list',
    'devices_config_networks_list',
    'tests_list',
    'tests_check_result',
]
