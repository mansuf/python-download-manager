import time
from pdm.constants import BUFFER
from urllib.request import (
    build_opener,
    urlopen,
    Request
)
from http.client import HTTPResponse, HTTPMessage
from threading import Thread, Event
from pdm.utils import get_filename
from concurrent.futures import Future
from pdm.hooker import ProgressDownloadHooker


class _Retriever:
    def __init__(
        self,
        http_response: HTTPResponse,
        file: str,
        part: int,
        single_mode=False
    ):
        self.http = http_response
        if single_mode:
            self.file = file
        else:
            self.file = file + '.part' + str(part)
        self.speed_download = 0

    def get_file(self):
        return open(self.file, 'wb')

    def download(self):
        file = self.get_file()
        chunk_size = int(BUFFER.__repr__())
        while True:
            # adapted from https://github.com/choldgraf/download/blob/master/download/download.py#L380
            # with some modifications
            t0 = time.time()
            chunk = self.http.read(chunk_size)
            dt = time.time() - t0
            if dt < 0.005:
                chunk_size *= 2
            elif dt > 0.1 and chunk_size > BUFFER:
                chunk_size = chunk_size // 2
            if not chunk:
                break
            file.write(chunk)
            self.speed_download = len(chunk) * 8
            if chunk == b'':
                break
        self.speed_download = 'finished'
        file.close()
        return self.file

class Retriever1Connections:
    def __init__(self, url: str, info_length: int, filename: str=None):
        self.opener = build_opener()
        self.filename = filename
        self.url = url
        self.length = info_length

    def download(self):
        res = self.opener.open(self.url)
        filename = self.filename or get_filename(res)
        r = _Retriever(res, filename, 0, True)
        r.download()
        return filename

class Retriever2Connections:
    def __init__(self, url: str, length: int, filename: str=None):
        self.opener = build_opener()
        self.filename = filename
        self.url = url
        self.length = self.get_length(length)

    def get_length(self, length: int):
        divided = length / 2
        if not divided.is_integer():
            final = [0, divided - 0.5, divided + 0.5, length]
        elif divided.is_integer():
            final = [0, divided - 1, divided, length]
        return final

    def _download(self, part: int, start_from: int, end_from: int, future: Future):
        req = Request(self.url)
        req.headers['Range'] = 'bytes=%s-%s' % (int(start_from), int(end_from))
        res = self.opener.open(req)
        filename = self.filename or get_filename(res)
        r = _Retriever(res, filename, part)
        future.set_result(r.download())

    def download(self):
        fut1 = Future()
        thread = Thread(target=self._download, name='worker_pdm_0', daemon=True, args=(
            0,
            self.length[0],
            self.length[1],
            fut1
        ))
        thread.start()
        fut2 = Future()
        thread = Thread(target=self._download, name='worker_pdm_1', daemon=True, args=(
            1,
            self.length[2],
            self.length[3],
            fut2
        ))
        thread.start()
        return [
            fut1.result(),
            fut2.result()
        ]

class Retriever3Connections:
    def __init__(self, url: str, length: int, filename: str=None):
        self.opener = build_opener()
        self.filename = filename
        self.url = url
        self.length = self.get_length(length)

    def get_length(self, length: int):
        final = [0, int(length / 3), int(length / 3 + length / 3), length]
        return final

    def _download(
        self,
        part: int,
        start_from: int,
        end_from: int,
        future: Future,
        progress_bar: ProgressDownloadHooker
    ):
        req = Request(self.url)
        req.headers['Range'] = 'bytes=%s-%s' % (int(start_from), int(end_from))
        res = self.opener.open(req)
        filename = self.filename or get_filename(res)
        r = _Retriever(res, filename, part)
        progress_bar.add_worker(r)
        future.set_result(r.download())

    def download(self):
        fut1 = Future()
        print('Download Using 3 Connections')
        progress_bar = ProgressDownloadHooker()
        thread = Thread(target=self._download, name='worker_pdm_0', daemon=True, args=(
            0,
            self.length[0],
            self.length[1],
            fut1,
            progress_bar
        ))
        thread.start()
        fut2 = Future()
        thread = Thread(target=self._download, name='worker_pdm_1', daemon=True, args=(
            1,
            self.length[1],
            self.length[2],
            fut2,
            progress_bar
        ))
        thread.start()
        fut3 = Future()
        thread = Thread(target=self._download, name='worker_pdm_2', daemon=True, args=(
            2,
            self.length[2],
            self.length[3],
            fut3,
            progress_bar
        ))
        thread.start()
        progress_bar.start()
        result =  [
            fut1.result(),
            fut2.result(),
            fut3.result()
        ]
        progress_bar.stop()
        return result


