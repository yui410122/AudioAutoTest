from com.dtmilano.android.viewclient import ViewClient

import sys
import numpy as np
import matplotlib.pyplot as plt

def draw_rect(min_c, max_c, style, linewidth=4, ax=None):
    min_x, min_y = min_c
    max_x, max_y = max_c
    
    if ax != None:
        ax.plot([min_x, min_x, max_x, max_x, min_x], [min_y, max_y, max_y, min_y, min_y], style, linewidth=linewidth)
    else:
        plt.plot([min_x, min_x, max_x, max_x, min_x], [min_y, max_y, max_y, min_y, min_y], style, linewidth=linewidth)


def main(output_path="out.png"):
    device, serialno = ViewClient.connectToDeviceOrExit(serialno=None)
    vc = ViewClient(device, serialno)

    img = np.array(device.takeSnapshot())
    plt.imshow(img)

    views_dict = vc.getViewsById()
    # clickables = filter(lambda v: v.getClickable(), views_dict.values())
    # views = clickables
    views = views_dict.values()

    for v in views:
        min_c, max_c = v.getBounds()
        draw_rect(min_c, max_c, style="r--", linewidth=1)
        plt.annotate(v.getId().split("/")[-1] if len(v.getId()) > 0 else "\"empty\"", xy=v.getCenter(),
            horizontalalignment="center", verticalalignment="center", color="b", size=2.5)

    plt.gca().get_xaxis().set_visible(False)
    plt.gca().get_yaxis().set_visible(False)
    plt.savefig(output_path, bbox_inches="tight", pad_inches=0, dpi=300)

    pass    

if __name__ == "__main__":
    output_path = "out.png" if len(sys.argv) < 2 else sys.argv[1]
    sys.argv = sys.argv[:1]
    main(output_path)
