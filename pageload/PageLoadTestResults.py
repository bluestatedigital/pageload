import csv, os, json, re, hashlib, shutil
from itertools import izip
from datetime import datetime

class Factory:
    def create(self, testDir):
        assetFactory = AssetFactory()
        runFactory = RunFactory(ViewFactory(assetFactory))
        return PageLoadTestResults(self._generateSignature(testDir), testDir, assetFactory, runFactory)
    def _generateSignature(self, testDir):
        fp = open( os.path.join(testDir, 'request.xml') )
        contents = fp.read()
        fp.close()
        return hashlib.md5(contents).hexdigest()

class Run:
    def __init__(self, firstView, repeatView):
        self.__dict__.update(locals())
    def getFirstView(self):
        return self.firstView
    def getRepeatView(self):
        return self.repeatView
    def __str__(self):
        return str(self.firstView.getHeaders())

class RunFactory:
    def __init__(self, viewFactory):
        self.__dict__.update(locals())
    def create(self, runDir):
        firstView = self.viewFactory.create( os.path.join(runDir, 'firstView') )
        repeatView = self.viewFactory.create( os.path.join(runDir, 'repeatView') )
        return Run(firstView, repeatView)

class Asset:
    pass

class DictionaryAsset(Asset):
    def __init__(self, dictionary):
        self.__dict__.update(locals())
    def __len__(self):
        return len(self.dictionary)
    def __getitem__(self, key):
        return self.dictionary[key]
    def __setitem__(self, key, value):
        self.dictionary[key] = value
    def __delitem__(self, key):
        del self.dictionary[key]
    def __iter__(self):
        return iter(self.dictionary)
    def __reversed__(self):
        return reversed(self.dictionary)
    def __contains__(self, key):
        return key in self.dictionary
    def __str__(self):
        return json.dumps(self.dictionary, indent=4)
        #return str(self.dictionary)
    def __repr__(self):
        return repr(self.dictionary)

# A list is a special case of a dictionary
class ListAsset(DictionaryAsset):
    pass

###
# These assets for each Run's View objects
###

class PageData(DictionaryAsset):
    pass

class RequestData(DictionaryAsset):
    pass

class Utilization(DictionaryAsset):
    pass

class PageSpeedData(ListAsset):
    pass

class Headers(Asset):
    def __init__(self, requestHeaders, responseHeaders):
        self.__dict__.update(locals())
    def getRequestHeaders(self):
        return self.requestHeaders
    def getResponseHeaders(self):
        return self.responseHeaders
    def __str__(self):
        return json.dumps({'request': self.requestHeaders, 'response': self.responseHeaders}, indent=4)

###
# These are top level assets
###

class RequestDetails(DictionaryAsset):
    pass

class RequestSummary(DictionaryAsset):
    pass

