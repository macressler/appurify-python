"""
    Copyright 2013 Appurify, Inc
    All rights reserved

    Unless required by applicable law or agreed to in writing, software
    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
    License for the specific language governing permissions and limitations
    under the License.
"""
import argparse
import json
import os
import sys
import time
import pprint
import inspect

from . import constants
from .utils import log, get, post, wget

####################
## Access Token API
####################

def access_token_generate(api_key, api_secret, access_token_tag=None):
    """Generate an access token, given an api key and secret"""
    data = {'key': api_key, 'secret': api_secret}
    if type(access_token_tag) == list: data['tags'] = access_token_tag
    return post('access_token/generate', data)

def access_token_list(api_key, api_secret, page_no=1, page_size=10):
    """Retrieve a list of access tokens for a particular key/secret pair"""
    return get('access_token/list', {'key':api_key, 'secret':api_secret, 'page_no':page_no, 'page_size':page_size})

def access_token_usage(api_key, api_secret, access_token, page_no=1, page_size=10):
    """ DEPRECATED. Will be removed in future versions.
    Get details on device time used for a particular key/secret pair
    """
    return get('access_token/usage', {'key':api_key, 'secret':api_secret, 'access_token':access_token, 'page_no':page_no, 'page_size':page_size})

def access_token_validate(access_token):
    """Verify that an access token is valid and retrieve the remaining ttl for that token"""
    return post('access_token/validate', {'access_token':access_token})

##############
## Device API
##############

def devices_list(access_token):
    """Get list of devices"""
    return get('devices/list', {'access_token':access_token})

def devices_config_list(access_token):
    """Get available configuration option for devices"""
    return get('devices/config/list', {'access_token':access_token})

# TODO: access configuration parameters and pass it on
def devices_config(access_token, device_id):
    """Fetch configuration of specific device id"""
    return post('devices/config', {'access_token':access_token, 'device_id':device_id})

def devices_config_networks_list(access_token):
    return get('devices/config/networks/list', {'access_token':access_token})

###########
## App API
###########

def apps_list(access_token):
    return get('apps/list', {'access_token':access_token})

def apps_upload(access_token, source, source_type, type=None, name=None):
    files = None if source_type == 'url' else {'source':source}
    data = {'access_token':access_token, 'source_type':source_type}
    if source_type == 'url': data['source'] = source
    if type: data['app_test_type'] = type
    if name: data['name'] = name
    return post('apps/upload', data, files)

############
## Test API
############

def tests_list(access_token):
    return get('tests/list', {'access_token':access_token})

def tests_upload(access_token, source, source_type, type, app_id = None):
    files = None if source_type == 'url' else {'source':source}
    data = {'access_token':access_token, 'source_type':source_type, 'test_type': type}
    if app_id:
        data['app_id'] = app_id
    if source_type == 'url': data['source'] = source
    return post('tests/upload', data, files)

def tests_run(access_token, device_type_id, app_id, test_id, device_id=None):
    return post('tests/run', {'access_token':access_token, 'device_type_id':device_type_id, 'app_id':app_id, 'test_id':test_id, 'device_id':device_id, 'async': '1'})

def tests_check_result(access_token, test_run_id):
    return get('tests/check', {'access_token':access_token, 'test_run_id': test_run_id})

###################
## Config file API
###################

def config_upload(access_token, source, test_id):
    """Upload a configuration file to associate with a test."""
    data, files = {'access_token':access_token, 'test_id': test_id}, {'source':source}
    return post('tests/config/upload', data, files)

##########################
## Post processing
##########################

def print_single_test_response(test_response):
    try:
        for response_type in ['output', 'errors', 'exception', 'number_passes', 'number_fails']:
            response_text = test_response[response_type]
            log("Test %s: %s" % (response_type, response_text))

        response_pass = test_response['pass']
        if response_pass:
            log("All tests passed!")
        else:
            log("There were test failures")

        results_url = test_response['url']
        log("Detailed results url: %s" % results_url)
    except Exception as e:
        log("Error printing test results: %r" % e)

def download_test_response(results_url, result_dir):
    try:
        if not os.path.exists(result_dir):
            log("Attempting to create directory %s" % result_dir)
            os.makedirs(result_dir)
        if result_dir:
            result_path = result_dir + '/' + 'results.zip'
            log("Saving results to %s" % result_path)
            wget(results_url, result_path)
    except Exception as e:
        log("Error downloading test result file: %s" % e)

