from fabric.api import run

def host_type():
    run('uname -s')

def install_python_pkgs():
    run('sudo pip install tornado redis nydus')


