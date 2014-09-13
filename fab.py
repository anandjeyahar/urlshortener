from fabric.api import run
def check_and_create_virtual_env_dir():
    import os
    home_folder = os.environ.get("HOME")
    virtual_env_dir = os.path.join(home_folder, ".virtualenvs")
    if not os.path.exists(virtual_env_dir):
        os.mkdir(virtual_env_dir)
    os.system('virtualenv --no-site-packages %s' % os.path.join(virtual_env_dir, "urlshortener"))

def host_type():
    run('uname -s')

def install_python_pkgs():
    run(check_and_create_virtual_env_dir)
    run('source ~/.virtualenvs/urlshortener/bin/activate; pip install tornado redis')