def print_multi_test_responses(test_response):
    for result in test_response:
        log("Device Type %s result:" % result['device_type'])
        print_single_test_response(result["results"])
        log("\n")

def download_multi_test_response(test_response, result_dir):
    for result in test_response:
        try:
            result_url = result['results']['url']
            device_type_id = result['device_type_id']
            device_result_path = result_dir + "/device_type_%s" % device_type_id
            download_test_response(result_url, device_result_path)
        except Exception as e:
            log("Error downloading test response: %s" % e)

##########################
## Command line utilities
##########################

class AppurifyClientError(Exception):
    pass

class AppurifyClient():

    def __init__(self, *args, **kwargs):
        self.args = kwargs

        self.access_token = self.args.get('access_token', None)
        self.timeout = self.args.get('timeout_sec', None) or int(os.environ.get('APPURIFY_API_TIMEOUT', constants.API_TIMEOUT_SEC))
        self.poll_every = self.args.get('poll_every', None) or os.environ.get('APPURIFY_API_POLL_DELAY', constants.API_POLL_SEC)

        self.test_type = self.args.get('test_type' or None)
        self.device_type_id = self.args.get('device_type_id', None)
        self.device_id = self.args.get('device_id', None)

    def refreshAccessToken(self):
        if self.access_token is None:
            api_key = self.args.get('api_key', None)
            api_secret = self.args.get('api_secret',None)
            if api_key is None or api_secret is None:
                raise AppurifyClientError("Either access_token or api_key and api_secret are required parameters")
            log('generating access token...')
            r = access_token_generate(api_key, api_secret)
            if r.status_code == 200:
                access_token = r.json()['response']['access_token']
                log('access_token_generate success, access_token:%s' % access_token)
                self.access_token = access_token
            else:
                raise AppurifyClientError('access_token_generate failed with response %s' % r.text)
        return self.access_token

    def uploadApp(self):
        log('uploading app file...')
        app_src_type = self.args.get('app_src_type', None)
        app_src = self.args.get('app_src', None)
        app_name = self.args.get('name', None)
        if app_src is None and self.test_type in constants.NO_APP_SOURCE:
            r = apps_upload(self.access_token, None, 'url', self.test_type, name=app_name)
        else:
            if app_src is None:
                raise AppurifyClientError("app src is required for test type %s" % self.test_type)
            if app_src_type != 'url':
                with open(app_src, 'rb') as app_file_source:
                    r = apps_upload(self.access_token, app_file_source, app_src_type, app_src_type, app_name)
            else:
                r = apps_upload(self.access_token, app_src, app_src_type, app_src_type, app_name)
        if r.status_code == 200:
            app_id = r.json()['response']['app_id']
            log('apps_upload success, app_id:%s' % app_id)
            return app_id
        else:
            raise AppurifyClientError('apps_upload failed with response %s' % r.text)

    def uploadTest(self, app_id):
        log('uploading test file...')
        test_src_type = self.args.get('test_src_type', None)
        test_src = self.args.get('test_src', None)
        if not test_src and self.test_type not in constants.NO_TEST_SOURCE:
            raise AppurifyClientError('test_type %s requires a test source' % self.test_type)
        if test_src:
            if test_src_type != 'url':
                with open(test_src, 'rb') as test_file_source:
                    r = tests_upload(self.access_token, test_file_source, test_src_type, self.test_type, app_id=app_id)
            else:
                r = tests_upload(self.access_token, test_src, test_src_type, self.test_type, app_id=app_id)
        elif self.test_type in constants.NO_TEST_SOURCE:
            r = tests_upload(self.access_token, None, 'url', self.test_type)
        if r.status_code == 200:
            test_id = r.json()['response']['test_id']
            log('tests_upload success, test_id:%s' % test_id)
            return test_id
        else:
            raise AppurifyClientError('tests_upload failed with response %s' % r.text)

    def uploadConfig(self, test_id, config_src):
        log('uploading config file...')
        with open(config_src, 'rb') as config_src_file:
            r = config_upload(self.access_token, config_src_file, test_id)
            if r.status_code == 200:
                log('config file upload success, test_id:%s' % test_id)
                config_id = r.json()['response']['config_id']
                return config_id
            else:
                raise AppurifyClientError('config file upload  failed with response %s' % r.text)

    def runTest(self, app_id, test_id):
        r = tests_run(self.access_token, self.device_type_id, app_id, test_id, self.device_id)
        if r.status_code == 200:
            test_response = r.json()['response']
            test_run_id = test_response['test_run_id']
            log('tests_run success scheduling test test_run_id:%s' % test_run_id)

            try:
                configs = [test_response['config']]
            except:
                try:
                    configs = map(lambda x: x['config'], test_response['test_runs'])
                except:
                    configs = []
            return (test_run_id, configs)
        else:
            raise AppurifyClientError('runTest failed scheduling test with response %s' % r.text)

    def printConfigs(self, configs):
        if configs:
            found_config = False
            print "== Test will run with the following device configurations =="
            for config in configs:
                if config:
                    found_config = True
                    print json.dumps(config, sort_keys=True,indent=4, separators=(',', ': '))
            if not found_config:
                print "Default"
            print "== End device configurations =="

    def pollTestResult(self, test_run_id):
        test_status = None
        runtime = 0

        while test_status != 'complete' and runtime < self.timeout:
            time.sleep(self.poll_every)
            r = tests_check_result(self.access_token, test_run_id)
            test_status_response = r.json()['response']
            test_status = test_status_response['status']
            if test_status == 'complete':
                test_response = test_status_response['results']
                log("**** COMPLETE - JSON SUMMARY FOLLOWS ****")
                log(json.dumps(test_response))
                log("**** COMPLETE - JSON SUMMARY ENDS ****")
                return test_status_response
            else:
                log("%s sec elapsed" % str(runtime))
                if 'message' in test_status_response:
                    log(test_status_response['message'])
                log("Test progress: {}".format(test_status_response.get('detailed_status', 'status-unavailable')))
            runtime = runtime + self.poll_every

        raise AppurifyClientError("Test result poll timed out after %s seconds" % self.timeout)


    def reportTestResult(self, test_status_response):
        test_response = test_status_response['results']
        result_dir = self.args.get('result_dir', None)
        if 'complete_count' in test_status_response:
            print_multi_test_responses(test_response)
            if result_dir:
                download_multi_test_response(test_response, result_dir)
        else:
            print_single_test_response(test_response)
            if result_dir:
                result_url = test_response['url']
                download_test_response(result_url, result_dir)

        if 'pass' in test_status_response:
            all_pass = test_status_response['pass']
        elif 'pass' in test_response:
            all_pass = test_response['pass']
        else:
            all_pass = False
        return all_pass

    def main(self):
        """
        Returns 0 if all tests run with no errors
        Returns 1 otherwise
        """
        exit_code = 0

        try:
            self.refreshAccessToken()

            if self.test_type is None:
                raise AppurifyClientError("test_type is required")

            # upload app/test of use passed id's
            app_id = self.args.get('app_id', None) or self.uploadApp()
            test_id = self.args.get('test_id', None) or self.uploadTest(app_id)
            config_src = self.args.get('config_src', False)
            if config_src:
                self.uploadConfig(test_id, config_src)
            # start test run
            test_run_id, configs = self.runTest(app_id, test_id)
            self.printConfigs(configs)

            # poll for results and print report
            test_status_response = self.pollTestResult(test_run_id)
            all_pass = self.reportTestResult(test_status_response)

            if not all_pass:
                exit_code = 1
        except AppurifyClientError, e:
            log(str(e))
            exit_code = 1

        log('done with exit code %s' % exit_code)
        return exit_code