class Retriever:
    def __init__(
        self,
        url: str,
        filename: str,
        timeout: int=None,
        connections: int=2
    ):
        # Testing Connection to URL given
        tester = urlopen(url, timeout=timeout)
        tester.close()
        self.filename = filename
        self.url = url
        self._connections = connections

    def _download_single_conn(self):
        r = Retriever1Connections(self.url, self.filename)
        return r.download()

    def _download_multi_conn(self, info_length):
        if self._connections < 1 or self._connections > 4:
            raise ValueError('invalid connections value, maximum connections allowed is 4')
        else:
            if self._connections == 2:
                r = Retriever2Connections(self.url, info_length, self.filename)
                return r.download()
            elif self._connections == 3:
                r = Retriever3Connections(self.url, info_length, self.filename)
                return r.download()

    def get_info_length(self):
        return urlopen(self.url).length

    def retrieve(self):
        info_length = self.get_info_length()
        # for doesn't support get length file like google-drive
        # multi connection require to see length of the file
        if info_length is None:
            # if pdm can't retrieve Content-Length info
            # force download to single connection
            return self._download_single_conn()
        else:
            if self._connections == 1:
                return self._download_single_conn()
            else:
                return self._download_multi_conn(info_length)


    # def _retrieve(self, part, filename, start_from, end_from, event, single_mode=False):
    #     r = Request(self.url)
    #     if not single_mode:
    #         r.headers['Range'] = 'bytes=%s-%s' % (int(start_from), int(end_from))
    #     print(r.headers)
    #     http_response = self.opener.open(r)
    #     print(http_response.headers['Content-Disposition'])
    #     print(http_response.length, part)
    #     if single_mode:
    #         _ = _Retriever(self.url, http_response, filename, part, True)
    #         _.download()
    #         event.set()
    #     else:
    #         _ = _Retriever(
    #             self.url,
    #             http_response,
    #             filename,
    #             part
    #         )
    #         _.download()
    #         event.set()

    # def get_length(self, length: int):
    #     divided = length / 2
    #     if not divided.is_integer():
    #         final = [0, divided - 0.5, divided + 0.5, length]
    #     elif divided.is_integer():
    #         final = [0, divided - 1, divided, length]
    #     return final



    # def retrieve(self):
    #     info_length = self.get_info_length()
    #     # for doesn't support get length file like google-drive
    #     # multi connection require to see length of the file
    #     if info_length is None:
    #         return self._download_single_conn()
    #     else:
    #         return self._download_multi_conn(info_length)

    # def _download_single_conn(self):
    #     e = Event()
    #     self._retrieve(None, self.filename, None, None, e, True)
    #     return [self.filename]

    # def _download_multi_conn(self, info_length):
    #     i = 0
    #     length = self.get_length(info_length)
    #     wait_event1 = Event()
    #     thread = Thread(target=self._retrieve, name='worker_pdm_' + str(i), daemon=True, args=(
    #         i,
    #         self.filename,
    #         length[0],
    #         length[1],
    #         wait_event1
    #     ))
    #     thread.start()
    #     i += 1
    #     wait_event2= Event()
    #     thread = Thread(target=self._retrieve, name='worker_pdm_' + str(i), daemon=True, args=(
    #         i,
    #         self.filename,
    #         length[2],
    #         length[3],
    #         wait_event2
    #     ))
    #     thread.start()
    #     wait_event1.wait()
    #     wait_event2.wait()
    #     return [
    #         self.filename + '.part0',
    #         self.filename + '.part1'
    #     ]


