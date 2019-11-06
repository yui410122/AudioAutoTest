import os

def run():
    git_proj = "https://github.com/bojanpotocnik/AndroidViewClient"
    os.system("pip install git+{}".format(git_proj))

if __name__ == "__main__":
    run()

