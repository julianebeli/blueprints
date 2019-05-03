from subaccount_data import root_sub_account, info


def get_parents(id):

    ids = [id]
    p = info[str(id)]["parent"]
    ids.append(p)
    while p != root_sub_account:
        p = info[str(p)]["parent"]
        ids.append(p)
    return ids[:-1]


if __name__ == '__main__':

    print(get_parents(39))
