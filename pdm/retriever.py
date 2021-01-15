from pdm.constants import BUFFER
from urllib.request import (
    build_opener,
    urlopen,
    Request
)
from http.client import HTTPResponse, HTTPMessage
from threading import Thread, Event

class _Retriever:
    def __init__(
        self,
        url: str,
        http_response: HTTPResponse,
        file: str,
        part: int,
        single_mode=False
    ):
        self.http = http_response
        self.url = url
        if single_mode:
            self.file = file
        else:
            self.file = file + '.part' + str(part)

    def get_file(self):
        return open(self.file, 'wb')

    def download(self):
        file = self.get_file()
        while True:
            data = self.http.read(BUFFER)
            print(data)
            file.write(data)
            if data == b'':
                break
        file.close()


class Retriever:
    def __init__(self, url: str, filename: str, timeout: int=None):
        # Testing Connection to URL given
        tester = urlopen(url, timeout=timeout)
        tester.close()
        self.filename = filename
        self.opener = build_opener()
        self.url = url

    def _retrieve(self, part, filename, start_from, end_from, event, single_mode=False):
        r = Request(self.url)
        if not single_mode:
            r.headers['Range'] = 'bytes=%s-%s' % (int(start_from), int(end_from))
        print(r.headers)
        http_response = self.opener.open(r)
        print(http_response.length, part)
        if single_mode:
            _ = _Retriever(self.url, http_response, filename, part, True)
            _.download()
            event.set()
        else:
            _ = _Retriever(
                self.url,
                http_response,
                filename,
                part
            )
            _.download()
            event.set()

    def get_length(self, length: int):
        divided = length / 2
        if not divided.is_integer():
            final = [0, divided - 0.5, divided + 0.5, length]
        elif divided.is_integer():
            final = [0, divided - 1, divided, length]
        return final

    def get_info_length(self):
        return urlopen(self.url).length

    def retrieve(self):
        info_length = self.get_info_length()
        # for doesn't support get length file like google-drive
        # multi connection require to see length of the file
        if info_length is None:
            return self._download_single_conn()
        else:
            return self._download_multi_conn(info_length)

    def _download_single_conn(self):
        e = Event()
        self._retrieve(None, self.filename, None, None, e, True)
        return [self.filename]

    def _download_multi_conn(self, info_length):
        i = 0
        length = self.get_length(info_length)
        wait_event1 = Event()
        thread = Thread(target=self._retrieve, name='worker_pdm_' + str(i), daemon=True, args=(
            i,
            self.filename,
            length[0],
            length[1],
            wait_event1
        ))
        thread.start()
        i += 1
        wait_event2= Event()
        thread = Thread(target=self._retrieve, name='worker_pdm_' + str(i), daemon=True, args=(
            i,
            self.filename,
            length[2],
            length[3],
            wait_event2
        ))
        thread.start()
        wait_event1.wait()
        wait_event2.wait()
        return [
            self.filename + '.part0',
            self.filename + '.part1'
        ]


