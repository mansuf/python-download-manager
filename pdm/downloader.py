import os
from pdm.retriever import Retriever
from pdm.constants import BUFFER

class PythonDownloadManager:
    def __init__(self, replace=False, max_connections=2):
        self.replace = replace
        self.max_connections = max_connections

    def _merge_files(self, filenames, dest):
        if os.path.exists(dest):
            if not self.replace:
                return
        writer = open(dest, 'wb')
        for file in filenames:
            rf = open(file, 'rb')
            while True:
                data = rf.read(BUFFER)
                if data == b'':
                    break
                else:
                    writer.write(data)
            rf.close()
        writer.close()
        for file in filenames:
            os.remove(file)

    def download(self, url: str, filename: str=None, timeout: int=None):
        if filename is not None:
            if os.path.exists(filename):
                return
        r = Retriever(url, filename, timeout, self.max_connections)
        filenames = r.retrieve()
        if isinstance(filenames, list):
            self._merge_files(filenames, filenames[0].split('.part0')[0])
            return filenames[0].split('.part0')[0]
        else:
            if filename is None:
                return filenames
            elif filenames == filename:
                return filenames
            else:
                os.rename(filenames, filename)
                return filenames


