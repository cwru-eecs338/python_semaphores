#!/usr/bin/env python3
from os import fork, getpid, wait

from sysv_ipc import Semaphore, SharedMemory, IPC_CREAT, IPC_EXCL, IPC_PRIVATE

def print_with_pid(string, *args, **kwargs):
    s = '{:>5}: {}'.format(getpid(), string)
    __builtins__.print(s, *args, **kwargs)

print = print_with_pid

if __name__ == '__main__':
    shm = SharedMemory(IPC_PRIVATE, size=16, flags=IPC_CREAT)
    sem = Semaphore(IPC_PRIVATE, flags=IPC_CREAT | IPC_EXCL)
    pid = fork()
    print('Parent process')
    if pid:
        print('Writing bytes to shared memory')
        shm.write(b'some bytes')
        print('Releasing semaphore')
        sem.release()
    else:
        print('Child process')
        print('Acquiring semaphore')
        sem.acquire()
        print('Reading from shared memory.')
        print(shm.read())
    print('Detaching shared memory.')
    shm.detach()
    if pid:
        print('Waiting for child to finish')
        wait()
        print('Removing shared memory')
        shm.remove()
        print('Removing semaphore')
        sem.remove()
