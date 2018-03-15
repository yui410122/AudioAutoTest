from com.dtmilano.android.viewclient import ViewClient

def main():
    device, serialno = ViewClient.connectToDeviceOrExit(serialno=None)
    vc = ViewClient(device, serialno)
    views_dict = vc.getViewsById()

    print("-------- Show the detail in the returned by the API ViewClient.getViewsById() --------")
    for key, value in views_dict.items():
        print("{}:\n{}\n".format(key, unicode(value).encode("UTF-8")))

    views = filter(lambda v: len(v.getId()) > 0, views_dict.values())
    id_view_dict = {}
    for v in views:
        if v.getId() in id_view_dict.keys():
            id_view_dict[v.getId()].append(v)
        else:
            id_view_dict[v.getId()] = [v]

    print("\n")
    print("-------- Print the id-to-view pairs --------")
    for key, value in id_view_dict.items():
        for each in value:
            print("{}:\n{}\n".format(key, unicode(each).encode("UTF-8")))

    vc.traverse()

    pass    

if __name__ == "__main__":
    main()
