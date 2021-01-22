import time
import threading
from pdm.constants import BUFFER
from pdm.utils import sizeof_fmt

class ProgressDownloadHooker:
    def __init__(self, *workers):
        self._stop = threading.Event()
        self.workers = self._parse_workers(workers)

    def _parse_workers(self, workers):
        data = {}
        for num in range(len(workers)):
            data[num] = workers[num]
        return data

    def _calculate_speed(self, number_arrays):
        total_number_arrays = 0
        for num in number_arrays:
            total_number_arrays += num
        return total_number_arrays / len(number_arrays)

    def _loop_print_worker(self):
        while True:
            words = ''
            total_speed = 0
            for key in self.workers.keys():
                worker = self.workers[key]
                try:
                    speed = sizeof_fmt(float(worker.speed_download))
                    total_speed += worker.speed_download
                except ValueError:
                    speed = 'finished'
                words += 'speed worker ' + str(key) + ' = ' + str(speed) + ', '
            if self._stop.is_set():
                print('\r' + 'total speed = ' + sizeof_fmt(total_speed) + ', ' + words[:len(words) - 2]) # remove comma in the end
                return
            else:
                print('\r' + 'total speed = ' + sizeof_fmt(total_speed) + ', ' + words[:len(words) - 2], end='') # remove comma in the end
            # add timeout to prevent overloading CPU
            time.sleep(0.1)

    def add_worker(self, worker):
        pos = max([num for num in self.workers.keys()] or [-1]) + 1
        self.workers[pos] = worker

    def start(self):
        t = threading.Thread(
            target=self._loop_print_worker,
            name='progress-download-worker',
            daemon=True
        )
        t.start()

    def stop(self):
        self._stop.set()