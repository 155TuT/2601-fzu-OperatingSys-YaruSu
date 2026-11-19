#include "mysem.h"

#include <ctype.h>
#include <errno.h>
#include <limits.h>
#include <signal.h>
#include <stdbool.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/sem.h>
#include <sys/shm.h>
#include <sys/wait.h>
#include <time.h>
#include <unistd.h>

enum { MAX_CAPACITY = 1024, MAX_PAIRS = 32 };

struct Warehouse {
    int capacity, initial, stock;
    int in, out;                 /* 下一次写入和取出的位置。 */
    int produced, consumed;
    int producers_left, consumers_left;
    unsigned role_seed;
    int slots[];                 /* 0 表示空位，正数为产品编号。 */
};

static struct Warehouse *warehouse;
static int shmid = -1;
static MySem empty = -1, full = -1, mutex = -1;
static volatile sig_atomic_t stopped;

static void on_signal(int sig)
{
    stopped = sig;
}

static void release_ipc(void)
{
    if (warehouse && shmdt(warehouse) < 0)
        perror("shmdt");
    if (shmid >= 0 && shmctl(shmid, IPC_RMID, NULL) < 0)
        perror("shmctl IPC_RMID");
    if (mutex >= 0) freesem(mutex);
    if (full >= 0) freesem(full);
    if (empty >= 0) freesem(empty);
}

static int number(const char *s, int low, int high)
{
    char *end;
    errno = 0;
    long n = strtol(s, &end, 10);
    if (end == s || errno || n < low || n > high)
        return -1;
    while (isspace((unsigned char)*end))
        ++end;
    return *end == '\0' ? (int)n : -1;
}

static int ask(const char *name, int low, int high)
{
    char line[80];
    printf("%s [%d..%d]:\n", name, low, high);
    if (fgets(line, sizeof line, stdin)) {
        int n = number(line, low, high);
        if (n >= 0 && (feof(stdin) || strchr(line, '\n')))
            return n;
    }
    fprintf(stderr, "Enter an integer from %d to %d for %s.\n", low, high, name);
    return -1;
}

static bool init(int pairs, unsigned seed)
{
    int cap = ask("Warehouse capacity", 1, MAX_CAPACITY);
    if (cap < 0) return false;
    int initial = ask("Initial stock", 0, cap);
    if (initial < 0) return false;

    shmid = shmget(IPC_PRIVATE, sizeof *warehouse + (size_t)cap * sizeof(int), 0600);
    if (shmid < 0) {
        perror("shmget");
        return false;
    }
    void *addr = shmat(shmid, NULL, 0);
    if (addr == (void *)-1) {
        perror("shmat");
        return false;
    }
    warehouse = addr;
    /* 新段由内核清零。已有产品从 0 号位连续摆放，满仓时 in 回到 0。 */
    warehouse->capacity = cap;
    warehouse->initial = warehouse->stock = initial;
    warehouse->in = initial % cap;
    warehouse->out = 0;
    warehouse->producers_left = warehouse->consumers_left = pairs;
    warehouse->role_seed = seed;
    for (int i = 0; i < initial; ++i)
        warehouse->slots[i] = i + 1;

    if ((empty = newsem(cap - initial)) < 0 || (full = newsem(initial)) < 0 ||
        (mutex = newsem(1)) < 0) {
        perror("newsem");
        return false;
    }
    printf("Initial: capacity=%d stock=%d in=%d out=0 pairs=%d seed=%u\n",
           cap, initial, warehouse->in, pairs, seed);
    printf("IPC: shm=%d empty=%d full=%d mutex=%d\n", shmid, empty, full, mutex);
    return true;
}

/* 同一轮有相同数量的 P 和 C。子进程按剩余名额随机抽取自己的角色。 */
static bool draw_producer(void)
{
    psem(mutex);
    int total = warehouse->producers_left + warehouse->consumers_left;
    bool producer = rand_r(&warehouse->role_seed) % total < warehouse->producers_left;
    if (producer)
        --warehouse->producers_left;
    else
        --warehouse->consumers_left;
    vsem(mutex);
    return producer;
}

/* 在临界区内记录产品和游标，使输出顺序对应仓库的实际操作顺序。 */
static void show_state(int item)
{
    printf("  item=%d stock=%d/%d in=%d out=%d\n", item, warehouse->stock,
           warehouse->capacity, warehouse->in, warehouse->out);
}

static void Pro(void)
{
    long pid = (long)getpid();
    printf("P %ld started.\n", pid);
    psem(empty);  /* 先预留空位，再进入临界区。 */
    psem(mutex);
    int pos = warehouse->in;
    int item = warehouse->initial + ++warehouse->produced;
    warehouse->slots[pos] = item;
    warehouse->in = (pos + 1) % warehouse->capacity;
    ++warehouse->stock;
    show_state(item);
    printf("P %ld put an item to %d.\n", pid, pos);
    vsem(mutex);
    vsem(full);
}

