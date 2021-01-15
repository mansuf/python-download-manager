import os
from pdm.retriever import Retriever
from pdm.constants import BUFFER

class PythonDownloadManager:
    def __init__(self, replace=False):
        self.replace = replace

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

    def download(self, url: str, filename: str, timeout: int=None):
        r = Retriever(url, filename, timeout)
        filenames = r.retrieve()        
        self._merge_files(filenames, filename)
        return filename




