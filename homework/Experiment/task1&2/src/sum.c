/* 实验一：读取一个非负整型数 n，计算 1 + 2 + ... + n。 */
#include <ctype.h>
#include <errno.h>
#include <limits.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

int main(void)
{
    char input[128];
    char *end;
    long n;
    long long sum;

    printf("Please enter an integer n (0..%d): ", INT_MAX);
    fflush(stdout);
    /* fgets + strtol 同时检查空输入、非法字符和超出整型范围。 */
    if (fgets(input, sizeof input, stdin) == NULL ||
        (strchr(input, '\n') == NULL && !feof(stdin))) {
        fprintf(stderr, "Input Error! A complete integer is required.\n");
        return EXIT_FAILURE;
    }
    errno = 0;
    n = strtol(input, &end, 10);
    if (end == input || errno == ERANGE || n < 0 || n > INT_MAX) {
        fprintf(stderr, "Input Error! n must be in 0..%d.\n", INT_MAX);
        return EXIT_FAILURE;
    }
    while (isspace((unsigned char)*end)) {
        ++end;
    }
    if (*end != '\0') {
        fprintf(stderr, "Input Error! Unexpected characters after n.\n");
        return EXIT_FAILURE;
    }
    /* 先提升到 long long，再相乘，避免 int 乘法溢出；n=0 时和为 0。 */
    sum = (long long)n * ((long long)n + 1) / 2;
    printf("1 + ... + %ld = %lld\n", n, sum);
    return EXIT_SUCCESS;
}
