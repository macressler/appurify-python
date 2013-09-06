# Appurify Python Client

The official Python client for the [Appurify](http://www.appurify.com) API.

### Installation

```
pip install appurify-0.1.10.tar.gz
```

This will install any missing dependencies and add two executable scripts to your bin folder:

```
$ appurify-client.py -h
$ appurify-tunnel.py -h
```

### Running Tests

```
appurify-client.py --api-key $API_KEY --api-secret $API_SECRET \
--app-src $APP-SRC --app-test-type $TEST_TYPE --test-src $TEST_SRC --test-type $TEST_TYPE \
--device-type-id $DEVICE_TYPE_IDS --result-dir $RESULT_DIR
```

### Parameters

- `API-KEY`: Used for authentication
- `API-SECRET`: Used for authentication
- `APP-SRC`: The path or URL to the app binary (.ipa or .apk)
- `TEST_SRC`: The path or URL where the test files are located
- `TEST_TYPE`: Your test framework name (i.e. calabash, ios_robot, ocunit, uiautomation)
- `DEVICE_TYPE_IDS`: A comma separated list of numbers representing the device type IDs you wish to use for your test
- `RESULT_DIR`: The directory on your local machine where you want your results to be written.

### Jenkins Integration
In Jenkins create a new Execute Shell build step and upload your app using the Python wrapper as pictured below.

![Jenkins Integration](https://raw.github.com/appurify/appurify-python/master/jenkins.png)

### Contribution

Found a bug or want to add a much needed feature?  Go for it and just send us the Pull Request!
