#!/usr/bin/env python3
'''
Non business-logic utils
'''

def subgroup(list, grp):
    if not list: return None
    list = sorted(list)

    buckets = []
    last = None

    for curr in list:
        if last is not None and grp(last, curr):  #careful if last = 0
            bucket.append(curr)
        else:
            bucket = [curr]
            buckets.append(bucket)
        last = curr

    return buckets

def filterOutIndex(list, idxes):
    idxes = set(idxes)
    return [elem for i, elem in enumerate(list) if i not in idxes]

def swaplist(list, i1, i2):
    e1 = list[i1]
    e2 = list[i2]
    list[i1] = e2
    list[i2] = e1

def rotateLeft(list, first, last, step):
    tmp = None
    for i in range(first, last+1, step):
        if tmp is None:
            tmp = list[i]
        else:
            list[i-step] = list[i]

    list[last] = tmp

def rotateRight(list, first, last, step):
    tmp =  None
    for i in range(last, first-1, -step):
        if tmp is None:
            tmp = list[i];
        else:
            list[i+step] = list[i]

    list[first] = tmp


if __name__ == '__main__':
    def adjacent(x, y):
        return -1 <= x - y <= 1

    #print(subgroup(None, adjacent))
    #print(subgroup([], adjacent))
    #print(subgroup([0], adjacent))
    #print(subgroup([0, 1, 2, 3, 4, 5], adjacent))
    #print(subgroup([0, 1, 2, 4, 7], adjacent))

    list = [0, 1, 0, 2, 0, 3, 0] 
    print(list)
    rotateRight(list, 1, 5, 2)
    print('-->', list)

    

