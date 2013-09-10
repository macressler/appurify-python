"""
Copyright 2013 Appurify, Inc
All rights reserved
    
Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
License for the specific language governing permissions and limitations
under the License.

To run tests:
from parent directory of tests:
python -m unittest tests.test_client
"""
import unittest
import json
import mock
from appurify.client import AppurifyClient, AppurifyClientError

class TestObject(object):
    pass

def mockRequestObj(response_obj, status_code=200):
    r = TestObject()
    r.headers = {'x-api-server-hostname': 'django-01'}
    r.text = json.dumps(response_obj)
    r.status_code = status_code
    r.json = lambda: response_obj
    return r

def mockRequestPost(url, data, files=None, verify=False, headers={'User-Agent': 'MockAgent'}):
    if 'access_token/generate' in url:
        return mockRequestObj({"meta": {"code": 200}, "response": {"access_token": "test_access_token", "ttl": 86400}})
    if 'apps/upload' in url:
        name = data.get('name', None)
        return mockRequestObj({"meta": {"code": 200}, 
                               "response": {"_id_": None, 
                                            "uploaded_on": "2013-09-09T21:25:24Z", 
                                            "name": name, 
                                            "app_group_id": None, 
                                            "test_type": "test_test_type", 
                                            "size": None, 
                                            "app_group": "None", 
                                            "id": 12345, 
                                            "app_id": "test_app_id"}})
    if 'tests/upload' in url:
        return mockRequestObj({"meta": {"code": 200}, 
                               "response": {"uploaded_on": "2013-09-09T22:30:51Z", 
                                            "name": "use_bdd_tests.zip", "ttl": 86400,
                                             "config": None, 
                                             "test_type": "uiautomation",
                                             "test_id": "test_test_id", 
                                              "expired": False, 
                                              "id": 3456, 
                                              "size": 1326}})
    if 'config/upload/' in url:
        return mockRequestObj({"meta": {"code": 200}, 
                               "response": {"test_id": "test_test_id", 
                                            "config_id": 23456, 
                                            "conf_file": "appurify.conf"}})
    if 'tests/run' in url:
        return mockRequestObj({"meta": {"code": 200}, 
                               "response": {"test_run_id": "test_test_run_id", 
                                            "test_id": "test_test_id", 
                                            "app_id": "test_app_id", 
                                            "request_time": "2013-09-09 22:39:19.186788+00:00"}})

def mockRequestGet(url, params, verify=False, headers={'User-Agent': 'MockUserAgent'}):
    if 'tests/check' in url:
        if mockRequestGet.count <= 0:
            mockRequestGet.count = mockRequestGet.count + 1
            return mockRequestObj({"meta": {"code": 200}, 
                                   "response": {"status": "in-progress", 
                                                "test_run_id": "test_test_run_id", 
                                                "test_config": "[uiautomation]\n\n[appurify]\nprofiler=1\npcap=1\n", 
                                                "device_type": "58 - iPhone 5_NR / iOS 6.1.2", 
                                                "device_type_id": 58}})
        else:
            mockRequestGet.count = mockRequestGet.count + 1
            return mockRequestObj({"meta": {"code": 200}, 
                                   "response": {"status": "complete", 
                                                "test_config": "[test_type]\nconfig", 
                                                "results": {"exception": None, 
                                                            "errors": "", 
                                                            "url": "http://localhost/resource/tests/result/?run_id=dummy_test_run_id", 
                                                            "number_passes": 1, 
                                                            "number_fails": 1, 
                                                            "pass": False, 
                                                            "output": "test_run_output"}, 
                                                "test_run_id": "test_test_run_id", 
                                                "device_type": "58 - iPhone 5_NR / iOS 6.1.2", 
                                                "device_type_id": 58}})
mockRequestGet.count = 0

