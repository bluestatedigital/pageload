import os, json
from datetime import datetime

class TestDirectoryInvalidError(Exception):
    pass

class Factory:
    def __init__(self, testResultsFactory):
        self.__dict__.update(locals())

    def _load(self, testsDir):
        results = []
        for resultDir in sorted(os.listdir(testsDir)):
            try:
                date = datetime.strptime( resultDir, '%Y%m%d%H%M%S' )
            except ValueError:
                continue
            path = os.path.join(testsDir, resultDir)
            if os.path.isfile( os.path.join(path, 'request.xml') ):
                results.append( self.testResultsFactory.create(path))
        return results

    def load(self, testsDir):
        if not os.path.isdir(testsDir):
            os.makedirs(testsDir)

        if not os.path.isdir( os.path.join(testsDir, '.pageload') ):
            os.makedirs(os.path.join(testsDir, '.pageload'))
            
        return PageLoadTestDirectory(testsDir, self._load(testsDir))

    def discover(self, baseDir):
        if not os.path.isdir( baseDir ):
            raise TestDirectoryInvalidError('%s is not a directory\n' % (baseDir))

        directories = []

        for name in os.listdir( baseDir ):
            testsDir = os.path.join(baseDir, name)
            if os.path.isdir(testsDir) and os.path.isdir( os.path.join(testsDir, '.pageload') ):
                results = self._load(testsDir)
                directories.append( PageLoadTestDirectory(testsDir, results) )
        return directories

class PageLoadTestDirectory:
    def __init__(self, directory, results):
        self.__dict__.update(locals())
    def getTestResults(self):
        return self.results
    def getDirectory(self):
        return self.directory
    def getName(self):
        return os.path.basename(self.directory)
    def addResult(self, result):
        self.results.append( result )
        self.writeManifest()
    def getManifest(self):
        manifest = dict()
        for result in self.results:
            manifest[ result.getSignature() ] = result
        return manifest
    def writeManifest(self):
        path = os.path.join(self.directory, '.pageload')
        path = os.path.join(path, 'manifest')
        manifest = self.getManifest()
        for sig, result in manifest.items():
            manifest[sig] = result.getDateTime().strftime('%Y%m%d%H%M%S')
        fp = open(path, 'w')
        fp.write( json.dumps(manifest, indent=4) )
        fp.close()
    def getTestResultByHash(self, hash):
        manifest = self.getManifest()
        for sig, result in manifest.items():
            if sig.lower().startswith(hash.lower()):
                return result
        return None
