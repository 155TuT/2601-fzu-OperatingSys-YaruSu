#include "mysem.h"

#include <errno.h>
#include <stdio.h>
#include <stdlib.h>
#include <sys/sem.h>
#include <unistd.h>

/* Linux 的 SETVAL 通过 semun.val 传入初值。每个集合只用第 0 项。 */
union semun {
    int val;
    struct semid_ds *buf;
    unsigned short *array;
};

MySem newsem(int initVal)
{
    MySem id = semget(IPC_PRIVATE, 1, 0600);
    if (id >= 0 && semctl(id, 0, SETVAL, (union semun){.val = initVal}) < 0) {
        int cause = errno;
        freesem(id);
        errno = cause;
        return -1;
    }
    return id;
}

static void change(MySem id, short delta)
{
    struct sembuf op = {.sem_num = 0, .sem_op = delta, .sem_flg = 0};
    while (semop(id, &op, 1) < 0) {
        if (errno != EINTR) {
            perror("semop");
            _exit(EXIT_FAILURE);   /* 父进程通过 waitpid 处理子进程失败。 */
        }
    }
}

void psem(MySem semID)
{
    change(semID, -1);
}

void vsem(MySem semID)
{
    change(semID, 1);
}

void freesem(MySem semID)
{
    if (semctl(semID, 0, IPC_RMID) < 0)
        perror("semctl IPC_RMID");
}