static void Con(void)
{
    long pid = (long)getpid();
    printf("C %ld started.\n", pid);
    psem(full);   /* 先预留一件产品，再进入临界区。 */
    psem(mutex);
    int pos = warehouse->out;
    int item = warehouse->slots[pos];
    warehouse->slots[pos] = 0;
    warehouse->out = (pos + 1) % warehouse->capacity;
    --warehouse->stock;
    ++warehouse->consumed;
    show_state(item);
    printf("C %ld got an item from %d.\n", pid, pos);
    vsem(mutex);
    vsem(empty);
}

static bool run_children(int pairs, unsigned seed)
{
    pid_t children[2 * MAX_PAIRS] = {0};
    int count = 0;
    for (; count < 2 * pairs && !stopped; ++count) {
        pid_t pid = fork();
        if (pid < 0) {
            perror("fork");
            break;
        }
        if (pid == 0) {
            signal(SIGINT, SIG_DFL);
            signal(SIGTERM, SIG_DFL);
            if (draw_producer())
                Pro();
            else
                Con();
            _exit(EXIT_SUCCESS);  /* 内核同时解除子进程继承的共享内存映射。 */
        }
        children[count] = pid;
        if (count + 1 < 2 * pairs) {
            struct timespec gap = {.tv_nsec = (10 + rand_r(&seed) % 31) * 1000000L};
            while (!stopped && nanosleep(&gap, &gap) < 0 && errno == EINTR) {}
        }
    }

    int remaining = count;
    while (!stopped && count == 2 * pairs && remaining > 0) {
        int status;
        pid_t done = waitpid(-1, &status, 0);
        if (done < 0) {
            if (errno == EINTR) continue;
            perror("waitpid");
            break;
        }
        for (int i = 0; i < count; ++i)
            if (children[i] == done) children[i] = 0;
        --remaining;
        if (!WIFEXITED(status) || WEXITSTATUS(status) != EXIT_SUCCESS) {
            fprintf(stderr, "Child %ld failed.\n", (long)done);
            break;
        }
        if (remaining == 0) return true;
    }
    /* fork 部分成功、子进程异常或用户中断时，收回本轮所有等待者。 */
    for (int i = 0; i < count; ++i) {
        if (children[i] > 0) {
            kill(children[i], SIGKILL);
            while (waitpid(children[i], NULL, 0) < 0 && errno == EINTR) {}
        }
    }
    return false;
}

static bool final_state(int pairs)
{
    int e = semctl(empty, 0, GETVAL);
    int f = semctl(full, 0, GETVAL);
    int m = semctl(mutex, 0, GETVAL);
    printf("Final: produced=%d consumed=%d stock=%d in=%d out=%d\n",
           warehouse->produced, warehouse->consumed, warehouse->stock,
           warehouse->in, warehouse->out);
    printf("Semaphores: empty=%d full=%d mutex=%d\n", e, f, m);
    return warehouse->produced == pairs && warehouse->consumed == pairs &&
           warehouse->stock == warehouse->initial && e == warehouse->capacity - f &&
           f == warehouse->stock && m == 1;
}

int main(int argc, char **argv)
{
    int pairs = argc > 1 ? number(argv[1], 1, MAX_PAIRS) : 4;
    int supplied_seed = argc > 2 ? number(argv[2], 0, INT_MAX) : 0;
    if (argc > 3 || pairs < 0 || supplied_seed < 0) {
        fprintf(stderr, "Usage: %s [pairs (1..%d) [seed (0..%d)]]\n", argv[0],
                MAX_PAIRS, INT_MAX);
        return EXIT_FAILURE;
    }
    unsigned seed = argc > 2 ? (unsigned)supplied_seed : (unsigned)time(NULL) ^ (unsigned)getpid();
    setvbuf(stdout, NULL, _IONBF, 0);  /* fork 前关闭缓冲，重定向也能实时看到各行。 */
    struct sigaction sa = {.sa_handler = on_signal};
    sigemptyset(&sa.sa_mask);
    if (sigaction(SIGINT, &sa, NULL) < 0 || sigaction(SIGTERM, &sa, NULL) < 0 ||
        sigaction(SIGPIPE, &sa, NULL) < 0) {
        perror("sigaction");
        return EXIT_FAILURE;
    }
    bool ok = init(pairs, seed) && run_children(pairs, seed) && final_state(pairs);
    release_ipc();
    if (stopped) return 128 + stopped;
    return ok ? EXIT_SUCCESS : EXIT_FAILURE;
}