class AssetFactory:
    def createPageSpeedData(self, pageSpeedDataFile):
        fp = open(pageSpeedDataFile)
        contents = fp.read()
        fp.close()
        obj = json.loads(contents)
        return PageSpeedData(obj)

    def createPageData(self, pageDataCsv):
        csvReader = csv.reader(open(pageDataCsv, 'rb'), delimiter='\t')
        header = next(csvReader)
        body = next(csvReader)
        return PageData(dict(izip(header, body)))

    def createRequestsData(self, requestsDataCsvFile):
        csvReader = csv.reader(open(requestsDataCsvFile, 'rb'), delimiter='\t')
        header = next(csvReader)
        requests = []
        for row in csvReader:
            requests.append( RequestData(dict(izip(header, row))) )
        return requests

    def createUtilization(self, utilizationCsv):
        csvReader = csv.reader(open(utilizationCsv, 'rb'), delimiter=',')
        header = next(csvReader)
        utilization = []
        for row in csvReader:
            utilization.append( Utilization(dict(izip(header, row))) )
        return utilization

    def createRequestDetails(self, detailsCsvFile):
        requestCsvReader = csv.reader(open(detailsCsvFile, 'rb'), delimiter=',', quotechar='"')
        header = next(requestCsvReader)
        requests = []
        for row in requestCsvReader:
            requests.append( RequestDetails(dict(izip(header, row))) )
        return requests

    def createRequestSummary(self, summaryCsvFile):
        requestCsvReader = csv.reader(open(summaryCsvFile, 'rb'), delimiter=',', quotechar='"')
        header = next(requestCsvReader)
        requests = []
        for row in requestCsvReader:
            requests.append( RequestSummary(dict(izip(header, row))) )
        return requests

    def createHeaders(self, headersFile):
        headerFileLines = open( headersFile ).readlines() 
        for index, line in enumerate(headerFileLines):
            if line.startswith('Request details'):
                break

        headerFileLines = headerFileLines[index + 1:]
        headerFileLines = list(map(lambda x: x.strip(), headerFileLines))
        headerFileLines = list(filter(lambda x: len(x), headerFileLines))
        headerFileLines.append('EOT')

        buf = '['
        while len(headerFileLines):
            (advance, string) = self._jsonifyHeaders(headerFileLines[0], headerFileLines)
            headerFileLines = headerFileLines[advance:]
            buf += string
        buf = buf.replace(',]', ']')
        buf += ']'
        headers = json.loads(buf)
        return list(map(lambda x: Headers(x['request'], x['response']), headers))

    def _jsonifyHeaders(self, line, lines):
        advance = 1
        if re.match('Request 1:', line):
            string = '{'
            advance = lines.index('Request Headers:')
        elif re.match('Request (\d+):', line):
            string = ']},{'
            advance = lines.index('Request Headers:')
        elif re.match('EOT', line):
            string = ']}'
        elif re.match('Request Headers:', line):
            string = '"request": ['
        elif re.match('Response Headers:', line):
            string = '], "response": ['
        else:
            string = '"%s",' % (line.replace('"', '\\"'))
        return (advance, string)

class View:
    def __init__(self, headers, pageData, pageSpeedData, requestData, utilizationData):
        self.__dict__.update(locals())
    def getHeaders(self):
        return self.headers
    def getPageData(self):
        return self.pageData
    def getPageSpeedData(self):
        return self.pageSpeedData
    def getRequestData(self):
        return self.requestData
    def getUtilizationData(self):
        return self.utilizationData

class ViewFactory:
    def __init__(self, viewAssetFactory):
        self.__dict__.update(locals())
    def create(self, viewDir):
        headers = self.viewAssetFactory.createHeaders(os.path.join(viewDir, 'data/headers'))
        pageData = self.viewAssetFactory.createPageData(os.path.join(viewDir, 'data/pageData'))
        pageSpeedData = self.viewAssetFactory.createPageSpeedData(os.path.join(viewDir, 'data/PageSpeedData'))
        requestData = self.viewAssetFactory.createRequestsData(os.path.join(viewDir, 'data/requestsData'))
        utilizationData = self.viewAssetFactory.createUtilization(os.path.join(viewDir, 'data/utilization'))
        return View( headers, pageData, pageSpeedData, requestData, utilizationData )

class PageLoadTestResults:
    def __init__(self, md5signature, testDir, assetFactory, runFactory):
        self.__dict__.update(locals())
        self._cache = {}

    # Any method that this decorator caches its return value so subsequent calls are faster
    def cached(key):
        def wrapper(func):
            def cachedResults(*args, **kwargs):
                self = args[0]
                if key in self._cache and self._cache[key]:
                    return self._cache[key]

                result = func(*args, **kwargs)
                self._cache[key] = result
                return result
            return cachedResults
        return wrapper

    @cached('request_details')
    def getRequestDetails(self):
        return self.assetFactory.createRequestDetails(os.path.join(self.testDir, 'detail.csv'))

    @cached('request_summary')
    def getRequestSummary(self):
        return self.assetFactory.createRequestSummary(os.path.join(self.testDir, 'summary.csv'))

    @cached('runs')
    def getRuns(self):
        runDir = os.path.join(self.testDir, 'run')
        dirs = os.listdir(runDir)
        runs = []
        for directory in dirs:
            path = os.path.join( runDir, directory )
            run = self.runFactory.create( path )
            runs.append(run)
        return runs

    def getSignature(self):
        return self.md5signature

    def getDateTime(self):
        return datetime.strptime(os.path.basename(self.testDir), '%Y%m%d%H%M%S')

    def remove(self):
        shutil.rmtree(self.testDir)
