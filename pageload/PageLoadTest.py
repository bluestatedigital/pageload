import httplib, urllib
import StringIO, sys, os, json, logging, shutil
from xml.etree.ElementTree import ElementTree
from xml.dom.minidom import parseString as parseXmlString
from urlparse import urlparse
from time import sleep
from datetime import datetime
from pageload.PageLoadTestResults import Factory as PageLoadTestResultsFactory

class Factory:
    def create(self, testDirectory, url, config):
        return PageLoadTest(testDirectory, url, config, PageLoadTestResultsFactory())

class PageLoadTestException(Exception):
    pass

class PageLoadTest:
    def __init__(self, testDirectory, url, config = {}, testResultsFactory = None):
        self.__dict__.update(locals())
        self.logger = logging.getLogger('pageload')
        self.defaultHeaders = {
            "Content-type": "application/x-www-form-urlencoded"
        }

    def run(self):
        timestamp = datetime.today()
        baseDir = self.testDirectory.getDirectory()

        pldir = os.path.join(baseDir, '.pageload')
        if not os.path.isdir(pldir):
            os.makedirs(pldir)

        testDir = os.path.normpath( os.path.join(baseDir, timestamp.strftime('%Y%m%d%H%M%S')) )

        assets = {
            'parameters.json': os.path.join(testDir, 'parameters.json'),
            'request.xml': os.path.join(testDir, 'request.xml'),
            'response.xml': os.path.join(testDir, 'response.xml'),
            'summary.csv': os.path.join(testDir, 'summary.csv'),
            'detail.csv': os.path.join(testDir, 'detail.csv'),
            'run': os.path.join(testDir, 'run')
        }

        try:
            os.makedirs(testDir)
            self.logger.info('Directory %s created' % (testDir))
        except OSError as error:
            self.logger.error('Cannot create directory %s: %s' % (testDir, error))
            sys.exit(-1)

        try:
            os.mkdir( assets['run'] )
            self.logger.info('Directory %s created' % (assets['run']))
        except OSError as error:
            self.logger.error('Cannot create directory ./%s: %s' % (assets['run'], error))
            sys.exit(-1)
        
        testParameters = {
            'url': self.url,
            'config': self.config
        }

        parameters = open( assets['parameters.json'], 'w' )
        parameters.write( json.dumps(testParameters, sort_keys=True, indent=4) )
        parameters.close()

        (response, data) = self._makeHttpRequest('POST', self.config['wptserver'], '/runtest.php', urllib.urlencode(self.config), self.defaultHeaders)
        fp = open( assets['request.xml'], 'w' )
        fp.write(data)
        fp.close()

        self.logger.debug("Retrieved data\n %s" % data)
        tree = self._getXmlTree(data)
        xmlUrl = urlparse(tree.find('data/xmlUrl').text).path

        self.logger.info('Waiting for results')

        slept = 0
        cont = False
        while True:
            (response, statusData) = self._makeHttpRequest('GET', self.config['wptserver'], xmlUrl)
            statusTree = self._getXmlTree(statusData)
            statusCode = int(statusTree.find('statusCode').text)
            if 100 <= statusCode < 200:
                sleep(10)
                slept += 10
                if slept > 900:
                    self.logger.error('Timed out waiting for response (900 seconds)')
                    cont = True
                    break
                continue
            elif 400 <= statusCode < 500:
                self.logger.error('Could not retrieve response (HTTP status code %d)' % (statusCode))
                cont = True
                break
            break

        if cont:
            shutil.rmtree(testDir)
            return None

        self.logger.info('Results finished processing')
        self.logger.info('Downloading reports')

        (response, data) = self._makeHttpRequest('GET', self.config['wptserver'], urlparse(tree.find('data/xmlUrl').text).path)
        resultTree = self._getXmlTree(data)
        tData = data

        fp = open( assets['response.xml'], 'w' )
        fp.write( parseXmlString(data).toprettyxml() )
        fp.close()

        for asset, xmlElement in {'summary.csv': 'data/summaryCSV', 'detail.csv': 'data/detailCSV'}.items():
            urlParts = urlparse( tree.find( xmlElement ).text )
            (response, data) = self._makeHttpRequest('GET', self.config['wptserver'], urlParts.path)
            fp = open( assets[asset], 'w' )
            fp.write( data )
            fp.close()

        images = ['waterfall', 'checklist', 'screenShot']
        rawData = ['headers', 'pageData', 'requestsData', 'utilization', 'PageSpeedData']

        self.logger.info('Downloading run data')

        for run in resultTree.findall('data/run'):

            id = run.find('id').text
            runDir = os.path.join(assets['run'], id)

            try:
                os.mkdir(runDir)
                self.logger.info('Directory %s created' % (runDir))
            except OSError as error:
                self.logger.error('Cannot create directory ./%s: %s' % (runDir, error))
                sys.exit(-1)

            for view in [run.find('firstView'), run.find('repeatView')]:

                if view is None:
                    self.logger.error('Malformed response from server:')
                    self.logger.error(tData)
                    continue

                viewDir = os.path.join(runDir, view.tag)
                imageDir = os.path.join(viewDir, 'images')
                dataDir = os.path.join(viewDir, 'data')

                for Dir in [viewDir, imageDir, dataDir]:
                    try:
                        os.mkdir( Dir )
                        self.logger.info('Directory %s created' % ( Dir ))
                    except OSError as error:
                        self.logger.error('Cannot create directory ./%s: %s' % ( Dir, error ))
                        sys.exit(-1)

                for imageName in images:
                    imageUrl = view.find('images/' + imageName).text
                    localFileName = os.path.join(imageDir, imageName + '.' + imageUrl[-3:])
                    self._downloadFile(imageUrl, localFileName)

                for rawDataName in rawData:
                    rawDataUrl = view.find('rawData/' + rawDataName).text
                    localFileName = os.path.join(dataDir, rawDataName)
                    self._downloadFile(rawDataUrl, localFileName)
        result = self.testResultsFactory.create( testDir )
        self.testDirectory.addResult( result )
        return result

    def _makeHttpRequest(self, method, host, path, params='', headers={}):
        httpConnection = httplib.HTTPConnection(host)
        httpConnection.request(method, path, params, headers)
        response = httpConnection.getresponse()
        data = response.read()
        self.logger.info('%s %s %s (HTTP %s %s)' % (method.upper(), host, path, response.status, response.reason))
        httpConnection.close()
        return (response, data)

    def _downloadFile(self, url, localPath):
        try:
            self.logger.info('Downloading %s' % (url))
            value = urllib.urlretrieve(url, localPath)
            return value
        except IOError:
            self.logger.error('Could not download %s' % (url))

    def _getXmlTree( self, xmlString ):
        dataIO = StringIO.StringIO(xmlString)
        tree = ElementTree()
        tree.parse(dataIO)
        return tree
