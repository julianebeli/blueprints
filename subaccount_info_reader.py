from subaccount_data import root_sub_account, info

# print(info)

def get_parent(id):

    ids = []
    p = info[str(id)]["parent"]
    ids.append(p)
    while p != root_sub_account:
        p = info[str(p)]["parent"]
        ids.append(p)
    return ids[:-1]


def get_child(id):
    children = []
    for k,v in info.items():
        if v["parent"] == id:
            children.append(int(k))
    return children

if __name__ == '__main__':

    print(get_parent(396))
    print(get_child(396))
