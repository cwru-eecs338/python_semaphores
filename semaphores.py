#!/usr/bin/env python3
from collections import namedtuple
from os import fork, getpid, wait
import struct
from sys import exit

from sysv_ipc import Semaphore, SharedMemory, IPC_CREAT, IPC_EXCL, IPC_PRIVATE

def print_with_pid(*objects, **kwargs):
    """
    Functions as a drop-in replacement for __builtins__.print
    """
    if objects:
        # Bit of a hack: if you provide at least one positional argument,
        # replace the first one (regardless of type) with a string that
        # starts with the process ID.
        objects = list(objects)
        objects[0] = '{:>5}: {}'.format(getpid(), objects[0])
    __builtins__.print(*objects, **kwargs)

print = print_with_pid

BUF_SIZE = 3
class LuckyCharm:
    """
    Inspired by the python_threads example at
    https://github.com/cwru-eecs338/python_threads
    """
    MAX_CHARM_NAME_LENGTH = 32
    STRUCT_PACK_FORMAT = '{}sii'.format(MAX_CHARM_NAME_LENGTH)

    def __init__(self, name, ansi_color, setting):
        """
        The "name" argument is truncated to MAX_CHARM_NAME_LENGTH
        characters. If it is a bytes object (e.g. as returned by
        struct.unpack), it is decoded to a str.
        """
        if isinstance(name, bytes):
            name = name.decode()
        self.name = name[:self.MAX_CHARM_NAME_LENGTH]
        self.ansi_color = ansi_color
        self.setting = setting

    def __str__(self):
        return '\033[{};{}m{}\033[0m'.format(self.setting,
            self.ansi_color, self.name)

    def pack(self):
        """
        Returns this LuckyCharm's data as a tuple. Encodes the
        name to a bytes object so that the struct module can
        accept it.
        """
        return struct.pack(self.STRUCT_PACK_FORMAT,
            self.name.encode(), self.setting, self.ansi_color)

CHARMS = [
    LuckyCharm('PINK HEART',       35, 1),
    LuckyCharm('ORANGE STAR',      33, 0),
    LuckyCharm('YELLOW MOON',      33, 1),
    LuckyCharm('GREEN CLOVER',     32, 0),
    LuckyCharm('BLUE DIAMOND',     34, 1),
    LuckyCharm('PURPLE HORSESHOE', 35, 0),
    LuckyCharm('RED BALLOON',      31, 0),
]
SHARED_MEMORY_SIZE = struct.calcsize(LuckyCharm.STRUCT_PACK_FORMAT) * BUF_SIZE

def consumer(shm, mutex, empty, full):
    exit()

def producer(shm, mutex, empty, full):
    exit()

def main():
    # Set up shared data
    shm = SharedMemory(IPC_PRIVATE, size=SHARED_MEMORY_SIZE, flags=IPC_CREAT)
    mutex = Semaphore(IPC_PRIVATE, flags=IPC_CREAT | IPC_EXCL)
    empty = Semaphore(IPC_PRIVATE, flags=IPC_CREAT | IPC_EXCL)
    full = Semaphore(IPC_PRIVATE, flags=IPC_CREAT | IPC_EXCL)
    # Fork producer
    producer_id = fork()
    if not producer_id:
        producer(shm, mutex, empty, full)
    consumer_id = fork()
    if not consumer_id:
        consumer(shm, mutex, empty, full)
    wait()
    wait()
    # Whatever happens above, try to clean up after ourselves
    shm.detach()
    shm.remove()
    mutex.remove()
    empty.remove()
    full.remove()

if __name__ == '__main__':
    main()