class TestAuth(unittest.TestCase):
    def setUp(self):
        self.client = AppurifyClient(api_key="test_key", api_secret="test_secret")

    @mock.patch("requests.post", mockRequestPost)
    def testGetAccessToken(self):
        client = AppurifyClient(api_key="test_key", api_secret="test_secret")
        client.refreshAccessToken()
        access_token = client.access_token
        self.assertEqual(access_token, "test_access_token", "Should return proper access token on post")

    def testGetAccessTokenPrePop(self):
        client = AppurifyClient(access_token="Already_Set")
        client.refreshAccessToken()
        access_token = client.access_token
        self.assertEqual(access_token, "Already_Set", "Should return access token when one is provided")

    def testNoAuth(self):
        client = AppurifyClient()
        with self.assertRaises(AppurifyClientError):
            """ Should error out on no auth data """
            client.refreshAccessToken()

class TestUpload(unittest.TestCase):

    @mock.patch("requests.post", mockRequestPost)
    def testUploadAppNoSource(self):
        client = AppurifyClient(access_token="authenticated", test_type='ios_webrobot')
        app_id = client.uploadApp()
        self.assertEqual(app_id, "test_app_id", "Should properly fetch web robot for app id")

    @mock.patch("requests.post", mockRequestPost)
    def testUploadAppSource(self):
        client = AppurifyClient(access_token="authenticated", app_src=__file__, app_src_type='raw', test_type='calabash', name="test_name")
        app_id = client.uploadApp()
        self.assertEqual(app_id, "test_app_id", "Should properly fetch web robot for app id")

    @mock.patch("requests.post", mockRequestPost)
    def testUploadAppNoSourceError(self):
        client = AppurifyClient(access_token="authenticated", app_src_type='raw', test_type='calabash')
        with self.assertRaises(AppurifyClientError):
            client.uploadApp()

    @mock.patch("requests.post", mockRequestPost)
    def testUploadTestNoSource(self):
        client = AppurifyClient(access_token="authenticated", test_type='ios_webrobot')
        app_id = client.uploadTest('test_app_id')
        self.assertEqual(app_id, "test_test_id", "Should properly fetch web robot for app id")

    @mock.patch("requests.post", mockRequestPost)
    def testUploadTest(self):
        client = AppurifyClient(access_token="authenticated", test_src=__file__, test_type="uiautomation", test_src_type='raw')
        test_id = client.uploadTest('test_app_id')
        self.assertEqual(test_id, "test_test_id", "Should properly fetch web robot for app id")

    @mock.patch("requests.post", mockRequestPost)
    def testUploadTestNoSourceError(self):
        client = AppurifyClient(access_token="authenticated", test_type='uiautomation')
        with self.assertRaises(AppurifyClientError):
            app_id = client.uploadTest('test_app_id')

    @mock.patch("requests.post", mockRequestPost)
    def testUploadConfig(self):
        client = AppurifyClient(access_token="authenticated", test_type="ios_webrobot")
        config_id = client.uploadConfig("test_id", config_src=__file__)
        self.assertEqual(config_id, 23456, "Should properly fetch uploaded config id")

class TestRun(unittest.TestCase):

    @mock.patch("requests.post", mockRequestPost)
    def testRunTestSingle(self):
        client = AppurifyClient(access_token="authenticated")
        test_run_id = client.runTest("app_id", "test_test_id")
        self.assertEqual(test_run_id, "test_test_run_id", "Should get test_run_id when executing run")

    @mock.patch("requests.get", mockRequestGet)
    def testPollTestResult(self):
        mockRequestGet.count = 0
        client = AppurifyClient(access_token="authenticated", timeout_sec=2, poll_every=0.1)
        test_status_response = client.pollTestResult("test_test_run_id")
        self.assertEqual(test_status_response['status'], "complete", "Should poll until complete")

    @mock.patch("requests.post", mockRequestPost)
    @mock.patch("requests.get", mockRequestGet)
    def testMain(self):
        client = AppurifyClient(api_key="test_key", api_secret="test_secret", test_type="uiautomation", 
                                app_src=__file__, app_src_type='raw', 
                                test_src=__file__, test_src_type='raw',
                                timeout_sec=2, poll_every=0.1)
        result_code = client.main()
        self.assertEqual(result_code, 1, "Main should execute and return result code")

    @mock.patch("requests.get", mockRequestGet)
    def testPollTimeout(self):
        mockRequestGet.count = -20
        client = AppurifyClient(access_token="authenticated", timeout_sec=0.2, poll_every=0.1)
        with self.assertRaises(AppurifyClientError):
            client.pollTestResult("test_test_run_id")