def execute(action, kwargs, required):
    """Execute a particular action and prints received response."""
    os.environ['APPURIFY_API_RETRY_ON_FAILURE'] = '0' #disable retries
    pp = pprint.PrettyPrinter(indent=4)
    r = globals()[action](**{k : v for k,v in kwargs.iteritems() if k in required})
    pp.pprint(r.json())
    return 0 if r.status_code == 200 else 1

def init():
    parser = argparse.ArgumentParser(
        description='Appurify developer REST API client v%s' % constants.__version__,
        epilog='Email us at %s for further information' % constants.__contact__
    )

    parser.add_argument('--api-key', help='Appurify developer key')
    parser.add_argument('--api-secret', help='Appurify developer secret')
    parser.add_argument('--access-token-tag', action='append', help='colon separated key:value tag for access_token to be generated')
    parser.add_argument('--access-token', help='Specify to use this access token instead of generating a new one')

    parser.add_argument('--app-src', help='Path or Url of app file to upload')
    parser.add_argument('--app-id', help='Specify to use previously uploaded app file')

    parser.add_argument('--test-src', help='Path or Url of test file to upload')
    parser.add_argument('--test-type', help='Type of test being uploaded')
    parser.add_argument('--test-id', help='Specify to use previously uploaded test file')

    parser.add_argument('--device-type-id', help='Device type to reserve and run tests upon (you may run tests on multiple devices by using a comma separated list of device IDs)')
    parser.add_argument('--device-id', help='Specify to use a particular device')

    parser.add_argument('--config-src', help='Path of additional configuration to add to test')
    parser.add_argument('--result-dir', help='Path to save downloaded results to')
    parser.add_argument('--action', help='Specific API to call (default: main)')

    parser.add_argument('--name', help='Optional, the name of the app to display')

    kwargs = {}
    args = parser.parse_args()

    # (optional) when 'main' is the requested action
    # (required) when 'devices_config' is the requested action
    kwargs['device_id'] = args.device_id

    # (required) access_token || api_key && api_secret
    # (optional) access_token_tag
    if args.access_token == None and (args.api_key == None or args.api_secret == None):
        parser.error('--access-token OR --api-key and --api-secret is required')

    kwargs['api_key'] = args.api_key
    kwargs['api_secret'] = args.api_secret
    kwargs['access_token'] = args.access_token
    kwargs['access_token_tag'] = args.access_token_tag

    # (optional)
    if args.action:
        if args.action in constants.SUPPORTED_ACTIONS:
            argspec = inspect.getargspec(globals()[args.action])
            required = argspec[0] if not argspec[3] else argspec[0][: -1 * len(argspec[3])]
            for k in required:
                if not k in kwargs or not kwargs[k]:
                    parser.error('"%s" action requires following parameters: %s. "%s" not found.' % (args.action, ", ".join(required), k))
            sys.exit(execute(args.action, kwargs, required))
        else:
            parser.error('"%s" action is not supported. Available options are: %s' % (args.action, ", ".join(constants.SUPPORTED_ACTIONS)))

    # (required) app_id || app_src
    # (optional) app_test_type
    # (calculated) app_src_type
    if args.app_id is None and args.app_src is None and args.test_type not in constants.NO_APP_SOURCE:
        parser.error('--app-id OR --app-src is required')

    kwargs['app_id'] = args.app_id
    kwargs['app_src'] = args.app_src

    if args.app_src:
        if args.app_src[0:4] == 'http':
            kwargs['app_src_type'] = 'url'
        else:
            try:
                with open(args.app_src) as _: pass
                kwargs['app_src_type'] = 'raw'
            except:
                parser.error('--app-src %s could not be found' % args.app_src)

    # (required) test_id || test_src && test_type
    if args.test_id == None and (args.test_src == None or args.test_type == None) and args.test_type not in constants.NO_TEST_SOURCE:
        parser.error('--test-id OR --test-src and --test-type is required')

    kwargs['test_id'] = args.test_id
    kwargs['test_type'] = args.test_type
    kwargs['test_src'] = args.test_src
    if args.test_type not in constants.SUPPORTED_TEST_TYPES:
        parser.error('--test-type must be one of the following: %s' % ', '.join(constants.SUPPORTED_TEST_TYPES))

    # (calculated) test_src_type
    if args.test_src:
        if args.test_src[0:4] == 'http':
            kwargs['test_src_type'] = 'url'
        else:
            try:
                with open(args.test_src) as _: pass
                kwargs['test_src_type'] = 'raw'
            except:
                parser.error('--test-src %s could not be found' % args.test_src)

    # (optional) config_src
    if args.config_src != None:
        kwargs['config_src'] = args.config_src

    # (required) device_type_id
    kwargs['device_type_id'] = args.device_type_id

    # (optional) result_dir
    kwargs['result_dir'] = args.result_dir

    # (optional) app name
    kwargs['name'] = args.name

    client = AppurifyClient(**kwargs)
    sys.exit(client.main())

if __name__ == '__main__':
    init()
