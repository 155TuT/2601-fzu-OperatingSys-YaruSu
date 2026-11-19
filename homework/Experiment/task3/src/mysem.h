#ifndef MYSEM_H
#define MYSEM_H

typedef int MySem;

MySem newsem(int initVal);
void psem(MySem semID);
void vsem(MySem semID);
void freesem(MySem semID);

#endif
