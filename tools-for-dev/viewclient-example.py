from com.dtmilano.android.viewclient import ViewClient

def main():
    device, serialno = ViewClient.connectToDeviceOrExit(serialno=None)
    vc = ViewClient(device, serialno)
    views_dict = vc.getViewsById()

    print("-------- Show the detail in the returned by the API ViewClient.getViewsById() --------")
    for key, value in views_dict.items():
        print("{}:\n{}\n".format(key, unicode(value).encode("UTF-8")))

    views = views_dict.values()
    id_view_dict = dict(map(lambda v: (v.getId(), v), [v for v in views if len(v.getId()) > 0]))

    print("\n")
    print("-------- Print the id-to-view pairs --------")
    for key, value in id_view_dict.items():
        print("{}:\n{}\n".format(key, unicode(value).encode("UTF-8")))

    pass    

if __name__ == "__main__":
    main()
