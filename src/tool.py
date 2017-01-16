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

if __name__ == '__main__':
    def adjacent(x, y):
        return -1 <= x - y <= 1

    print(subgroup(None, adjacent))
    print(subgroup([], adjacent))
    print(subgroup([0], adjacent))
    print(subgroup([0, 1, 2, 3, 4, 5], adjacent))
    print(subgroup([0, 1, 2, 4, 7], adjacent))

