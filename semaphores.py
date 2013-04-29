#!/usr/bin/env python3
"""
This is a Python (>= 3.2) port of the semaphore example code at
https://github.com/cwru-eecs338/semaphores . It uses System V semaphores and
shared memory through the sysv_ipc module.
"""
from os import fork, getpid, wait
import struct
from sys import exit

from sysv_ipc import Semaphore, SharedMemory, IPC_CREAT, IPC_EXCL, IPC_PRIVATE

def print_with_pid(*objects, **kwargs):
    """
    Functions as a drop-in replacement for __builtins__.print.
    Prepends the process ID to everything that is printed.
    """
    if objects:
        # Bit of a hack: if you provide at least one positional argument,
        # replace the first one (regardless of type) with a string that
        # starts with the right-justified process ID.
        objects = list(objects)
        objects[0] = '{:>5}: {}'.format(getpid(), objects[0])
    __builtins__.print(*objects, **kwargs)

print = print_with_pid

# Global constant:
BUF_SIZE = 3

class LuckyCharm:
    """
    Inspired by the python_threads example at
    https://github.com/cwru-eecs338/python_threads
    """
    # This is the maximum number of *bytes* that can be stored in shared
    # memory using UTF-8 encoding.
    MAX_CHARM_NAME_LENGTH = 32
    STRUCT_PACK_FORMAT = '{}sii'.format(MAX_CHARM_NAME_LENGTH)
    STRUCT_PACK_SIZE = struct.calcsize(STRUCT_PACK_FORMAT)

    def __init__(self, name, ansi_color, setting):
        """
        If the "name" argument is a bytes object (e.g. as returned by
        struct.unpack), it is decoded to a str.

        The str version of "name" is then encoded to UTF-8 bytes, truncated
        to MAX_CHARM_NAME_LENGTH and then decoded back to a str. If the
        byte string is truncated in the middle of a multi-byte character,
        the entire character is dropped.
        """
        if isinstance(name, bytes):
            # The struct module will dutifully give us the zero
            # bytes that follow the actual data that we want to
            # use for "name". Strip any zero bytes before decoding.
            name = name.strip(b'\x00').decode()
        # If we lose the latter part of a multi-byte character when we
        # truncate to MAX_CHARM_NAME_LENGTH bytes, drop the entire character
        # with errors='ignore'
        self.name = name.encode()[:self.MAX_CHARM_NAME_LENGTH].decode(
            errors='ignore')
        self.ansi_color = ansi_color
        self.setting = setting

    def __str__(self):
        return '\033[{};{}m{}\033[0m'.format(self.setting,
            self.ansi_color, self.name)

    def pack(self):
        """
        Returns this LuckyCharm's data packed as a byte string.

        Important: since the unpacked values are passed directly
        to this class's constructor in the "unpack" class method,
        the order that the fields are packed must match the
        order of the fields in the constructor.
        """
        return struct.pack(self.STRUCT_PACK_FORMAT,
            self.name.encode(), self.ansi_color, self.setting)

    @classmethod
    def unpack(cls, data):
        """
        Creates a LuckyCharm object from a byte string.
        """
        args = struct.unpack(cls.STRUCT_PACK_FORMAT, data)
        return cls(*args)

CHARMS = [
    LuckyCharm('PINK HEART',       35, 1),
    LuckyCharm('ORANGE STAR',      33, 0),
    LuckyCharm('YELLOW MOON',      33, 1),
    LuckyCharm('GREEN CLOVER',     32, 0),
    LuckyCharm('BLUE DIAMOND',     34, 1),
    LuckyCharm('PURPLE HORSESHOE', 35, 0),
    LuckyCharm('RED BALLOON',      31, 0),
]
CHARM_COUNT = len(CHARMS)
SHARED_MEMORY_SIZE = LuckyCharm.STRUCT_PACK_SIZE * BUF_SIZE

def consumer(shm, mutex, empty, full):
    nextc = 0
    # We don't want to iterate over the CHARMS list; we just need
    # to know how many times to read from the shared memory.
    for _ in range(CHARM_COUNT):
        full.acquire()
        mutex.acquire()
        # Pointer arithmetic is actually nicer in C:
        offset = nextc * LuckyCharm.STRUCT_PACK_SIZE
        packed_data = shm.read(LuckyCharm.STRUCT_PACK_SIZE, offset=offset)
        charm = LuckyCharm.unpack(packed_data)
        print('    Consuming: {}'.format(charm))
        nextc = (nextc + 1) % BUF_SIZE
        mutex.release()
        empty.release()
    exit()

def producer(shm, mutex, empty, full):
    nextp = 0
    # Iterate directly over the CHARMS list. We'll serialize these
    # objects into the shared memory buffer
    for charm in CHARMS:
        empty.acquire()
        mutex.acquire()
        print('Producing: {}'.format(charm))
        # Pointer arithmetic is actually nicer in C:
        offset = nextp * LuckyCharm.STRUCT_PACK_SIZE
        packed_data = charm.pack()
        # Note: can *not* use "offset" as a keyword argument.
        # It isn't processed correctly in version 0.6.4 of the
        # sysv_ipc package.
        shm.write(packed_data, offset)
        nextp = (nextp + 1) % BUF_SIZE
        mutex.release()
        full.release()
    exit()

def main():
    # Set up shared data
    shm = SharedMemory(IPC_PRIVATE, size=SHARED_MEMORY_SIZE, flags=IPC_CREAT)
    mutex = Semaphore(IPC_PRIVATE, initial_value=1,
        flags=IPC_CREAT | IPC_EXCL)
    empty = Semaphore(IPC_PRIVATE, initial_value=BUF_SIZE,
        flags=IPC_CREAT | IPC_EXCL)
    full = Semaphore(IPC_PRIVATE, flags=IPC_CREAT | IPC_EXCL)
    print('Forking producer')
    producer_id = fork()
    if not producer_id:
        producer(shm, mutex, empty, full)
    print('Forking consumer')
    consumer_id = fork()
    if not consumer_id:
        consumer(shm, mutex, empty, full)
    # Wait for children
    wait()
    wait()
    # Clean up.
    shm.detach()
    shm.remove()
    mutex.remove()
    empty.remove()
    full.remove()

if __name__ == '__main__':
    main()
